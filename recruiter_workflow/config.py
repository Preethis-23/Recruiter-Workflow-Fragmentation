"""Configuration management for Recruiter Workflow API."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional, List
import logging


class Settings(BaseSettings):
    """Application settings using environment variables with sensible defaults.
    
    pydantic-settings automatically maps UPPER_CASE field names to
    environment variables, so no explicit ``env=`` is needed.
    """

    # Application settings
    APP_NAME: str = "Recruiter Workflow Fragmentation API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v):
        """Parse DEBUG environment variable."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ('true', '1', 't', 'y', 'yes', 'on')
        return bool(v)
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database settings
    DATABASE_URL: str = "sqlite:///./recruiter_workflow.db"
    DATABASE_ECHO: bool = False
    
    # Security settings
    SECRET_KEY: str = "your-secret-key-here"
    ALLOWED_ORIGINS: List[str] = ["*"]
    API_KEY: Optional[str] = None
    
    # Rate limiting
    RATE_LIMIT: int = 100
    RATE_LIMIT_WINDOW: int = 60
    
    # LLM Provider: "openai" or "ollama"
    LLM_PROVIDER: str = "ollama"
    
    # OpenAI settings
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    
    # Ollama settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    
    # File storage settings
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Agent settings
    AGENT_MAX_ITERATIONS: int = 10
    AGENT_VERBOSE: bool = True
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_log_level(self) -> int:
        """Convert string log level to logging constant."""
        return getattr(logging, self.LOG_LEVEL.upper(), logging.INFO)


# Initialize settings
settings = Settings()