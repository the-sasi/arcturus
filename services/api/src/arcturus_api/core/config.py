"""Typed application settings, loaded from environment / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ARCTURUS_", extra="ignore")

    app_name: str = "Arcturus API"
    environment: str = "development"
    debug: bool = True

    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Infrastructure connections (defaults match infra/docker-compose.yml)
    postgres_dsn: str = "postgresql+asyncpg://arcturus:arcturus@localhost:5432/arcturus"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    neo4j_url: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "arcturus-dev"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "arcturus"
    minio_secret_key: str = "arcturus-dev"

    # Providers (each capability is independently swappable)
    market_data_provider: str = "yahoo"
    fundamental_data_provider: str = "yahoo"
    news_provider: str = "yahoo"


@lru_cache
def get_settings() -> Settings:
    return Settings()
