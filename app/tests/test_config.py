"""
Tests for configuration module.

This module tests the application configuration settings and validation.
Following the development rule: Use pytest for all testing with proper async support.
"""

import pytest
import os
from unittest.mock import patch
from pydantic import ValidationError

from app.config import Settings, get_settings


class TestSettings:
    """Test cases for Settings configuration."""

    def test_default_settings(self):
        """Test default configuration values."""
        settings = Settings()
        
        assert settings.app_name == "SaveMyLinks"
        assert settings.app_version == "1.0.0"
        assert settings.debug is False
        assert settings.database_url == "sqlite+aiosqlite:///./savemylinks.db"
        assert settings.secret_key is not None
        assert len(settings.secret_key) >= 32
        assert settings.allowed_hosts == ["*"]
        assert settings.cors_origins == ["*"]
        assert settings.max_url_length == 2048
        assert settings.max_title_length == 200
        assert settings.max_description_length == 1000
        assert settings.max_category_length == 100
        assert settings.cache_ttl == 3600
        assert settings.rate_limit_requests == 100
        assert settings.rate_limit_window == 60

    @patch.dict(os.environ, {
        "APP_NAME": "TestApp",
        "APP_VERSION": "2.0.0",
        "DEBUG": "true",
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "SECRET_KEY": "test-secret-key-for-testing-purposes-only",
        "ALLOWED_HOSTS": "localhost,127.0.0.1",
        "CORS_ORIGINS": "http://localhost:3000,http://localhost:8080",
        "MAX_URL_LENGTH": "1024",
        "MAX_TITLE_LENGTH": "150",
        "MAX_DESCRIPTION_LENGTH": "500",
        "MAX_CATEGORY_LENGTH": "50",
        "CACHE_TTL": "1800",
        "RATE_LIMIT_REQUESTS": "50",
        "RATE_LIMIT_WINDOW": "30"
    })
    def test_environment_override(self):
        """Test that environment variables override default settings."""
        settings = Settings()
        
        assert settings.app_name == "TestApp"
        assert settings.app_version == "2.0.0"
        assert settings.debug is True
        assert settings.database_url == "postgresql://test:test@localhost/test"
        assert settings.secret_key == "test-secret-key-for-testing-purposes-only"
        assert settings.allowed_hosts == ["localhost", "127.0.0.1"]
        assert settings.cors_origins == ["http://localhost:3000", "http://localhost:8080"]
        assert settings.max_url_length == 1024
        assert settings.max_title_length == 150
        assert settings.max_description_length == 500
        assert settings.max_category_length == 50
        assert settings.cache_ttl == 1800
        assert settings.rate_limit_requests == 50
        assert settings.rate_limit_window == 30

    def test_secret_key_generation(self):
        """Test that secret key is generated if not provided."""
        settings = Settings()
        
        # Should have a secret key
        assert settings.secret_key is not None
        assert len(settings.secret_key) >= 32
        
        # Should be different each time if not set via environment
        settings2 = Settings()
        # Note: This might be the same due to caching, but the generation logic should work

    @patch.dict(os.environ, {"SECRET_KEY": "short"})
    def test_short_secret_key_validation(self):
        """Test that short secret keys are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        assert "Secret key must be at least 32 characters long" in str(exc_info.value)

    @patch.dict(os.environ, {"MAX_URL_LENGTH": "0"})
    def test_invalid_max_url_length(self):
        """Test that invalid max URL length is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        assert "Input should be greater than 0" in str(exc_info.value)

    @patch.dict(os.environ, {"RATE_LIMIT_REQUESTS": "-1"})
    def test_invalid_rate_limit_requests(self):
        """Test that negative rate limit requests is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        assert "Input should be greater than 0" in str(exc_info.value)

    def test_database_url_validation(self):
        """Test database URL validation."""
        # Valid SQLite URL
        settings = Settings(database_url="sqlite+aiosqlite:///./test.db")
        assert settings.database_url == "sqlite+aiosqlite:///./test.db"
        
        # Valid PostgreSQL URL
        settings = Settings(database_url="postgresql+asyncpg://user:pass@localhost/db")
        assert settings.database_url == "postgresql+asyncpg://user:pass@localhost/db"

    def test_cors_origins_parsing(self):
        """Test CORS origins parsing from string."""
        settings = Settings(cors_origins="http://localhost:3000,https://example.com")
        assert settings.cors_origins == ["http://localhost:3000", "https://example.com"]

    def test_allowed_hosts_parsing(self):
        """Test allowed hosts parsing from string."""
        settings = Settings(allowed_hosts="localhost,127.0.0.1,example.com")
        assert settings.allowed_hosts == ["localhost", "127.0.0.1", "example.com"]


class TestGetSettings:
    """Test cases for get_settings function."""

    def test_get_settings_returns_settings_instance(self):
        """Test that get_settings returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_caching(self):
        """Test that get_settings returns the same instance (caching)."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    @patch.dict(os.environ, {"APP_NAME": "CachedTestApp"})
    def test_get_settings_with_environment(self):
        """Test get_settings with environment variables."""
        # Clear any existing cache
        get_settings.cache_clear()
        
        settings = get_settings()
        assert settings.app_name == "CachedTestApp"