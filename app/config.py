"""
Configuration Management for SaveMyLinks Application

This module provides centralized configuration management using Pydantic settings.
It supports environment variables, .env files, and provides type-safe configuration
with validation and sensible defaults for development.

Key Features:
- Type-safe configuration with Pydantic BaseSettings
- Environment-based settings (development/staging/production)
- Comprehensive validation including CORS security checks
- Support for .env files with automatic loading
- Development-friendly defaults with production security
"""

import os
from functools import lru_cache
from typing import List, Optional, Literal, Any
from pydantic import field_validator, Field, ConfigDict, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import EnvSettingsSource
from pydantic.fields import FieldInfo


class CustomEnvSettingsSource(EnvSettingsSource):
    """Custom environment settings source that handles comma-separated lists."""
    
    def prepare_field_value(
        self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool
    ) -> Any:
        """Prepare field value, handling comma-separated lists for specific fields."""
        # Handle comma-separated list fields
        if field_name in ("cors_origins", "allowed_origins", "allowed_hosts") and isinstance(value, str):
            if not value.strip():
                return []
            return [item.strip() for item in value.split(",") if item.strip()]
        
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    
    This class defines all configuration options for the SaveMyLinks application.
    Settings can be provided via environment variables, .env files, or use defaults.
    """
    
    # Application Settings
    app_name: str = Field(default="SaveMyLinks", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    environment: Literal["development", "staging", "production"] = Field(
        default="development", 
        description="Application environment"
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # Server Settings
    host: str = Field(default="127.0.0.1", description="Server host address")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=True, description="Enable auto-reload for development")
    
    # Database Settings
    database_url: str = Field(
        default="sqlite+aiosqlite:///./savemylinks.db",
        description="Database connection URL"
    )
    database_echo: bool = Field(
        default=False, 
        description="Enable SQLAlchemy query logging"
    )
    
    # CORS Settings
    allowed_origins: List[str] = Field(
        default=["http://localhost:8000", "http://127.0.0.1:8000"],
        validation_alias=AliasChoices("allowed_origins", "ALLOWED_ORIGINS"),
        description="List of allowed CORS origins"
    )
    cors_origins: List[str] = Field(
        default=["*"],
        validation_alias=AliasChoices("cors_origins", "CORS_ORIGINS"),
        description="CORS origins (alias for allowed_origins)"
    )
    allowed_hosts: List[str] = Field(
        default=["*"],
        validation_alias=AliasChoices("allowed_hosts", "ALLOWED_HOSTS"),
        description="List of allowed host headers"
    )
    allow_credentials: bool = Field(
        default=False,
        description="Allow credentials in CORS requests"
    )
    allowed_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed HTTP methods for CORS"
    )
    allowed_headers: List[str] = Field(
        default=["*"],
        description="Allowed headers for CORS requests"
    )
    
    # Content Validation Settings
    max_url_length: int = Field(
        default=2048,
        gt=0,
        description="Maximum URL length allowed"
    )
    max_title_length: int = Field(
        default=200,
        gt=0,
        description="Maximum title length allowed"
    )
    max_description_length: int = Field(
        default=1000,
        gt=0,
        description="Maximum description length allowed"
    )
    max_category_length: int = Field(
        default=100,
        gt=0,
        description="Maximum category length allowed"
    )
    
    # Security Settings
    secret_key: str = Field(
        default_factory=lambda: os.urandom(32).hex(),
        description="Secret key for cryptographic operations"
    )
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes"
    )
    
    # Rate Limiting Settings
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting middleware"
    )
    rate_limit_requests: int = Field(
        default=100,
        gt=0,
        description="Number of requests allowed per window"
    )
    rate_limit_window: int = Field(
        default=60,
        gt=0,
        description="Rate limiting window in seconds"
    )
    
    # Logging Settings
    log_level: str = Field(
        default="DEBUG",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    log_file: Optional[str] = Field(
        default="logs/savemylinks.log",
        description="Log file path (None for console only)"
    )
    log_rotation: bool = Field(
        default=True,
        description="Enable log file rotation"
    )
    log_max_size: str = Field(
        default="10MB",
        description="Maximum log file size before rotation"
    )
    log_backup_count: int = Field(
        default=5,
        description="Number of backup log files to keep"
    )
    
    # Cache Settings
    cache_enabled: bool = Field(
        default=True,
        description="Enable in-memory caching"
    )
    cache_default_ttl: int = Field(
        default=300,
        description="Default cache TTL in seconds"
    )
    cache_ttl: int = Field(
        default=3600,
        description="Cache TTL in seconds (alias for cache_default_ttl)"
    )
    cache_max_size: int = Field(
        default=1000,
        description="Maximum number of cache entries"
    )
    
    # Static Files Settings
    static_files_enabled: bool = Field(
        default=True,
        description="Enable static file serving"
    )
    static_directory: str = Field(
        default="app/static",
        description="Static files directory"
    )
    
    # Template Settings
    templates_directory: str = Field(
        default="app/templates",
        description="Templates directory"
    )
    
    @field_validator("allowed_origins", "cors_origins", "allowed_hosts", mode="before")
    @classmethod
    def parse_string_lists(cls, v: Any) -> Any:
        """Parse comma-separated strings into lists."""
        if isinstance(v, str):
            # Handle empty strings
            if not v.strip():
                return []
            # Split by comma and strip whitespace
            return [item.strip() for item in v.split(",") if item.strip()]
        elif isinstance(v, list):
            return v
        elif v is None:
            return []
        else:
            # Convert other types to string first, then parse
            return cls.parse_string_lists(str(v))
    
    @field_validator("allowed_origins")
    @classmethod
    def validate_cors_security(cls, v, info):
        """
        Validate CORS configuration for security.
        
        Prevents wildcard origins when credentials are enabled.
        """
        # Get other field values from validation info
        if hasattr(info, 'data') and info.data.get("allow_credentials", False) and "*" in v:
            raise ValueError(
                "Cannot use wildcard CORS origins when credentials are enabled. "
                "This is a security vulnerability. Please specify explicit origins."
            )
        return v
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting."""
        valid_environments = ["development", "staging", "production"]
        if v not in valid_environments:
            raise ValueError(f"Environment must be one of: {valid_environments}")
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level setting."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v, info):
        """Validate secret key length and production requirements."""
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        
        # Get other field values from validation info
        if (hasattr(info, 'data') and info.data.get("environment") == "production" and 
            v == "your-secret-key-change-in-production"):
            raise ValueError(
                "You must set a secure SECRET_KEY in production environment"
            )
        return v
    
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"
    
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"
    
    def get_cors_origins(self) -> List[str]:
        """
        Get CORS origins with environment-specific defaults.
        
        Returns safe defaults for development and requires explicit
        configuration for production.
        """
        if self.is_development() and not self.allowed_origins:
            return ["http://localhost:8000", "http://127.0.0.1:8000"]
        return self.allowed_origins
    
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """Customize settings sources to use our custom environment source."""
        return (
            init_settings,
            CustomEnvSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Environment variable prefixes
        env_prefix="",
        # Field aliases for common environment variable names
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings with caching.
    
    This function creates and caches the settings instance to avoid
    re-parsing environment variables on every call.
    
    Returns:
        Settings: Configured application settings
    """
    return Settings()


def get_database_url() -> str:
    """
    Get database URL with environment-specific handling.
    
    Returns:
        str: Database connection URL
    """
    settings = get_settings()
    return settings.database_url


def is_development() -> bool:
    """
    Check if application is running in development mode.
    
    Returns:
        bool: True if in development mode
    """
    return get_settings().is_development()


def is_production() -> bool:
    """
    Check if application is running in production mode.
    
    Returns:
        bool: True if in production mode
    """
    return get_settings().is_production()


# Export commonly used settings for convenience
__all__ = [
    "Settings",
    "get_settings",
    "get_database_url", 
    "is_development",
    "is_production"
]