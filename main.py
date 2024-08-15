import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from urllib.parse import parse_qs, urljoin, urlparse
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.probability import FreqDist
from heapq import nlargest
import tiktoken

from gpt import generate_related_services

nltk.download('punkt_tab')
nltk.download('stopwords')

def summarize_text(text, ratio=0.2):
    sentences = sent_tokenize(text)
    words = word_tokenize(text.lower())
    stop_words = set(stopwords.words('english'))
    word_frequencies = FreqDist(word for word in words if word not in stop_words)
    
    sentence_scores = {}
    for sentence in sentences:
        for word in word_tokenize(sentence.lower()):
            if word in word_frequencies:
                if sentence not in sentence_scores:
                    sentence_scores[sentence] = word_frequencies[word]
                else:
                    sentence_scores[sentence] += word_frequencies[word]
    
    select_length = int(len(sentences) * ratio)
    summary = nlargest(select_length, sentence_scores, key=sentence_scores.get)
    return ' '.join(summary)

def should_skip_url(url):
    skip_patterns = [
        'pdf', '.jpg', '.png', '/news/', '/careers/', '/career/', '/jobs/', '/job/',
        'contact', 'search', 'privacy', 'terms', 'cookie', 'location', 'locations'
    ]
    
    if any(pattern in url.lower() for pattern in skip_patterns):
        return True

    last_segment = url.split("#")[-1]
    if(last_segment != '' and "/" not in last_segment):
        return True


    # Check for pagination parameters
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    if 'page' in query_params:
        return True
    
    return False

async def clean_content(html):
    soup = BeautifulSoup(html, 'html.parser')

    # Remove unwanted tags
    unwanted_tags = ['script', 'style', 'footer', 'header', 'nav', 'aside', 'img', 'link', 'noscript', 'meta', 'source', 'video']
    for tag in unwanted_tags:
        for element in soup.find_all(tag):
            element.decompose()

    # Remove elements with unwanted classes or ids
    unwanted_patterns = ['sidebar', 'menu', 'advertisement', 'ad-', 'banner', 'widget', 'popup', 'modal', 'cookie', 'social', 'navbar', 'footer', 'header']
    for pattern in unwanted_patterns:
        for element in soup.find_all(class_=re.compile(pattern, re.I)):
            element.decompose()
        for element in soup.find_all(id=re.compile(pattern, re.I)):
            element.decompose()

    # Get the cleaned text
    cleaned_text = soup.get_text(separator='\n', strip=True)
    return cleaned_text

async def crawl_website(start_url, max_pages=400):
    visited_urls = set()
    to_visit = [start_url]
    base_domain = urlparse(start_url).netloc
    crawled_content = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        while to_visit and len(visited_urls) < max_pages:
            url = to_visit.pop(0)
            print(f"Crawling: {url}")
            if url in visited_urls or should_skip_url(url):
                if(should_skip_url(url)):
                    print(f"Skipping: {url}")
                # add to visited_urls to avoid infinite loop
                visited_urls.add(url)
                continue

            try:
                await page.goto(url, wait_until="domcontentloaded")
                visited_urls.add(url)
                print(f"Crawled: {url}")

                # Get the page content
                content = await page.content()
                cleaned_content = await clean_content(content)
                summarized_content = summarize_text(cleaned_content)
                crawled_content[url] = summarized_content

                # Extract links
                links = await page.eval_on_selector_all("a[href]", """
                    (elements) => elements.map(el => el.href)
                """)

                # Process links
                for link in links:
                    absolute_url = urljoin(url, link)
                    if urlparse(absolute_url).netloc == base_domain and absolute_url not in visited_urls:
                        to_visit.append(absolute_url)

            except Exception as e:
                print(f"Error crawling {url}: {e}")

        await browser.close()
    print(f"Crawling completed. Total pages crawled: {len(visited_urls)}")
    return crawled_content

def count_tokens(text, model="gpt-4o"):
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

async def main():
    model = "gpt-4o"
    content = await crawl_website("https://www.recipharm.com/", max_pages=9999)
    # replace all the spaces and newlines with single space
    content = {url: re.sub(r'\s+', ' ', text) for url, text in content.items()}
    # Combine all content
    combined_content = "".join([f"{text} " for url, text in content.items()])
    # Write combined content to file
    with open("crawled_content.txt", "w", encoding="utf-8") as f:
        f.write(combined_content)
    
    # Count tokens
    token_count = count_tokens(combined_content, model)
    
    print(f"Combined content written to 'crawled_content.txt'")
    print(f"Total token count: {token_count}")
    
    # Estimate cost (assuming gpt-3.5-turbo pricing)
    estimated_cost = (token_count / 1000) * 0.002  # $0.002 per 1K tokens
    print(f"Estimated cost for GPT-{model}: ${estimated_cost:.2f}")
    
    # read crawled_content.txt and pass it to the function
    print("Generating related services...")
    generate_related_services(combined_content)
    print("Related services generated.")
# Usage
if __name__ == "__main__":
    asyncio.run(main())