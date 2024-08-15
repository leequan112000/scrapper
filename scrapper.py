import json
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Page
from pydantic import BaseModel, Field

class Config(BaseModel):
    url: str = Field(..., description="URL to start the crawl")
    match: str = Field(..., description="Pattern to match against for links to crawl")
    exclude: Optional[str] = Field(None, description="Pattern to match against for links to exclude")
    selector: Optional[str] = Field(None, description="Selector to grab the inner text from")
    max_pages_to_crawl: int = Field(50, description="Maximum number of pages to crawl")
    output_file_name: str = Field("output.json", description="File name for the finished data")
    wait_for_selector_timeout: int = Field(1000, description="Timeout for waiting for a selector to appear")

class Crawler:
    def __init__(self, config: Config):
        self.config = config
        self.visited_urls: set = set()
        self.results: List[Dict[str, Any]] = []

    async def crawl(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await self.crawl_page(page, self.config.url)
            await browser.close()

    async def crawl_page(self, page: Page, url: str):
        if len(self.visited_urls) >= self.config.max_pages_to_crawl:
            return

        if url in self.visited_urls:
            return

        self.visited_urls.add(url)

        try:
            await page.goto(url)
            
            if self.config.selector:
                await page.wait_for_selector(self.config.selector, timeout=self.config.wait_for_selector_timeout)

            title = await page.title()
            
            if self.config.selector:
                html = await page.inner_text(self.config.selector)
            else:
                html = await page.inner_text('body')

            self.results.append({
                "title": title,
                "url": url,
                "html": html
            })

            print(f"Crawled: {url}")

            links = await page.eval_on_selector_all('a[href]', """
                (elements) => elements.map(el => el.href)
            """)

            for link in links:
                if self.should_crawl(link):
                    await self.crawl_page(page, link)

        except Exception as e:
            print(f"Error crawling {url}: {str(e)}")

    def should_crawl(self, url: str) -> bool:
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        if base_url != urlparse(self.config.url).netloc:
            return False

        if self.config.exclude and self.config.exclude in url:
            return False

        return self.config.match in url

    def write_results(self):
        with open(self.config.output_file_name, 'w') as f:
            json.dump(self.results, f, indent=2)

    def get_results(self):
        return self.results