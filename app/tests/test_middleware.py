"""
Tests for middleware functionality.

This module tests the various middleware components including rate limiting,
security headers, CORS, and request logging.
"""

import pytest
import time
import uuid
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from app.middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware
)
from app.exceptions import RateLimitError


class TestCORSMiddleware:
    """Test CORS middleware functionality."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app with CORS middleware."""
        app = FastAPI()
        
        # Add CORS middleware with test configuration
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "https://example.com"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        @app.post("/test")
        async def test_post_endpoint():
            return {"message": "created"}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_cors_simple_request_allowed_origin(self, client):
        """Test CORS simple request with allowed origin."""
        response = client.get(
            "/test",
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert response.headers["access-control-allow-credentials"] == "true"
    
    def test_cors_simple_request_disallowed_origin(self, client):
        """Test CORS simple request with disallowed origin."""
        response = client.get(
            "/test",
            headers={"Origin": "http://malicious-site.com"}
        )
        
        # Request should succeed but no CORS headers should be present
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers
    
    def test_cors_preflight_request_allowed_origin(self, client):
        """Test CORS preflight request with allowed origin."""
        response = client.options(
            "/test",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "https://example.com"
        assert response.headers["access-control-allow-credentials"] == "true"
        assert "POST" in response.headers["access-control-allow-methods"]
        assert "content-type" in response.headers["access-control-allow-headers"].lower()
    
    def test_cors_preflight_request_disallowed_origin(self, client):
        """Test CORS preflight request with disallowed origin."""
        response = client.options(
            "/test",
            headers={
                "Origin": "http://malicious-site.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        # Preflight should fail for disallowed origins
        assert response.status_code == 400
    
    def test_cors_preflight_disallowed_method(self, client):
        """Test CORS preflight request with disallowed method."""
        response = client.options(
            "/test",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "PATCH",  # Not in allowed methods
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        # Should fail for disallowed method
        assert response.status_code == 400
    
    def test_cors_actual_request_after_preflight(self, client):
        """Test actual CORS request after successful preflight."""
        # First, preflight request
        preflight_response = client.options(
            "/test",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        assert preflight_response.status_code == 200
        
        # Then, actual request
        actual_response = client.post(
            "/test",
            headers={
                "Origin": "http://localhost:3000",
                "Content-Type": "application/json"
            },
            json={"data": "test"}
        )
        
        assert actual_response.status_code == 200
        assert actual_response.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert actual_response.headers["access-control-allow-credentials"] == "true"
    
    def test_cors_no_origin_header(self, client):
        """Test request without Origin header (same-origin request)."""
        response = client.get("/test")
        
        assert response.status_code == 200
        # No CORS headers should be present for same-origin requests
        assert "access-control-allow-origin" not in response.headers
    
    def test_cors_wildcard_origin_app(self):
        """Test CORS with wildcard origin configuration."""
        app = FastAPI()
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,  # Must be False with wildcard
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        client = TestClient(app)
        
        response = client.get(
            "/test",
            headers={"Origin": "http://any-origin.com"}
        )
        
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "*"
        # Credentials should not be allowed with wildcard
        assert "access-control-allow-credentials" not in response.headers
    
    @patch('app.config.get_settings')
    def test_cors_configuration_from_settings(self, mock_get_settings):
        """Test CORS configuration loaded from application settings."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.allowed_origins = ["http://localhost:8000", "https://myapp.com"]
        mock_settings.allow_credentials = True
        mock_settings.allowed_methods = ["GET", "POST", "PUT", "DELETE"]
        mock_settings.allowed_headers = ["Content-Type", "Authorization"]
        mock_get_settings.return_value = mock_settings
        
        # Create app with settings-based CORS
        app = FastAPI()
        settings = mock_get_settings()
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins,
            allow_credentials=settings.allow_credentials,
            allow_methods=settings.allowed_methods,
            allow_headers=settings.allowed_headers,
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        client = TestClient(app)
        
        response = client.get(
            "/test",
            headers={"Origin": "https://myapp.com"}
        )
        
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "https://myapp.com"
        assert response.headers["access-control-allow-credentials"] == "true"


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
    
    @patch('app.middleware.get_settings')
    def test_rate_limit_exceeded_response(self, mock_get_settings, client):
        """Test response when rate limit is exceeded."""
        # Mock settings to enable rate limiting
        mock_settings = Mock()
        mock_settings.rate_limit_enabled = True
        mock_get_settings.return_value = mock_settings
        
        # Make requests up to the limit
        for _ in range(5):
            response = client.get("/test")
            assert response.status_code == 200
        
        # Next request should be rate limited
        response = client.get("/test")
        assert response.status_code == 429
        assert "rate limit exceeded" in response.json()["detail"].lower()
    
    @patch('app.middleware.get_settings')
    def test_rate_limit_headers_present(self, mock_get_settings, client):
        """Test that rate limit headers are present in response."""
        # Mock settings to enable rate limiting
        mock_settings = Mock()
        mock_settings.rate_limit_enabled = True
        mock_get_settings.return_value = mock_settings
        
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        
        # Check header values
        assert int(response.headers["X-RateLimit-Limit"]) == 5
        assert int(response.headers["X-RateLimit-Remaining"]) <= 5
        assert int(response.headers["X-RateLimit-Reset"]) > 0
    
    @patch('app.middleware.get_settings')
    def test_rate_limit_different_ips(self, mock_get_settings, app):
        """Test that rate limiting is per IP address."""
        # Mock settings to enable rate limiting
        mock_settings = Mock()
        mock_settings.rate_limit_enabled = True
        mock_get_settings.return_value = mock_settings
        
        app.add_middleware(RateLimitMiddleware, requests_per_window=2, window_seconds=60)
        client = TestClient(app)
        
        # Simulate requests from different IPs
        with patch('app.middleware.RateLimitMiddleware._get_client_ip') as mock_get_ip:
            # First IP - exhaust limit
            mock_get_ip.return_value = "192.168.1.1"
            for _ in range(2):
                response = client.get("/test")
                assert response.status_code == 200
            
            # Should be rate limited
            response = client.get("/test")
            assert response.status_code == 429
            
            # Second IP - should still work
            mock_get_ip.return_value = "192.168.1.2"
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
        return TestClient(app)
    
    @patch('app.config.get_settings')
    def test_security_headers_development(self, mock_get_settings, app):
        """Test security headers in development environment."""
        mock_settings = Mock()
        mock_settings.is_development = True
        mock_settings.is_production = False
        mock_get_settings.return_value = mock_settings
        
        # Add middleware after mocking settings
        app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(app)
        
        response = client.get("/test")
        
        assert response.status_code == 200
        
        # In development, CSP should be more permissive
        csp_header = response.headers.get("Content-Security-Policy")
        assert csp_header is not None
        assert "'unsafe-eval'" in csp_header
        assert "'unsafe-inline'" in csp_header
        
        # Other security headers should still be present
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        
        # HSTS should NOT be present in development
        assert "Strict-Transport-Security" not in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers
    
    @patch('app.config.get_settings')
    def test_security_headers_production(self, mock_get_settings, app):
        """Test security headers in production environment."""
        mock_settings = Mock()
        mock_settings.is_development = False
        mock_settings.is_production = True
        mock_get_settings.return_value = mock_settings
        
        # Add middleware after mocking settings
        app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(app)
        
        response = client.get("/test")
        
        assert response.status_code == 200
        
        # In production, CSP should be strict
        csp_header = response.headers.get("Content-Security-Policy")
        assert csp_header is not None
        assert "'unsafe-eval'" not in csp_header
        assert "'unsafe-inline'" not in csp_header
        
        # All security headers should be present
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers
    
    @patch('app.config.get_settings')
    def test_csp_header_comprehensive(self, mock_get_settings, app):
        """Test comprehensive CSP header configuration."""
        mock_settings = Mock()
        mock_settings.is_development = False
        mock_settings.is_production = True
        mock_get_settings.return_value = mock_settings
        
        # Add middleware after mocking settings
        app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(app)
        
        response = client.get("/test")
        
        csp = response.headers["Content-Security-Policy"]
        
        # Check key CSP directives
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "style-src 'self'" in csp
        assert "img-src 'self' data:" in csp
        assert "font-src 'self'" in csp
        assert "connect-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "base-uri 'self'" in csp
        assert "form-action 'self'" in csp
    
    @patch('app.config.get_settings')
    def test_security_headers_all_present(self, mock_get_settings, app):
        """Test that all expected security headers are present."""
        # Mock settings for development
        mock_settings = Mock()
        mock_settings.is_development = True
        mock_settings.is_production = False
        mock_get_settings.return_value = mock_settings
        
        # Add middleware after mocking settings
        app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(app)
        
        response = client.get("/test")
        
        expected_headers = [
            "X-Content-Type-Options",
            "X-XSS-Protection", 
            "X-Frame-Options",
            "Referrer-Policy",
            "Content-Security-Policy",
            "Permissions-Policy"
        ]
        
        for header in expected_headers:
            assert header in response.headers, f"Missing security header: {header}"
    
    @patch('app.config.get_settings')
    def test_permissions_policy_header(self, mock_get_settings, app):
        """Test Permissions Policy header configuration."""
        # Mock settings for development
        mock_settings = Mock()
        mock_settings.is_development = True
        mock_settings.is_production = False
        mock_get_settings.return_value = mock_settings
        
        # Add middleware after mocking settings
        app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(app)
        
        response = client.get("/test")
        
        permissions_policy = response.headers["Permissions-Policy"]
        
        # Check key permissions are restricted
        assert "camera=()" in permissions_policy
        assert "microphone=()" in permissions_policy
        assert "geolocation=()" in permissions_policy
        assert "payment=()" in permissions_policy


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
    
    @patch('app.middleware.log_api_request')
    def test_request_logging_success(self, mock_log_api_request, app):
        """Test successful request logging."""
        # Add middleware to app
        app.add_middleware(RequestLoggingMiddleware)
        client = TestClient(app)
        
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert "X-Response-Time" in response.headers
        
        # Check that the request was logged
        mock_log_api_request.assert_called_once()
    
    @patch('app.logging_config.log_security_event')
    def test_request_logging_error(self, mock_log_security_event, app):
        """Test error request logging."""
        # Add middleware to app
        app.add_middleware(RequestLoggingMiddleware)
        client = TestClient(app)
        
        # This will cause a 500 error but the middleware should catch it
        with pytest.raises(Exception, match="Test error"):
            response = client.get("/error")
        
        # The middleware should handle the exception and add headers
        # But since the exception is re-raised, we can't check the response
        # We can only verify that the middleware processed the request
    
    def test_request_id_generation(self, app):
        """Test request ID generation and header."""
        # Add middleware to app
        app.add_middleware(RequestLoggingMiddleware)
        client = TestClient(app)
        
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        
        # Request ID should be a valid UUID
        request_id = response.headers["X-Request-ID"]
        uuid.UUID(request_id)  # This will raise ValueError if not valid UUID
    
    def test_response_time_header(self, app):
        """Test response time header."""
        # Add middleware to app
        app.add_middleware(RequestLoggingMiddleware)
        client = TestClient(app)
        
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-Response-Time" in response.headers
        
        # Response time should be in milliseconds format
        response_time = response.headers["X-Response-Time"]
        assert response_time.endswith("ms")
        
        # Should be a valid float
        time_value = float(response_time[:-2])
        assert time_value >= 0