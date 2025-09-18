"""
Custom Exception Handling for SaveMyLinks Application

This module provides a comprehensive exception hierarchy and global error handlers
for the SaveMyLinks application. It includes custom exceptions for different
error scenarios, structured error responses, and automatic error logging.

Key Features:
- Custom exception hierarchy with specific error types
- Global exception handlers for FastAPI
- Structured error responses with consistent format
- Automatic error logging with context
- Development vs production error detail handling
- HTTP status code mapping for different exception types
"""

import traceback
from typing import Dict, Any, Optional, Union
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

from app.config import get_settings


# Base Exception Classes
class SaveMyLinksException(Exception):
    """
    Base exception class for SaveMyLinks application.
    
    All custom exceptions should inherit from this class to ensure
    consistent error handling and logging.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        """
        Initialize base exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
            status_code: HTTP status code
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.status_code = status_code


# Business Logic Exceptions
class ValidationError(SaveMyLinksException):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(message, status_code=400, **kwargs)
        if field:
            self.details["field"] = field


class NotFoundError(SaveMyLinksException):
    """Exception raised when a resource is not found."""
    
    def __init__(self, resource: str, identifier: Union[str, int], **kwargs):
        message = f"{resource} with identifier '{identifier}' not found"
        super().__init__(message, status_code=404, **kwargs)
        self.details.update({
            "resource": resource,
            "identifier": str(identifier)
        })


class DuplicateError(SaveMyLinksException):
    """Exception raised when trying to create a duplicate resource."""
    
    def __init__(self, resource: str, field: str, value: str, **kwargs):
        message = f"{resource} with {field} '{value}' already exists"
        super().__init__(message, status_code=409, **kwargs)
        self.details.update({
            "resource": resource,
            "field": field,
            "value": value
        })


class PermissionError(SaveMyLinksException):
    """Exception raised for permission/authorization errors."""
    
    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        super().__init__(message, status_code=403, **kwargs)


class AuthenticationError(SaveMyLinksException):
    """Exception raised for authentication errors."""
    
    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(message, status_code=401, **kwargs)


# Database Exceptions
class DatabaseError(SaveMyLinksException):
    """Exception raised for database-related errors."""
    
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        super().__init__(message, status_code=500, **kwargs)
        if operation:
            self.details["operation"] = operation


class DatabaseConnectionError(DatabaseError):
    """Exception raised for database connection errors."""
    
    def __init__(self, message: str = "Database connection failed", **kwargs):
        super().__init__(message, **kwargs)


class DatabaseIntegrityError(DatabaseError):
    """Exception raised for database integrity constraint violations."""
    
    def __init__(self, message: str, constraint: Optional[str] = None, **kwargs):
        super().__init__(message, status_code=409, **kwargs)
        if constraint:
            self.details["constraint"] = constraint


# External Service Exceptions
class ExternalServiceError(SaveMyLinksException):
    """Exception raised for external service errors."""
    
    def __init__(
        self,
        service: str,
        message: str,
        status_code: int = 502,
        **kwargs
    ):
        super().__init__(f"{service} error: {message}", status_code=status_code, **kwargs)
        self.details["service"] = service


class RateLimitError(SaveMyLinksException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, status_code=429, **kwargs)
        if retry_after:
            self.details["retry_after"] = retry_after


# Configuration Exceptions
class ConfigurationError(SaveMyLinksException):
    """Exception raised for configuration errors."""
    
    def __init__(self, setting: str, message: str, **kwargs):
        super().__init__(f"Configuration error for '{setting}': {message}", **kwargs)
        self.details["setting"] = setting


# Link-specific Exceptions
class LinkError(SaveMyLinksException):
    """Base exception for link-related errors."""
    pass


class InvalidURLError(LinkError):
    """Exception raised for invalid URL format."""
    
    def __init__(self, url: str, **kwargs):
        message = f"Invalid URL format: {url}"
        super().__init__(message, status_code=400, **kwargs)
        self.details["url"] = url


class URLNotAccessibleError(LinkError):
    """Exception raised when URL is not accessible."""
    
    def __init__(self, url: str, reason: str, **kwargs):
        message = f"URL not accessible: {url} - {reason}"
        super().__init__(message, status_code=400, **kwargs)
        self.details.update({
            "url": url,
            "reason": reason
        })


class LinkNotFoundError(NotFoundError):
    """Exception raised when a link is not found."""
    
    def __init__(self, link_id: Union[str, int], **kwargs):
        super().__init__("Link", link_id, **kwargs)


# Error Response Formatting
def format_error_response(
    error: Exception,
    request: Request,
    include_details: bool = False
) -> Dict[str, Any]:
    """
    Format error response with consistent structure.
    
    Args:
        error: Exception instance
        request: FastAPI request object
        include_details: Whether to include detailed error information
        
    Returns:
        Dict: Formatted error response
    """
    settings = get_settings()
    
    # Base error response
    response = {
        "error": True,
        "message": "An error occurred",
        "timestamp": str(request.state.timestamp) if hasattr(request.state, 'timestamp') else None,
        "path": str(request.url.path),
        "method": request.method
    }
    
    # Handle custom exceptions
    if isinstance(error, SaveMyLinksException):
        response.update({
            "message": error.message,
            "error_code": error.error_code,
            "details": error.details if include_details else {}
        })
    
    # Handle HTTP exceptions
    elif isinstance(error, (HTTPException, StarletteHTTPException)):
        response.update({
            "message": error.detail,
            "error_code": f"HTTP_{error.status_code}"
        })
    
    # Handle validation errors
    elif isinstance(error, RequestValidationError):
        response.update({
            "message": "Validation error",
            "error_code": "VALIDATION_ERROR",
            "details": {
                "validation_errors": error.errors()
            } if include_details else {}
        })
    
    # Handle generic exceptions
    else:
        if settings.is_development():
            response.update({
                "message": str(error),
                "error_code": error.__class__.__name__,
                "details": {
                    "traceback": traceback.format_exc()
                } if include_details else {}
            })
        else:
            response.update({
                "message": "Internal server error",
                "error_code": "INTERNAL_ERROR"
            })
    
    return response


# Global Exception Handlers
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for all unhandled exceptions.
    
    Args:
        request: FastAPI request object
        exc: Exception instance
        
    Returns:
        JSONResponse: Formatted error response
    """
    logger = logging.getLogger(__name__)
    settings = get_settings()
    
    # Log the exception
    logger.error(
        f"Unhandled exception: {exc}",
        extra={
            "exception_type": exc.__class__.__name__,
            "path": str(request.url.path),
            "method": request.method,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "traceback": traceback.format_exc()
        },
        exc_info=True
    )
    
    # Determine status code
    status_code = getattr(exc, 'status_code', 500)
    
    # Format response
    response_data = format_error_response(
        exc,
        request,
        include_details=settings.is_development()
    )
    
    return JSONResponse(
        status_code=status_code,
        content=response_data
    )


async def custom_exception_handler(request: Request, exc: SaveMyLinksException) -> JSONResponse:
    """
    Handler for custom SaveMyLinks exceptions.
    
    Args:
        request: FastAPI request object
        exc: Custom exception instance
        
    Returns:
        JSONResponse: Formatted error response
    """
    logger = logging.getLogger(__name__)
    settings = get_settings()
    
    # Log based on severity
    if exc.status_code >= 500:
        logger.error(
            f"Server error: {exc.message}",
            extra={
                "error_code": exc.error_code,
                "details": exc.details,
                "path": str(request.url.path),
                "method": request.method
            },
            exc_info=True
        )
    elif exc.status_code >= 400:
        logger.warning(
            f"Client error: {exc.message}",
            extra={
                "error_code": exc.error_code,
                "details": exc.details,
                "path": str(request.url.path),
                "method": request.method
            }
        )
    
    # Format response
    response_data = format_error_response(
        exc,
        request,
        include_details=settings.is_development()
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handler for HTTP exceptions.
    
    Args:
        request: FastAPI request object
        exc: HTTP exception instance
        
    Returns:
        JSONResponse: Formatted error response
    """
    logger = logging.getLogger(__name__)
    
    # Log HTTP errors
    if exc.status_code >= 500:
        logger.error(
            f"HTTP {exc.status_code}: {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "path": str(request.url.path),
                "method": request.method
            }
        )
    elif exc.status_code >= 400:
        logger.warning(
            f"HTTP {exc.status_code}: {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "path": str(request.url.path),
                "method": request.method
            }
        )
    
    # Format response
    response_data = format_error_response(exc, request)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handler for request validation errors.
    
    Args:
        request: FastAPI request object
        exc: Validation error instance
        
    Returns:
        JSONResponse: Formatted error response
    """
    logger = logging.getLogger(__name__)
    settings = get_settings()
    
    # Log validation errors
    logger.warning(
        f"Validation error: {exc}",
        extra={
            "validation_errors": exc.errors(),
            "path": str(request.url.path),
            "method": request.method
        }
    )
    
    # Format response
    response_data = format_error_response(
        exc,
        request,
        include_details=settings.is_development()
    )
    
    return JSONResponse(
        status_code=422,
        content=response_data
    )


# Exception Handler Registration
def register_exception_handlers(app):
    """
    Register all exception handlers with the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(SaveMyLinksException, custom_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)


# Utility Functions
def raise_not_found(resource: str, identifier: Union[str, int]) -> None:
    """
    Convenience function to raise NotFoundError.
    
    Args:
        resource: Resource type
        identifier: Resource identifier
    """
    raise NotFoundError(resource, identifier)


def raise_validation_error(message: str, field: Optional[str] = None) -> None:
    """
    Convenience function to raise ValidationError.
    
    Args:
        message: Error message
        field: Field name (optional)
    """
    raise ValidationError(message, field)


def raise_duplicate_error(resource: str, field: str, value: str) -> None:
    """
    Convenience function to raise DuplicateError.
    
    Args:
        resource: Resource type
        field: Field name
        value: Field value
    """
    raise DuplicateError(resource, field, value)


# Export all exception classes and handlers
__all__ = [
    # Base exceptions
    "SaveMyLinksException",
    
    # Business logic exceptions
    "ValidationError",
    "NotFoundError", 
    "DuplicateError",
    "PermissionError",
    "AuthenticationError",
    
    # Database exceptions
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseIntegrityError",
    
    # External service exceptions
    "ExternalServiceError",
    "RateLimitError",
    
    # Configuration exceptions
    "ConfigurationError",
    
    # Link-specific exceptions
    "LinkError",
    "InvalidURLError",
    "URLNotAccessibleError",
    "LinkNotFoundError",
    
    # Handlers and utilities
    "register_exception_handlers",
    "format_error_response",
    "raise_not_found",
    "raise_validation_error",
    "raise_duplicate_error"
]