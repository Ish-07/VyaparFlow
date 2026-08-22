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

    # AI providers — NVIDIA NIM (OpenAI-compatible) as primary; rule-based
    # parser remains as fallback when the LLM is unavailable or returns
    # something we can't trust. See app/services/ai/ for the abstraction.
    speech_provider: str = "openai"
    llm_provider: str = "nvidia_nim"
    llm_api_key: str | None = None
    llm_base_url: str = "https://integrate.api.nvidia.com/v1"
    llm_command_model: str = "meta/llama-3.3-70b-instruct"
    llm_rag_model: str = "meta/llama-3.1-8b-instruct"
    llm_agent_model: str = "nvidia/llama-3.3-nemotron-super-49b-v1.5"
    embedding_model: str = "nvidia/nemotron-3-embed-1b"
    translation_model: str = "nvidia/riva-translate-4b-instruct-v1_1"
    ai_request_timeout_seconds: float = 10.0
    ai_max_retries: int = 1
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
