import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""

    # Service
    service_name: str = Field(default="rag-service", env="SERVICE_NAME")
    service_version: str = Field(default="1.0.0", env="SERVICE_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")

    # Database
    database_url: str = Field(env="DATABASE_URL")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")

    # Embedding Model
    embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        env="EMBEDDING_MODEL"
    )
    embedding_dimension: int = Field(default=768, env="EMBEDDING_DIMENSION")
    embedding_batch_size: int = Field(default=32, env="EMBEDDING_BATCH_SIZE")

    # Document Processing
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    max_file_size: int = Field(default=52428800, env="MAX_FILE_SIZE")  # 50MB
    supported_formats: str = Field(default="pdf,docx,txt,md", env="SUPPORTED_FORMATS")

    # RAG Settings
    default_top_k: int = Field(default=5, env="DEFAULT_TOP_K")
    min_similarity_score: float = Field(default=0.7, env="MIN_SIMILARITY_SCORE")
    max_context_length: int = Field(default=8000, env="MAX_CONTEXT_LENGTH")

    # Anthropic API
    anthropic_api_key: str = Field(env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-4-20250514", env="ANTHROPIC_MODEL")
    max_tokens: int = Field(default=4096, env="MAX_TOKENS")

    # Storage
    upload_dir: str = Field(default="/app/uploads", env="UPLOAD_DIR")
    temp_dir: str = Field(default="/app/temp", env="TEMP_DIR")

    # Rate Limiting
    rate_limit_per_minute: int = Field(default=30, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=500, env="RATE_LIMIT_PER_HOUR")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"],
        env="CORS_ORIGINS"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
