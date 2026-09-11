import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings are loaded locally from environment variables and .env."""

    project_name: str = "News Authentication API"
    version: str = "0.1.0"
    api_v1_str: str = "/api/v1"

    database_url: str = "sqlite:///./news_auth.db"
    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    fact_check_api_key: str = "mock-fact-check-key-local"
    seed_demo_data: bool = True
    initial_admin_username: str | None = None
    initial_admin_email: str | None = None
    initial_admin_password: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def is_production(self) -> bool:
        """Whether the process runs in Vercel's serverless environment."""
        return bool(os.environ.get("VERCEL"))

    @property
    def db_url(self) -> str:
        """Return a persistent database URL suitable for the current environment."""
        if self.is_production and self.database_url.startswith("sqlite"):
            raise RuntimeError(
                "DATABASE_URL must point to a persistent PostgreSQL database when deploying to Vercel."
            )
        if self.database_url.startswith("postgres://"):
            return "postgresql+psycopg://" + self.database_url.removeprefix("postgres://")
        if self.database_url.startswith("postgresql://"):
            return "postgresql+psycopg://" + self.database_url.removeprefix("postgresql://")
        return self.database_url

    @property
    def signing_key(self) -> str:
        """Return the JWT secret, rejecting unsafe production defaults."""
        if self.jwt_secret:
            return self.jwt_secret
        if self.is_production:
            raise RuntimeError("JWT_SECRET must be configured when deploying to Vercel.")
        return "local-development-only-jwt-secret"

    @property
    def should_seed_demo_data(self) -> bool:
        """Demo data is never seeded in production deployments."""
        return self.seed_demo_data and not self.is_production


settings = Settings()
