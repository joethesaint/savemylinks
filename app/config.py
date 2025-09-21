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
        if field_name in ("allowed_origins", "allowed_hosts") and isinstance(value, str):
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
    
    # CORS Settings - Standardized naming
    allowed_origins: List[str] = Field(
        default=["http://localhost:8000", "http://127.0.0.1:8000"],
        validation_alias=AliasChoices("allowed_origins", "ALLOWED_ORIGINS", "cors_origins", "CORS_ORIGINS"),
        description="List of allowed CORS origins"
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
    
    # Cache Settings - Standardized naming
    cache_enabled: bool = Field(
        default=True,
        description="Enable in-memory caching"
    )
    cache_default_ttl: int = Field(
        default=300,
        validation_alias=AliasChoices("cache_default_ttl", "cache_ttl"),
        description="Default cache TTL in seconds"
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
    
    @field_validator("allowed_origins", "allowed_hosts", mode="before")
    @classmethod
    def parse_string_lists(cls, v: Any) -> Any:
        """Parse comma-separated strings into lists."""
        if isinstance(v, str):
            if not v.strip():
                return []
            return [item.strip() for item in v.split(",") if item.strip()]
        elif isinstance(v, list):
            return v
        else:
            return []
    
    @field_validator("allowed_origins")
    @classmethod
    def validate_cors_security(cls, v, info):
        """Validate CORS origins for security."""
        # Don't override empty lists - let get_cors_origins() handle defaults
        if not v:
            return v
        
        # In production, warn about wildcard origins
        environment = info.data.get("environment", "development")
        if environment == "production" and "*" in v:
            import warnings
            warnings.warn(
                "Using wildcard '*' for CORS origins in production is not recommended for security",
                UserWarning
            )
        
        return v
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting."""
        valid_environments = {"development", "staging", "production"}
        if v not in valid_environments:
            raise ValueError(f"Environment must be one of: {valid_environments}")
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level setting."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v_upper
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v, info):
        """Validate secret key strength."""
        if len(v) < 32:
            import warnings
            warnings.warn(
                "Secret key should be at least 32 characters long for security",
                UserWarning
            )
        
        environment = info.data.get("environment", "development")
        if environment == "production" and v == os.urandom(32).hex():
            import warnings
            warnings.warn(
                "Using auto-generated secret key in production. Set SECRET_KEY environment variable.",
                UserWarning
            )
        
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins with environment-specific defaults."""
        if self.is_development and not self.allowed_origins:
            return ["http://localhost:8000", "http://127.0.0.1:8000"]
        elif self.is_production and "*" in self.allowed_origins:
            # In production, be more restrictive
            return ["https://yourdomain.com"]  # Replace with actual domain
        return self.allowed_origins or ["*"]  # Fallback to wildcard if empty
    
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """Customize settings sources to use our custom env source."""
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
        # Allow reading from environment variables
        env_prefix="",
        # Ignore extra fields not defined in the model
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.
    
    This function uses LRU cache to ensure settings are loaded only once
    and reused throughout the application lifecycle.
    
    Returns:
        Settings: Application configuration instance
    """
    return Settings()


def get_database_url() -> str:
    """
    Get database URL from settings.
    
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
    return get_settings().is_development


def is_production() -> bool:
    """
    Check if application is running in production mode.
    
    Returns:
        bool: True if in production mode
    """
    return get_settings().is_production


# Export public interface
__all__ = [
    "Settings",
    "get_settings",
    "get_database_url", 
    "is_development",
    "is_production"
]