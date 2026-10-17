from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    secret_key: SecretStr 
    database_url: str
    redis_url: str
    admin_api_key: str
    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "knowledge_chunks"
    qdrant_timeout_seconds: int = 30
    # Embeddings
    embedding_dimension: int = 2048
    # anthropic_api_key: SecretStr | None = None
    
    # OpenRouter / Embeddings
    openrouter_api_key: SecretStr = SecretStr("")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    embedding_model: str = "nvidia/llama-nemotron-embed-vl-1b-v2:free"
    embedding_batch_size: int = 32
    embedding_max_concurrency: int = 2
    embedding_timeout_seconds: float = 60.0
    embedding_max_retries: int = 5


    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]