from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import AliasChoices, Field, SecretStr, model_validator
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
    # Chunking (sizes are in characters; ~4 chars per token for English)
    chunk_size_chars: int = Field(default=1500, gt=0)
    chunk_overlap_chars: int = Field(default=200, ge=0)
    # Ingestion
    max_chunks_per_document: int = Field(default=2000, gt=0)
    ingestion_batch_size: int = Field(default=64, gt=0)
    # File storage (local disk now; swap implementation for S3 later)
    storage_local_dir: Path = Path("var/uploads")
    # Uploads
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, gt=0)

    # Retrieval
    retrieval_top_k: int = Field(default=5, ge=1, le=50)
    retrieval_score_threshold: float | None = None
    # LLM
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "meta-llama/llama-3.1-8b-instruct"
    llm_max_tokens: int = 500
    llm_temperature: float = 0.3
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2


    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    # LangSmith Tracing
    langchain_tracing_v2: bool = Field(
        default=False,
        validation_alias=AliasChoices("langchain_tracing_v2", "langsmith_tracing"),
    )
    langchain_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("langchain_api_key", "langsmith_api_key"),
    )
    langchain_endpoint: str = Field(
        default="https://api.smith.langchain.com",
        validation_alias=AliasChoices("langchain_endpoint", "langsmith_endpoint"),
    )
    langchain_project: str = Field(
        default="realestate-ai",
        validation_alias=AliasChoices("langchain_project", "langsmith_project"),
    )

    @model_validator(mode="after")
    def _validate_chunking(self) -> Self:
        if self.chunk_overlap_chars >= self.chunk_size_chars:
            raise ValueError("CHUNK_OVERLAP_CHARS must be smaller than CHUNK_SIZE_CHARS")
        return self

    @model_validator(mode="after")
    def _export_langsmith_env(self) -> Self:
        import os

        if self.langchain_tracing_v2 and self.langchain_api_key:
            api_key = self.langchain_api_key.get_secret_value()
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = api_key
            os.environ["LANGCHAIN_ENDPOINT"] = self.langchain_endpoint
            os.environ["LANGCHAIN_PROJECT"] = self.langchain_project

            os.environ["LANGSMITH_TRACING"] = "true"
            os.environ["LANGSMITH_API_KEY"] = api_key
            os.environ["LANGSMITH_ENDPOINT"] = self.langchain_endpoint
            os.environ["LANGSMITH_PROJECT"] = self.langchain_project
        return self

@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]




