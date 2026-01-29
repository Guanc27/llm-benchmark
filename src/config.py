"""
Application configuration.

Loads settings from environment variables (and .env file).
Uses pydantic-settings for validation and type coercion.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    # Default to SQLite for simplicity (no Docker needed)
    # Change to PostgreSQL for production: postgresql://user:pass@localhost:5432/dbname
    database_url: str = "sqlite:///./llm_benchmark.db"

    # API Keys
    anthropic_api_key: str = ""

    # Tell pydantic-settings to load from .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # Environment variables are case-insensitive
        case_sensitive=False,
    )


# Create a single instance to import elsewhere
# Usage: from src.config import settings
settings = Settings()
