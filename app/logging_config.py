"""
Logging Configuration for SaveMyLinks Application

This module provides comprehensive logging configuration with structured logging,
file rotation, and environment-specific settings. It supports both console and
file logging with proper formatting and performance considerations.

Key Features:
- Structured logging with JSON format for production
- Automatic log rotation with size and time-based rotation
- Environment-specific log levels and formats
- Performance logging for API endpoints
- Security event logging
- Centralized logger management
"""

import os
import sys
import logging
import logging.handlers
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pathlib import Path
import json

from app.config import get_settings


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    
    Formats log records as JSON objects with consistent structure
    for better parsing and analysis in production environments.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            str: JSON-formatted log message
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "lineno", "funcName", "created",
                "msecs", "relativeCreated", "thread", "threadName",
                "processName", "process", "getMessage", "exc_info",
                "exc_text", "stack_info"
            }:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str)


class ColoredFormatter(logging.Formatter):
    """
    Colored formatter for console output in development.
    
    Provides color-coded log levels for better readability
    during development and debugging.
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with colors.
        
        Args:
            record: Log record to format
            
        Returns:
            str: Color-formatted log message
        """
        # Add color to level name
        level_color = self.COLORS.get(record.levelname, '')
        reset_color = self.COLORS['RESET']
        
        # Create colored level name
        colored_level = f"{level_color}{record.levelname}{reset_color}"
        
        # Replace level name in format
        original_levelname = record.levelname
        record.levelname = colored_level
        
        # Format the message
        formatted = super().format(record)
        
        # Restore original level name
        record.levelname = original_levelname
        
        return formatted


class PerformanceFilter(logging.Filter):
    """
    Filter for performance-related log records.
    
    Adds performance metrics and request information
    to log records for API monitoring.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter and enhance performance log records.
        
        Args:
            record: Log record to filter
            
        Returns:
            bool: True if record should be logged
        """
        # Add performance context if available
        if hasattr(record, 'request_id'):
            record.context = 'performance'
        
        return True


class SecurityFilter(logging.Filter):
    """
    Filter for security-related log records.
    
    Enhances security events with additional context
    and ensures sensitive information is not logged.
    """
    
    SENSITIVE_FIELDS = {
        'password', 'token', 'secret', 'key', 'authorization',
        'cookie', 'session', 'csrf', 'api_key'
    }
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter and sanitize security log records.
        
        Args:
            record: Log record to filter
            
        Returns:
            bool: True if record should be logged
        """
        import re
        
        # Get the original message (preserve casing)
        original_message = record.getMessage()
        
        # Check for sensitive fields and mask their values
        redacted_message = original_message
        for field in self.SENSITIVE_FIELDS:
            # Build regex pattern to match field followed by separators and capture the value
            # Pattern matches: field_name followed by optional whitespace, then : or =, 
            # then optional whitespace, then optional quotes, then the value, then optional closing quotes
            pattern = rf'(?i)(\b{re.escape(field)}\b\s*[:=]\s*)(["\']?)([^"\'\\\s,}}]+)(\2)'
            
            def replace_value(match):
                return f"{match.group(1)}{match.group(2)}***REDACTED***{match.group(4)}"
            
            redacted_message = re.sub(pattern, replace_value, redacted_message)
        
        # Update the record message with redacted version
        if redacted_message != original_message:
            record.msg = redacted_message
            # Clear args to prevent re-formatting with original values
            record.args = ()
        
        # Add security context
        if hasattr(record, 'security_event'):
            record.context = 'security'
        
        return True


def setup_logging() -> None:
    """
    Set up application logging configuration.
    
    Configures loggers, handlers, and formatters based on
    application settings and environment.
    """
    settings = get_settings()
    
    # Create logs directory if it doesn't exist
    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level))
    
    if settings.is_development():
        # Use colored formatter for development
        console_format = (
            "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
        )
        console_formatter = ColoredFormatter(console_format)
    else:
        # Use JSON formatter for production
        console_formatter = JSONFormatter()
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if configured)
    if settings.log_file:
        if settings.log_rotation:
            # Rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                filename=settings.log_file,
                maxBytes=_parse_size(settings.log_max_size),
                backupCount=settings.log_backup_count,
                encoding='utf-8'
            )
        else:
            # Simple file handler
            file_handler = logging.FileHandler(
                filename=settings.log_file,
                encoding='utf-8'
            )
        
        file_handler.setLevel(getattr(logging, settings.log_level))
        
        # Always use JSON format for file logging
        file_formatter = JSONFormatter()
        file_handler.setFormatter(file_formatter)
        
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    _configure_application_loggers()
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "environment": settings.environment,
            "log_level": settings.log_level,
            "log_file": settings.log_file,
            "log_rotation": settings.log_rotation
        }
    )


def _parse_size(size_str: str) -> int:
    """
    Parse size string to bytes.
    
    Args:
        size_str: Size string (e.g., "10MB", "1GB")
        
    Returns:
        int: Size in bytes
    """
    size_str = size_str.upper().strip()
    
    if size_str.endswith('KB'):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith('MB'):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('GB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    else:
        # Assume bytes
        return int(size_str)


def _configure_application_loggers() -> None:
    """Configure application-specific loggers."""
    
    # FastAPI/Uvicorn loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    
    # SQLAlchemy logger
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    
    # Application loggers
    app_logger = logging.getLogger("app")
    app_logger.addFilter(PerformanceFilter())
    app_logger.addFilter(SecurityFilter())


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


def log_performance(
    logger: logging.Logger,
    operation: str,
    duration: float,
    **kwargs
) -> None:
    """
    Log performance metrics.
    
    Args:
        logger: Logger instance
        operation: Operation name
        duration: Operation duration in seconds
        **kwargs: Additional context
    """
    logger.info(
        f"Performance: {operation} completed in {duration:.3f}s",
        extra={
            "performance": True,
            "operation": operation,
            "duration": duration,
            **kwargs
        }
    )


def log_security_event(
    logger: logging.Logger,
    event_type: str,
    message: str,
    **kwargs
) -> None:
    """
    Log security events.
    
    Args:
        logger: Logger instance
        event_type: Type of security event
        message: Event message
        **kwargs: Additional context
    """
    logger.warning(
        f"Security Event [{event_type}]: {message}",
        extra={
            "security_event": True,
            "event_type": event_type,
            **kwargs
        }
    )


def log_api_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration: float,
    **kwargs
) -> None:
    """
    Log API request details.
    
    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration: Request duration in seconds
        **kwargs: Additional context
    """
    level = logging.INFO if status_code < 400 else logging.WARNING
    
    logger.log(
        level,
        f"{method} {path} - {status_code} ({duration:.3f}s)",
        extra={
            "api_request": True,
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration": duration,
            **kwargs
        }
    )


# Context managers for structured logging
class LogContext:
    """
    Context manager for adding structured context to log records.
    
    Usage:
        with LogContext(request_id="123", user_id="456"):
            logger.info("Processing request")
    """
    
    def __init__(self, **context):
        """
        Initialize log context.
        
        Args:
            **context: Context fields to add to log records
        """
        self.context = context
        self.old_factory = None
    
    def __enter__(self):
        """Enter context manager."""
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        logging.setLogRecordFactory(self.old_factory)


# Export commonly used functions
__all__ = [
    "setup_logging",
    "get_logger",
    "log_performance",
    "log_security_event",
    "log_api_request",
    "LogContext",
    "JSONFormatter",
    "ColoredFormatter"
]