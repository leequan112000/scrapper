from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Cromatic AI"
    aws_database_url: str
    openai_api_key: str
    together_api_key: str
    celery_broker_url: str
    celery_result_backend: str
    webhook_url: str
    webhook_secret: str

    model_config = SettingsConfigDict(env_file=".env")
