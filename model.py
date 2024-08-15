from config import Settings
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

def get_model() -> BaseChatModel:
    settings = Settings()

    gpt4o = ChatOpenAI(
        model="gpt-4o",
        temperature=0.95,
        max_retries=0,
        openai_api_key=settings.openai_api_key,
    )

    mixtral = ChatOpenAI(
        base_url="https://api.together.xyz/v1",
        api_key=settings.together_api_key,
        model="mistralai/Mixtral-8x7B-Instruct-v0.1",
        temperature=1,
        max_retries=0,
    )

    return gpt4o.with_fallbacks([mixtral])
