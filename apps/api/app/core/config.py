from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "local"

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Object storage
    object_storage_bucket: str = "vyaparflow-files"
    object_storage_endpoint: str | None = None
    object_storage_access_key: str | None = None
    object_storage_secret_key: str | None = None

    # AI providers
    speech_provider: str = "openai"
    llm_provider: str = "openai"
    llm_api_key: str | None = None

    # Business rule defaults
    command_confidence_threshold: float = 0.75
    allow_negative_stock: bool = False
    audio_retention_days: int = 0


@lru_cache
def get_settings() -> Settings:
    return Settings()
