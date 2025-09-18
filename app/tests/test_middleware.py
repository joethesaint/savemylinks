"""
Tests for middleware functionality.

This module tests the various middleware components including rate limiting,
security headers, and request logging.
"""

import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from app.middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware
)
from app.exceptions import RateLimitError


class TestRateLimitMiddleware:
    """Test rate limiting middleware."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app with rate limiting."""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        return app
    
    @pytest.fixture
    def rate_limit_middleware(self, app):
        """Create rate limit middleware instance."""
        return RateLimitMiddleware(app, requests_per_window=5, window_seconds=60)
    
    @pytest.fixture
    def client(self, app, rate_limit_middleware):
        """Create test client with middleware."""
        app.add_middleware(RateLimitMiddleware, requests_per_window=5, window_seconds=60)
        return TestClient(app)
    
    def test_get_client_ip_forwarded_for(self, rate_limit_middleware):
        """Test getting client IP from X-Forwarded-For header."""
        request = Mock()
        request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        request.client = None
        
        ip = rate_limit_middleware._get_client_ip(request)
        assert ip == "192.168.1.1"
    
    def test_get_client_ip_real_ip(self, rate_limit_middleware):
        """Test getting client IP from X-Real-IP header."""
        request = Mock()
        request.headers = {"X-Real-IP": "192.168.1.2"}
        request.client = None
        
        ip = rate_limit_middleware._get_client_ip(request)
        assert ip == "192.168.1.2"
    
    def test_get_client_ip_direct(self, rate_limit_middleware):
        """Test getting client IP from direct connection."""
        request = Mock()
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.3"
        
        ip = rate_limit_middleware._get_client_ip(request)
        assert ip == "192.168.1.3"
    
    def test_get_client_ip_unknown(self, rate_limit_middleware):
        """Test getting client IP when unknown."""
        request = Mock()
        request.headers = {}
        request.client = None
        
        ip = rate_limit_middleware._get_client_ip(request)
        assert ip == "unknown"
    
    def test_is_allowed_under_limit(self, rate_limit_middleware):
        """Test request is allowed when under rate limit."""
        client_ip = "192.168.1.1"
        
        # Record some requests (under limit)
        for _ in range(3):
            rate_limit_middleware._record_request(client_ip)
        
        assert rate_limit_middleware._is_allowed(client_ip) is True
    
    def test_is_allowed_at_limit(self, rate_limit_middleware):
        """Test request is not allowed when at rate limit."""
        client_ip = "192.168.1.2"
        
        # Record requests up to limit
        for _ in range(5):
            rate_limit_middleware._record_request(client_ip)
        
        assert rate_limit_middleware._is_allowed(client_ip) is False
    
    def test_is_allowed_old_requests_cleaned(self, rate_limit_middleware):
        """Test old requests are cleaned from rate limit tracking."""
        client_ip = "192.168.1.3"
        
        # Mock time to simulate old requests
        with patch('time.time') as mock_time:
            # Record requests in the past
            mock_time.return_value = 1000
            for _ in range(5):
                rate_limit_middleware._record_request(client_ip)
            
            # Move time forward beyond window
            mock_time.return_value = 1000 + rate_limit_middleware.window_seconds + 1
            
            # Should be allowed now (old requests cleaned)
            assert rate_limit_middleware._is_allowed(client_ip) is True
    
    def test_get_remaining_requests(self, rate_limit_middleware):
        """Test getting remaining requests count."""
        client_ip = "192.168.1.4"
        
        # Record some requests
        for _ in range(2):
            rate_limit_middleware._record_request(client_ip)
        
        remaining = rate_limit_middleware._get_remaining_requests(client_ip)
        assert remaining == 3  # 5 - 2 = 3
    
    def test_get_remaining_requests_zero(self, rate_limit_middleware):
        """Test remaining requests is zero when at limit."""
        client_ip = "192.168.1.5"
        
        # Record requests up to limit
        for _ in range(6):  # More than limit
            rate_limit_middleware._record_request(client_ip)
        
        remaining = rate_limit_middleware._get_remaining_requests(client_ip)
        assert remaining == 0
    
    @patch('app.middleware.get_settings')
    def test_rate_limit_disabled(self, mock_get_settings, client):
        """Test rate limiting is bypassed when disabled."""
        # Mock settings to disable rate limiting
        mock_settings = Mock()
        mock_settings.rate_limit_enabled = False
        mock_get_settings.return_value = mock_settings
        
        # Should allow many requests
        for _ in range(10):
            response = client.get("/test")
            assert response.status_code == 200


class TestSecurityHeadersMiddleware:
    """Test security headers middleware."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client with security headers middleware."""
        app.add_middleware(SecurityHeadersMiddleware)
        return TestClient(app)
    
    @patch('app.config.get_settings')
    def test_security_headers_development(self, mock_get_settings, client):
        """Test security headers in development environment."""
        mock_settings = Mock()
        mock_settings.is_production.return_value = False
        mock_settings.is_development.return_value = True
        mock_get_settings.return_value = mock_settings
        
        response = client.get("/test")
        
        # Check basic security headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        
        # Should not have HSTS in development
        assert "Strict-Transport-Security" not in response.headers
        
        # Should have relaxed CSP for development
        csp = response.headers["Content-Security-Policy"]
        assert "'unsafe-eval'" in csp
        assert "ws: wss:" in csp
    
    @patch('app.middleware.get_settings')
    def test_security_headers_production(self, mock_get_settings, client):
        """Test security headers in production environment."""
        mock_settings = Mock()
        mock_settings.is_production.return_value = True
        mock_settings.is_development.return_value = False
        mock_get_settings.return_value = mock_settings
        
        response = client.get("/test")
        
        # Should have HSTS in production
        assert "Strict-Transport-Security" in response.headers
        hsts = response.headers["Strict-Transport-Security"]
        assert "max-age=31536000" in hsts
        assert "includeSubDomains" in hsts
        assert "preload" in hsts
        
        # Should have strict CSP
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp


class TestRequestLoggingMiddleware:
    """Test request logging middleware."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        @app.get("/error")
        async def error_endpoint():
            raise Exception("Test error")
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client with request logging middleware."""
        app.add_middleware(RequestLoggingMiddleware)
        return TestClient(app)
    
    def test_request_logging_success(self, client):
        """Test successful request logging."""
        with patch('app.middleware.log_api_request') as mock_log:
            response = client.get("/test")
            
            assert response.status_code == 200
            
            # Check that request was logged
            mock_log.assert_called()
            
            # Check response has timing headers
            assert "X-Request-ID" in response.headers
            assert "X-Response-Time" in response.headers
    
    def test_request_logging_error(self, client):
        """Test error request logging."""
        with patch('app.middleware.logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            # The error endpoint will raise an exception, which gets re-raised by middleware
            # This is expected behavior - the middleware logs and re-raises
            with pytest.raises(Exception, match="Test error"):
                client.get("/error")
            
            # Check that error was logged
            mock_logger.error.assert_called()
    
    def test_request_id_generation(self, client):
        """Test request ID is generated and unique."""
        response1 = client.get("/test")
        response2 = client.get("/test")
        
        request_id1 = response1.headers.get("X-Request-ID")
        request_id2 = response2.headers.get("X-Request-ID")
        
        assert request_id1 is not None
        assert request_id2 is not None
        assert request_id1 != request_id2
    
    def test_response_time_header(self, client):
        """Test response time header is added."""
        response = client.get("/test")
        
        response_time = response.headers.get("X-Response-Time")
        assert response_time is not None
        
        # Should be a valid float value
        time_value = float(response_time.replace("ms", ""))
        assert time_value >= 0