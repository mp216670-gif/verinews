import os
import tempfile
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

    @property
    def db_url(self) -> str:
        # If running on Vercel serverless with default SQLite, store in writable /tmp directory
        if os.environ.get("VERCEL") and self.database_url == "sqlite:///./news_auth.db":
            tmp_db = os.path.join(tempfile.gettempdir(), "news_auth.db")
            return f"sqlite:///{tmp_db}"
        return self.database_url


settings = Settings()
