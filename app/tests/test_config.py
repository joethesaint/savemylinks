"""
Tests for configuration management.

This module tests the Settings class and its validation logic,
including environment variable parsing and security validations.
"""

import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError

from app.config import Settings, get_settings


class TestSettings:
    """Test the Settings configuration class."""
    
    def test_default_settings(self):
        """Test that default settings are loaded correctly."""
        settings = Settings()
        
        # Basic settings
        assert settings.app_name == "SaveMyLinks"
        assert settings.app_version == "1.0.0"
        assert settings.environment == "development"
        assert settings.debug is False
        
        # Server settings
        assert settings.host == "127.0.0.1"
        assert settings.port == 8000
        
        # CORS settings - using standardized names
        assert settings.allowed_origins == ["http://localhost:8000", "http://127.0.0.1:8000"]
        
        # Cache settings - using standardized names
        assert settings.cache_default_ttl == 300
    
    def test_environment_variable_parsing(self):
        """Test parsing of environment variables."""
        env_vars = {
            "APP_NAME": "TestApp",
            "ENVIRONMENT": "production",
            "DEBUG": "true",
            "PORT": "9000",
            "ALLOWED_ORIGINS": "http://localhost:3000,http://localhost:8080",
            "CACHE_DEFAULT_TTL": "1800",
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.app_name == "TestApp"
            assert settings.environment == "production"
            assert settings.debug is True
            assert settings.port == 9000
            assert settings.allowed_origins == ["http://localhost:3000", "http://localhost:8080"]
            assert settings.cache_default_ttl == 1800
    
    def test_cors_origins_alias_support(self):
        """Test that cors_origins alias still works for backward compatibility."""
        env_vars = {
            "CORS_ORIGINS": "http://localhost:3000,http://localhost:8080",
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.allowed_origins == ["http://localhost:3000", "http://localhost:8080"]
    
    def test_cache_ttl_alias_support(self):
        """Test that cache_ttl alias still works for backward compatibility."""
        env_vars = {
            "CACHE_TTL": "1800",
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.cache_default_ttl == 1800
    
    def test_string_list_parsing(self):
        """Test parsing of comma-separated string lists."""
        # Test direct instantiation with string
        settings = Settings(allowed_origins="http://localhost:3000,https://example.com")
        assert settings.allowed_origins == ["http://localhost:3000", "https://example.com"]
        
        # Test with spaces
        settings = Settings(allowed_origins="http://localhost:3000, https://example.com")
        assert settings.allowed_origins == ["http://localhost:3000", "https://example.com"]
        
        # Test empty string
        settings = Settings(allowed_origins="")
        assert settings.allowed_origins == []
        
        # Test single value
        settings = Settings(allowed_origins="http://localhost:3000")
        assert settings.allowed_origins == ["http://localhost:3000"]
    
    def test_cors_security_validation_production_warning(self):
        """Test CORS security validation warns about wildcards in production."""
        with patch('warnings.warn') as mock_warn:
            settings = Settings(environment="production", allowed_origins=["*"])
            assert settings.allowed_origins == ["*"]
            mock_warn.assert_called_once()
            assert "wildcard" in mock_warn.call_args[0][0].lower()
    
    def test_environment_validation(self):
        """Test environment validation."""
        # Valid environments
        for env in ["development", "staging", "production"]:
            settings = Settings(environment=env)
            assert settings.environment == env
        
        # Invalid environment
        with pytest.raises(ValidationError):
            Settings(environment="invalid")
    
    def test_log_level_validation(self):
        """Test log level validation."""
        # Valid log levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            settings = Settings(log_level=level)
            assert settings.log_level == level
        
        # Case insensitive
        settings = Settings(log_level="debug")
        assert settings.log_level == "DEBUG"
        
        # Invalid log level
        with pytest.raises(ValidationError):
            Settings(log_level="INVALID")
    
    def test_secret_key_validation_warning(self):
        """Test secret key validation warns about short keys."""
        with patch('warnings.warn') as mock_warn:
            settings = Settings(secret_key="short")
            assert settings.secret_key == "short"
            mock_warn.assert_called_once()
            assert "32 characters" in mock_warn.call_args[0][0]
    
    def test_properties(self):
        """Test convenience properties."""
        dev_settings = Settings(environment="development")
        assert dev_settings.is_development is True
        assert dev_settings.is_production is False
        
        prod_settings = Settings(environment="production")
        assert prod_settings.is_development is False
        assert prod_settings.is_production is True
    
    def test_get_cors_origins_method(self):
        """Test get_cors_origins method with environment-specific behavior."""
        # Development with empty origins
        dev_settings = Settings(environment="development", allowed_origins=[])
        assert dev_settings.get_cors_origins() == ["http://localhost:8000", "http://127.0.0.1:8000"]
        
        # Development with specified origins
        dev_settings = Settings(environment="development", allowed_origins=["http://localhost:3000"])
        assert dev_settings.get_cors_origins() == ["http://localhost:3000"]
        
        # Production with wildcard (should be restricted)
        prod_settings = Settings(environment="production", allowed_origins=["*"])
        assert prod_settings.get_cors_origins() == ["https://yourdomain.com"]
        
        # Production with specific origins
        prod_settings = Settings(environment="production", allowed_origins=["https://example.com"])
        assert prod_settings.get_cors_origins() == ["https://example.com"]


class TestSettingsCache:
    """Test settings caching functionality."""
    
    def test_get_settings_caching(self):
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        
        # Should be the same instance due to caching
        assert settings1 is settings2
    
    @patch.dict(os.environ, {"APP_NAME": "CachedApp"})
    def test_settings_cache_with_env_vars(self):
        """Test settings caching with environment variables."""
        # Clear the cache first
        get_settings.cache_clear()
        
        settings = get_settings()
        assert settings.app_name == "CachedApp"


class TestConfigValidation:
    """Test configuration validation edge cases."""
    
    def test_positive_integer_validation(self):
        """Test that positive integer fields are validated."""
        # Valid values
        settings = Settings(max_url_length=1000, port=8080)
        assert settings.max_url_length == 1000
        assert settings.port == 8080
        
        # Invalid values (should raise ValidationError)
        with pytest.raises(ValidationError):
            Settings(max_url_length=0)
        
        with pytest.raises(ValidationError):
            Settings(max_url_length=-1)
    
    def test_database_url_default(self):
        """Test database URL default value."""
        settings = Settings()
        assert settings.database_url == "sqlite+aiosqlite:///./savemylinks.db"
    
    def test_rate_limiting_defaults(self):
        """Test rate limiting default values."""
        settings = Settings()
        assert settings.rate_limit_enabled is True
        assert settings.rate_limit_requests == 100
        assert settings.rate_limit_window == 60


class TestEnvironmentSpecificBehavior:
    """Test environment-specific configuration behavior."""
    
    def test_development_defaults(self):
        """Test development environment defaults."""
        settings = Settings(environment="development")
        assert settings.debug is False  # Still requires explicit setting
        assert settings.is_development is True
        assert settings.get_cors_origins() == ["http://localhost:8000", "http://127.0.0.1:8000"]
    
    def test_production_security_warnings(self):
        """Test production environment security warnings."""
        with patch('warnings.warn') as mock_warn:
            Settings(
                environment="production",
                allowed_origins=["*"],
                secret_key="short"
            )
            
            # Should have warnings for both CORS and secret key
            assert mock_warn.call_count >= 2