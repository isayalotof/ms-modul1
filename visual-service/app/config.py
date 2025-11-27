"""Configuration module for Visual Service."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Service
    SERVICE_NAME: str = "visual-service"
    SERVICE_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # S3 Configuration
    S3_ENDPOINT: str = "http://minio:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "visual-storage"
    S3_REGION: str = "us-east-1"
    S3_USE_SSL: bool = False

    # API Keys
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Image Generation
    DEFAULT_IMAGE_SIZE: str = "1024x1024"
    MAX_IMAGE_SIZE: str = "1792x1792"
    SUPPORTED_IMAGE_FORMATS: str = "png,jpg,webp"

    # Chart Generation
    DEFAULT_CHART_DPI: int = 300
    DEFAULT_CHART_SIZE: str = "800x600"
    MAX_CHART_SIZE: str = "2400x1800"

    # Storage
    MAX_FILE_SIZE: str = "50MB"
    FILE_EXPIRATION_DAYS: int = 30

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Proxy Configuration
    HTTP_PROXY: str = ""
    HTTPS_PROXY: str = ""
    NO_PROXY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
