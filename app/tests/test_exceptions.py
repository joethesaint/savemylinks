"""
Tests for exception handling functionality.

This module tests the custom exception hierarchy, error handlers,
and utility functions for the SaveMyLinks application.
Following the development rule: Use pytest for all testing with proper async support.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse

from app.exceptions import (
    # Base exceptions
    SaveMyLinksException,
    
    # Business logic exceptions
    ValidationError,
    NotFoundError,
    DuplicateError,
    PermissionError,
    AuthenticationError,
    
    # Database exceptions
    DatabaseError,
    DatabaseConnectionError,
    DatabaseIntegrityError,
    
    # External service exceptions
    ExternalServiceError,
    RateLimitError,
    
    # Configuration exceptions
    ConfigurationError,
    
    # Link-specific exceptions
    LinkError,
    InvalidURLError,
    URLNotAccessibleError,
    LinkNotFoundError,
    
    # Handlers and utilities
    format_error_response,
    global_exception_handler,
    custom_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    register_exception_handlers,
    raise_not_found,
    raise_validation_error,
    raise_duplicate_error
)


class TestBaseException:
    """Test SaveMyLinksException base class."""
    
    def test_base_exception_creation(self):
        """Test creating base exception."""
        exc = SaveMyLinksException("Test message")
        
        assert str(exc) == "Test message"
        assert exc.message == "Test message"
        assert exc.error_code == "SaveMyLinksException"
        assert exc.details == {}
        assert exc.status_code == 500
    
    def test_base_exception_with_details(self):
        """Test base exception with custom details."""
        details = {"field": "value", "context": "test"}
        exc = SaveMyLinksException(
            "Test message",
            error_code="CUSTOM_ERROR",
            details=details,
            status_code=400
        )
        
        assert exc.message == "Test message"
        assert exc.error_code == "CUSTOM_ERROR"
        assert exc.details == details
        assert exc.status_code == 400


class TestBusinessLogicExceptions:
    """Test business logic exception classes."""
    
    def test_authentication_error(self):
        """Test AuthenticationError exception."""
        exc = AuthenticationError()
        
        assert exc.message == "Authentication required"
        assert exc.status_code == 401
        
        # Test with custom message
        exc_custom = AuthenticationError("Invalid token")
        assert exc_custom.message == "Invalid token"


class TestDatabaseExceptions:
    """Test database exception classes."""
    
    def test_database_error(self):
        """Test DatabaseError exception."""
        exc = DatabaseError("Connection failed", operation="SELECT")
        
        assert exc.message == "Connection failed"
        assert exc.status_code == 500
        assert exc.details["operation"] == "SELECT"
    
    def test_database_error_no_operation(self):
        """Test DatabaseError without operation."""
        exc = DatabaseError("Connection failed")
        
        assert exc.message == "Connection failed"
        assert "operation" not in exc.details
    
    def test_database_connection_error(self):
        """Test DatabaseConnectionError exception."""
        exc = DatabaseConnectionError()
        
        assert exc.message == "Database connection failed"
        assert exc.status_code == 500
        
        # Test with custom message
        exc_custom = DatabaseConnectionError("Timeout")
        assert exc_custom.message == "Timeout"
    
    def test_database_integrity_error(self):
        """Test DatabaseIntegrityError exception."""
        exc = DatabaseIntegrityError("Constraint violation", constraint="unique_email")
        
        assert exc.message == "Constraint violation"
        assert exc.status_code == 409
        assert exc.details["constraint"] == "unique_email"


class TestExternalServiceExceptions:
    """Test external service exception classes."""
    
    def test_external_service_error(self):
        """Test ExternalServiceError exception."""
        exc = ExternalServiceError("API", "Service unavailable", status_code=503)
        
        assert "API error: Service unavailable" in exc.message
        assert exc.status_code == 503
        assert exc.details["service"] == "API"
    
    def test_external_service_error_default_status(self):
        """Test ExternalServiceError with default status code."""
        exc = ExternalServiceError("API", "Service error")
        
        assert exc.status_code == 502
    
    def test_rate_limit_error(self):
        """Test RateLimitError exception."""
        exc = RateLimitError(retry_after=60)
        
        assert exc.message == "Rate limit exceeded"
        assert exc.status_code == 429
        assert exc.details["retry_after"] == 60
    
    def test_rate_limit_error_no_retry(self):
        """Test RateLimitError without retry_after."""
        exc = RateLimitError("Too many requests")
        
        assert exc.message == "Too many requests"
        assert "retry_after" not in exc.details


class TestConfigurationExceptions:
    """Test configuration exception classes."""
    
    def test_configuration_error(self):
        """Test ConfigurationError exception."""
        exc = ConfigurationError("DATABASE_URL", "Invalid format")
        
        assert "Configuration error for 'DATABASE_URL': Invalid format" in exc.message
        assert exc.details["setting"] == "DATABASE_URL"


class TestLinkExceptions:
    """Test link-specific exception classes."""
    
    def test_link_error(self):
        """Test LinkError base class."""
        exc = LinkError("Link error")
        
        assert exc.message == "Link error"
        assert isinstance(exc, SaveMyLinksException)
    
    def test_invalid_url_error(self):
        """Test InvalidURLError exception."""
        url = "invalid-url"
        exc = InvalidURLError(url)
        
        assert f"Invalid URL format: {url}" in exc.message
        assert exc.status_code == 400
        assert exc.details["url"] == url
    
    def test_url_not_accessible_error(self):
        """Test URLNotAccessibleError exception."""
        url = "https://example.com"
        reason = "Connection timeout"
        exc = URLNotAccessibleError(url, reason)
        
        assert f"URL not accessible: {url} - {reason}" in exc.message
        assert exc.status_code == 400
        assert exc.details["url"] == url
        assert exc.details["reason"] == reason
    
    def test_link_not_found_error(self):
        """Test LinkNotFoundError exception."""
        link_id = 123
        exc = LinkNotFoundError(link_id)
        
        assert "Link with identifier '123' not found" in exc.message
        assert exc.status_code == 404
        assert exc.details["resource"] == "Link"
        assert exc.details["identifier"] == "123"


class TestErrorResponseFormatting:
    """Test error response formatting."""
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request object."""
        request = Mock(spec=Request)
        request.url.path = "/test/path"
        request.method = "GET"
        request.state = Mock()
        request.state.timestamp = "2023-01-01T00:00:00Z"
        return request
    
    @patch('app.config.get_settings')
    def test_format_custom_exception(self, mock_get_settings, mock_request):
        """Test formatting custom exception."""
        mock_settings = Mock()
        mock_settings.is_development.return_value = True
        mock_get_settings.return_value = mock_settings
        
        exc = ValidationError("Invalid input", field="email")
        response = format_error_response(exc, mock_request, include_details=True)
        
        assert response["error"] is True
        assert response["message"] == "Invalid input"
        assert response["error_code"] == "ValidationError"
        assert response["details"]["field"] == "email"
        assert response["path"] == "/test/path"
        assert response["method"] == "GET"
    
    @patch('app.config.get_settings')
    def test_format_http_exception(self, mock_get_settings, mock_request):
        """Test formatting HTTP exception."""
        mock_settings = Mock()
        mock_get_settings.return_value = mock_settings
        
        exc = HTTPException(status_code=404, detail="Not found")
        response = format_error_response(exc, mock_request)
        
        assert response["message"] == "Not found"
        assert response["error_code"] == "HTTP_404"
    
    @patch('app.config.get_settings')
    def test_format_validation_error(self, mock_get_settings, mock_request):
        """Test formatting validation error."""
        mock_settings = Mock()
        mock_settings.is_development.return_value = True
        mock_get_settings.return_value = mock_settings
        
        # Mock validation error
        exc = Mock(spec=RequestValidationError)
        exc.errors.return_value = [{"field": "email", "message": "Invalid format"}]
        
        response = format_error_response(exc, mock_request, include_details=True)
        
        assert response["message"] == "Validation error"
        assert response["error_code"] == "VALIDATION_ERROR"
        assert "validation_errors" in response["details"]
    
    @patch('app.config.get_settings')
    def test_format_generic_exception_development(self, mock_get_settings, mock_request):
        """Test formatting generic exception in development."""
        mock_settings = Mock()
        mock_settings.is_development.return_value = True
        mock_get_settings.return_value = mock_settings
        
        exc = ValueError("Test error")
        response = format_error_response(exc, mock_request, include_details=True)
        
        assert response["message"] == "Test error"
        assert response["error_code"] == "ValueError"
        assert "traceback" in response["details"]
    
    @patch('app.exceptions.get_settings')
    def test_format_generic_exception_production(self, mock_get_settings, mock_request):
        """Test formatting generic exception in production."""
        mock_settings = Mock()
        mock_settings.is_development.return_value = False
        mock_get_settings.return_value = mock_settings
        
        exc = ValueError("Test error")
        response = format_error_response(exc, mock_request)
        
        assert response["message"] == "Internal server error"
        assert response["error_code"] == "INTERNAL_ERROR"


class TestExceptionHandlers:
    """Test exception handler functions."""
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request object."""
        request = Mock(spec=Request)
        request.url.path = "/test"
        request.method = "POST"
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "test-agent"}
        request.state = Mock()
        request.state.timestamp = "2023-01-01T00:00:00Z"
        return request
    
    @pytest.mark.asyncio
    @patch('app.config.get_settings')
    async def test_global_exception_handler(self, mock_get_settings, mock_request):
        """Test global exception handler."""
        mock_settings = Mock()
        mock_settings.is_development.return_value = True
        mock_get_settings.return_value = mock_settings
        
        exc = ValueError("Test error")
        
        with patch('logging.getLogger') as mock_logger:
            response = await global_exception_handler(mock_request, exc)
            
            assert isinstance(response, JSONResponse)
            assert response.status_code == 500
            
            # Check logging was called
            mock_logger.return_value.error.assert_called()
    
    @pytest.mark.asyncio
    @patch('app.config.get_settings')
    async def test_custom_exception_handler_server_error(self, mock_get_settings, mock_request):
        """Test custom exception handler for server errors."""
        mock_settings = Mock()
        mock_settings.is_development.return_value = True
        mock_get_settings.return_value = mock_settings
        
        exc = DatabaseError("Connection failed")
        
        with patch('logging.getLogger') as mock_logger:
            response = await custom_exception_handler(mock_request, exc)
            
            assert isinstance(response, JSONResponse)
            assert response.status_code == 500
            
            # Check error logging
            mock_logger.return_value.error.assert_called()
    
    @pytest.mark.asyncio
    @patch('app.config.get_settings')
    async def test_custom_exception_handler_client_error(self, mock_get_settings, mock_request):
        """Test custom exception handler for client errors."""
        mock_settings = Mock()
        mock_settings.is_development.return_value = True
        mock_get_settings.return_value = mock_settings
        
        exc = ValidationError("Invalid input")
        
        with patch('logging.getLogger') as mock_logger:
            response = await custom_exception_handler(mock_request, exc)
            
            assert isinstance(response, JSONResponse)
            assert response.status_code == 400
            
            # Check warning logging
            mock_logger.return_value.warning.assert_called()
    
    @pytest.mark.asyncio
    async def test_http_exception_handler(self, mock_request):
        """Test HTTP exception handler."""
        exc = HTTPException(status_code=404, detail="Not found")
        
        with patch('logging.getLogger') as mock_logger:
            response = await http_exception_handler(mock_request, exc)
            
            assert isinstance(response, JSONResponse)
            assert response.status_code == 404
            
            # Check warning logging for 4xx
            mock_logger.return_value.warning.assert_called()
    
    @pytest.mark.asyncio
    async def test_http_exception_handler_server_error(self, mock_request):
        """Test HTTP exception handler for server errors."""
        exc = HTTPException(status_code=500, detail="Internal error")
        
        with patch('logging.getLogger') as mock_logger:
            response = await http_exception_handler(mock_request, exc)
            
            assert isinstance(response, JSONResponse)
            assert response.status_code == 500
            
            # Check error logging for 5xx
            mock_logger.return_value.error.assert_called()
    
    @pytest.mark.asyncio
    @patch('app.config.get_settings')
    async def test_validation_exception_handler(self, mock_get_settings, mock_request):
        """Test validation exception handler."""
        mock_settings = Mock()
        mock_settings.is_development.return_value = True
        mock_get_settings.return_value = mock_settings
        
        # Mock validation error
        exc = Mock(spec=RequestValidationError)
        exc.errors.return_value = [{"field": "email", "message": "Invalid"}]
        
        with patch('logging.getLogger') as mock_logger:
            response = await validation_exception_handler(mock_request, exc)
            
            assert isinstance(response, JSONResponse)
            assert response.status_code == 422
            
            # Check warning logging
            mock_logger.return_value.warning.assert_called()


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_raise_not_found(self):
        """Test raise_not_found utility."""
        with pytest.raises(NotFoundError) as exc_info:
            raise_not_found("User", 123)
        
        exc = exc_info.value
        assert "User with identifier '123' not found" in exc.message
        assert exc.status_code == 404
    
    def test_raise_validation_error(self):
        """Test raise_validation_error utility."""
        with pytest.raises(ValidationError) as exc_info:
            raise_validation_error("Invalid input", field="email")
        
        exc = exc_info.value
        assert exc.message == "Invalid input"
        assert exc.details["field"] == "email"
    
    def test_raise_validation_error_no_field(self):
        """Test raise_validation_error without field."""
        with pytest.raises(ValidationError) as exc_info:
            raise_validation_error("Invalid input")
        
        exc = exc_info.value
        assert exc.message == "Invalid input"
        assert "field" not in exc.details
    
    def test_raise_duplicate_error(self):
        """Test raise_duplicate_error utility."""
        with pytest.raises(DuplicateError) as exc_info:
            raise_duplicate_error("User", "email", "test@example.com")
        
        exc = exc_info.value
        assert "User with email 'test@example.com' already exists" in exc.message
        assert exc.status_code == 409


class TestExceptionHandlerRegistration:
    """Test exception handler registration."""
    
    def test_register_exception_handlers(self):
        """Test registering exception handlers with FastAPI app."""
        mock_app = Mock()
        
        register_exception_handlers(mock_app)
        
        # Check that all handlers were registered
        assert mock_app.add_exception_handler.call_count == 5
        
        # Check specific handler registrations
        calls = mock_app.add_exception_handler.call_args_list
        
        # Extract exception types from calls
        registered_exceptions = [call[0][0] for call in calls]
        
        assert SaveMyLinksException in registered_exceptions
        assert HTTPException in registered_exceptions
        assert StarletteHTTPException in registered_exceptions
        assert RequestValidationError in registered_exceptions
        assert Exception in registered_exceptions


class TestCustomExceptions:
    """Test cases for custom exception classes."""

    def test_savemylinks_exception_base(self):
        """Test base SaveMyLinksException."""
        exc = SaveMyLinksException("Test error", "TEST_001")
        
        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.error_code == "TEST_001"
        assert exc.details == {}

    def test_savemylinks_exception_with_details(self):
        """Test SaveMyLinksException with details."""
        details = {"field": "value", "context": "test"}
        exc = SaveMyLinksException("Test error", "TEST_001", details)
        
        assert exc.details == details

class TestValidationError:
    """Test ValidationError exception."""
    
    def test_validation_error(self):
        """Test basic validation error."""
        exc = ValidationError("Invalid input")
        assert exc.message == "Invalid input"
        assert exc.status_code == 400
        assert exc.error_code == "ValidationError"
    
    def test_validation_error_with_field(self):
        """Test validation error with field."""
        exc = ValidationError("Invalid URL", field="url")
        assert exc.message == "Invalid URL"
        assert exc.details["field"] == "url"


class TestNotFoundError:
    """Test NotFoundError exception."""
    
    def test_not_found_error(self):
        """Test not found error."""
        exc = NotFoundError("Resource", "123")
        assert "Resource with identifier '123' not found" in exc.message
        assert exc.status_code == 404
        assert exc.details["resource"] == "Resource"
        assert exc.details["identifier"] == "123"


class TestDuplicateError:
    """Test DuplicateError exception."""
    
    def test_duplicate_error(self):
        """Test duplicate error."""
        exc = DuplicateError("Resource", "url", "http://example.com")
        assert "Resource with url 'http://example.com' already exists" in exc.message
        assert exc.status_code == 409
        assert exc.details["resource"] == "Resource"
        assert exc.details["field"] == "url"
        assert exc.details["value"] == "http://example.com"


class TestPermissionError:
    """Test PermissionError exception."""
    
    def test_permission_error(self):
        """Test permission error."""
        exc = PermissionError()
        assert exc.message == "Insufficient permissions"
        assert exc.status_code == 403
    
    def test_permission_error_custom_message(self):
        """Test permission error with custom message."""
        exc = PermissionError("Access denied")
        assert exc.message == "Access denied"
        assert exc.status_code == 403