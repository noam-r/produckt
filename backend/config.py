"""
Application configuration using Pydantic Settings.
Loads environment variables from .env file.
"""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = Field(
        default="sqlite:///./produck.db",
        description="Database connection string"
    )

    # Redis
    redis_url: str = Field(
        default="",
        description="Redis connection string (optional for POC)"
    )

    # Authentication
    secret_key: str = Field(
        ...,
        min_length=32,
        description="Secret key for session signing (min 32 chars)"
    )
    session_timeout_minutes: int = Field(
        default=60,
        description="Session expiration time in minutes"
    )
    bcrypt_rounds: int = Field(
        default=12,
        description="BCrypt password hashing rounds"
    )

    # Anthropic
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key"
    )
    anthropic_api_timeout: int = Field(
        default=600,
        description="Anthropic API timeout in seconds (max 600 for Anthropic API)"
    )
    anthropic_model: str = Field(
        default="claude-sonnet-4-5",
        description="Anthropic model to use for agents"
    )

    # Application
    environment: str = Field(
        default="development",
        description="Environment: development, staging, production"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR"
    )
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Comma-separated CORS origins"
    )

    # Rate Limiting
    rate_limit_per_minute: int = Field(
        default=100,
        description="Rate limit per user per minute"
    )
    rate_limit_org_per_minute: int = Field(
        default=1000,
        description="Rate limit per organization per minute"
    )

    # Optional: Observability
    langsmith_api_key: str = Field(
        default="",
        description="LangSmith API key (optional)"
    )
    langsmith_project: str = Field(
        default="produck-poc",
        description="LangSmith project name"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()
