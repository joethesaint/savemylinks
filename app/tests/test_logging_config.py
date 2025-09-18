"""
Tests for logging configuration module.

This module tests the logging configuration and sensitive data redaction.
Following the development rule: Use pytest for all testing with proper async support.
"""

import pytest
import logging
import json
from unittest.mock import patch, MagicMock
from io import StringIO

from app.logging_config import (
    JSONFormatter,
    ColoredFormatter,
    PerformanceFilter,
    SecurityFilter,
    setup_logging,
    get_logger,
    log_performance,
    log_security_event,
    log_api_request
)


class TestJSONFormatter:
    """Test cases for JSONFormatter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = JSONFormatter()

    def test_format_basic_record(self):
        """Test formatting of basic log record."""
        import logging
        import json
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = self.formatter.format(record)
        parsed = json.loads(formatted)
        
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test_logger"
        assert parsed["message"] == "Test message"
        assert "timestamp" in parsed

    def test_format_with_exception(self):
        """Test formatting with exception info."""
        import logging
        import json
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
            
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=exc_info
            )
            
            formatted = self.formatter.format(record)
            parsed = json.loads(formatted)
            
            assert parsed["level"] == "ERROR"
            assert "exception" in parsed
            assert "ValueError" in parsed["exception"]


class TestColoredFormatter:
    """Test cases for ColoredFormatter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = ColoredFormatter()

    def test_format_with_colors(self):
        """Test formatting with color codes."""
        import logging
        
        # Create formatter with a format string that includes levelname
        formatter = ColoredFormatter("%(levelname)s - %(message)s")
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        # The ColoredFormatter should include color codes for the level name
        assert 'ERROR' in formatted  # The level name should be present
        assert '\033[31m' in formatted  # Red color for ERROR
        assert '\033[0m' in formatted   # Reset color


class TestSecurityFilter:
    """Test cases for SecurityFilter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.filter = SecurityFilter()

    def test_redact_sensitive_data_password(self):
        """Test redaction of password fields."""
        import logging
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="User login with password=secret123",
            args=(),
            exc_info=None
        )
        
        # The SecurityFilter modifies the record in place
        result = self.filter.filter(record)
        assert result is True
        # Check if the message was redacted
        message = record.getMessage()
        assert "***REDACTED***" in message
        assert "secret123" not in message

    def test_redact_sensitive_data_token(self):
        """Test redaction of token fields."""
        import logging
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Authorization token=abc123def",
            args=(),
            exc_info=None
        )
        
        self.filter.filter(record)
        assert "***REDACTED***" in record.getMessage()
        assert "abc123def" not in record.getMessage()


class TestPerformanceFilter:
    """Test cases for PerformanceFilter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.filter = PerformanceFilter()

    def test_filter_performance_record(self):
        """Test filtering performance records."""
        import logging
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Performance metric",
            args=(),
            exc_info=None
        )
        record.request_id = "123"
        
        result = self.filter.filter(record)
        assert result is True
        assert record.context == "performance"


class TestLoggingSetup:
    """Test cases for logging setup functions."""

    def test_setup_logging(self):
        """Test setup_logging function."""
        # This should not raise any exceptions
        setup_logging()
        
        # Verify that loggers are configured
        logger = get_logger("test")
        assert logger is not None
        assert isinstance(logger, logging.Logger)

    def test_get_logger(self):
        """Test get_logger function."""
        logger = get_logger("test_module")
        assert logger is not None
        assert logger.name == "test_module"
        assert isinstance(logger, logging.Logger)


class TestLoggingIntegration:
    """Test cases for logging integration functions."""

    def test_log_performance(self):
        """Test log_performance function."""
        logger = get_logger("test_performance")
        # This should not raise any exceptions
        log_performance(
            logger=logger,
            operation="test_operation",
            duration=0.1,
            endpoint="/test",
            method="GET"
        )

    def test_log_security_event(self):
        """Test log_security_event function."""
        logger = get_logger("test_security")
        # This should not raise any exceptions
        log_security_event(
            logger=logger,
            event_type="login_attempt",
            message="User login attempt",
            user_id="test_user",
            ip_address="127.0.0.1",
            success=True
        )

    def test_log_api_request(self):
        """Test log_api_request function."""
        logger = get_logger("test_api")
        # This should not raise any exceptions
        log_api_request(
            logger=logger,
            method="GET",
            path="/test",
            status_code=200,
            duration=0.1
        )