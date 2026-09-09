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

        # AI provider configuration.
    # The rule-based parser remains available as a fallback when the
    # configured LLM is unavailable or returns an invalid response.
    speech_provider: str = "openai"
    llm_provider: str = "gemini"
    llm_api_key: str | None = None
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    # Gemini models
    llm_command_model: str = "gemini-2.5-flash"
    llm_rag_model: str = "gemini-2.5-flash"
    llm_agent_model: str = "gemini-2.5-flash"
    embedding_model: str = "gemini-embedding-001"
    embedding_dimension: int = 1536
    translation_model: str = "gemini-2.5-flash"

    ai_request_timeout_seconds: float = 60.0
    ai_max_retries: int = 2
    enable_rule_based_ai_fallback: bool = True

    #paddleocr setttings
    ocr_provider: str = "paddleocr"
    ocr_language: str = "en"
    ocr_enable_gpu: bool = False

    # Business rule defaults
    command_confidence_threshold: float = 0.75
    allow_negative_stock: bool = False
    audio_retention_days: int = 0


    #


@lru_cache
def get_settings() -> Settings:
    return Settings()
