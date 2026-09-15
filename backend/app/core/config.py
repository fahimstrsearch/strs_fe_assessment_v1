import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_ENV: str = "development"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5434/strs_training"
    CORS_ORIGINS: str = "*"
    LOG_LEVEL: str = ""

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def log_level(self) -> int:
        name = (self.LOG_LEVEL or ("INFO" if self.is_production else "DEBUG")).upper()
        return logging.getLevelNamesMapping().get(name, logging.INFO)

    @property
    def async_database_url(self) -> str:
        """Point a libpq URL at the asyncpg driver."""
        if self.DATABASE_URL.startswith("postgresql+asyncpg://"):
            return self.DATABASE_URL
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


@lru_cache
def get_config() -> Config:
    return Config()
