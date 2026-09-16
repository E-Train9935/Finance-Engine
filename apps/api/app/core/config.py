from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve .env relative to apps/api instead of the shell's working directory.
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_name: str = "FINENGINE"
    environment: str = "development"
    port: int = 8000

    twelve_data_api_key: str | None = None
    sec_user_agent: str = "FinEngine/2.0 portfolio-contact@example.com"

    cache_ttl_seconds: int = 300
    twelve_data_requests_per_minute: int = 7

    allowed_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def origin_list(self) -> list[str]:
        return [
            x.strip()
            for x in self.allowed_origins.split(",")
            if x.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()