from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings are loaded locally from environment variables and .env."""

    project_name: str = "News Authentication API"
    version: str = "0.1.0"
    api_v1_str: str = "/api/v1"

    database_url: str = "sqlite:///./news_auth.db"
    jwt_secret: str = "supersecretjwtkeyforlocalnewsauthenticationdevelopment12345"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    fact_check_api_key: str = "mock-fact-check-key-local"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
