"""
Security Middleware for SaveMyLinks Application

This module provides comprehensive security middleware including rate limiting,
security headers, request/response processing, and performance monitoring.
It integrates with the application's logging and configuration systems.

Key Features:
- Rate limiting with configurable windows and limits
- Security headers (HSTS, CSP, X-Frame-Options, etc.)
- Request/response logging and timing
- CORS handling with environment-specific configuration
- Request ID generation for tracing
- IP-based rate limiting with Redis support (optional)
"""

import time
import uuid
import asyncio
from typing import Dict, Optional, Callable, Any
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import logging

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import get_settings
from app.exceptions import RateLimitError
from app.logging_config import log_api_request, log_security_event


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with in-memory storage.
    
    Implements sliding window rate limiting per IP address
    with configurable limits and time windows.
    """
    
    def __init__(self, app, requests_per_window: int = 1000, window_seconds: int = 3600):
        """
        Initialize rate limiting middleware.
        
        Args:
            app: FastAPI application
            requests_per_window: Number of requests allowed per window
            window_seconds: Time window in seconds
        """
        super().__init__(app)
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.request_counts: Dict[str, deque] = defaultdict(deque)
        self.logger = logging.getLogger(__name__)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response: HTTP response
        """
        settings = get_settings()
        
        # Skip rate limiting if disabled
        if not settings.rate_limit_enabled:
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check rate limit
        if not self._is_allowed(client_ip):
            log_security_event(
                self.logger,
                "rate_limit_exceeded",
                f"Rate limit exceeded for IP: {client_ip}",
                client_ip=client_ip,
                path=str(request.url.path),
                method=request.method
            )
            
            raise RateLimitError(
                message="Rate limit exceeded. Please try again later.",
                retry_after=self.window_seconds
            )
        
        # Record request
        self._record_request(client_ip)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self._get_remaining_requests(client_ip)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_window)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(
            int(time.time()) + self.window_seconds
        )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.
        
        Args:
            request: HTTP request
            
        Returns:
            str: Client IP address
        """
        # Check for forwarded headers (proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"
    
    def _is_allowed(self, client_ip: str) -> bool:
        """
        Check if request is allowed based on rate limit.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            bool: True if request is allowed
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        # Clean old requests
        requests = self.request_counts[client_ip]
        while requests and requests[0] < window_start:
            requests.popleft()
        
        # Check if under limit
        return len(requests) < self.requests_per_window
    
    def _record_request(self, client_ip: str) -> None:
        """
        Record a request for rate limiting.
        
        Args:
            client_ip: Client IP address
        """
        self.request_counts[client_ip].append(time.time())
    
    def _get_remaining_requests(self, client_ip: str) -> int:
        """
        Get remaining requests for client.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            int: Number of remaining requests
        """
        current_count = len(self.request_counts[client_ip])
        return max(0, self.requests_per_window - current_count)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security headers middleware.
    
    Adds security-related HTTP headers to all responses
    to improve application security posture.
    """
    
    def __init__(self, app):
        """
        Initialize security headers middleware.
        
        Args:
            app: FastAPI application
        """
        super().__init__(app)
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to response.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response: HTTP response with security headers
        """
        response = await call_next(request)
        
        # Security headers
        security_headers = self._get_security_headers()
        
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response
    
    def _get_security_headers(self) -> Dict[str, str]:
        """
        Get security headers based on environment.
        
        Returns:
            Dict: Security headers
        """
        headers = {
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Enable XSS protection
            "X-XSS-Protection": "1; mode=block",
            
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions policy
            "Permissions-Policy": (
                "geolocation=(), microphone=(), camera=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=()"
            ),
        }
        
        # Add HSTS in production
        if self.settings.is_production():
            headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        
        if self.settings.is_development():
            # Relaxed CSP for development
            csp_directives.extend([
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
                "connect-src 'self' ws: wss:"
            ])
        
        headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        return headers


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Request logging and timing middleware.
    
    Logs all requests with timing information and adds
    request IDs for tracing.
    """
    
    def __init__(self, app):
        """
        Initialize request logging middleware.
        
        Args:
            app: FastAPI application
        """
        super().__init__(app)
        self.logger = logging.getLogger(__name__)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Log request and add timing information.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response: HTTP response with timing headers
        """
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        request.state.timestamp = datetime.now(timezone.utc)
        
        # Record start time
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log failed requests
            duration = time.time() - start_time
            self.logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "duration": duration,
                    "client_ip": self._get_client_ip(request),
                    "user_agent": request.headers.get("user-agent"),
                    "exception": str(exc)
                },
                exc_info=True
            )
            raise
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Add response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration * 1000:.3f}ms"
        
        # Log successful requests
        log_api_request(
            self.logger,
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            duration=duration,
            request_id=request_id,
            client_ip=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent")
        )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.
        
        Args:
            request: HTTP request
            
        Returns:
            str: Client IP address
        """
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"


class TrustedHostMiddleware(BaseHTTPMiddleware):
    """
    Trusted host middleware for host header validation.
    
    Validates the Host header to prevent host header injection attacks.
    """
    
    def __init__(self, app, allowed_hosts: Optional[list] = None):
        """
        Initialize trusted host middleware.
        
        Args:
            app: FastAPI application
            allowed_hosts: List of allowed host patterns
        """
        super().__init__(app)
        self.allowed_hosts = allowed_hosts or ["*"]
        self.logger = logging.getLogger(__name__)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Validate host header.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response: HTTP response
        """
        if "*" not in self.allowed_hosts:
            host = request.headers.get("host", "").lower()
            
            if not any(self._match_host(host, pattern) for pattern in self.allowed_hosts):
                log_security_event(
                    self.logger,
                    "invalid_host_header",
                    f"Invalid host header: {host}",
                    host=host,
                    client_ip=request.client.host if request.client else None
                )
                
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid host header"}
                )
        
        return await call_next(request)
    
    def _match_host(self, host: str, pattern: str) -> bool:
        """
        Match host against pattern.
        
        Args:
            host: Host header value
            pattern: Host pattern (supports wildcards)
            
        Returns:
            bool: True if host matches pattern
        """
        if pattern == "*":
            return True
        
        if pattern.startswith("*."):
            # Wildcard subdomain
            domain = pattern[2:]
            return host == domain or host.endswith(f".{domain}")
        
        return host == pattern


def setup_middleware(app) -> None:
    """
    Set up all middleware for the application.
    
    Args:
        app: FastAPI application instance
    """
    settings = get_settings()
    
    # Request logging (first to capture all requests)
    app.add_middleware(RequestLoggingMiddleware)
    
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Rate limiting
    if settings.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_window=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window
        )
    
    # Trusted hosts (in production)
    if settings.is_production():
        # In production, you should configure specific allowed hosts
        allowed_hosts = ["yourdomain.com", "www.yourdomain.com"]
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    
    # CORS middleware (last to handle preflight requests)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=settings.allow_credentials,
        allow_methods=settings.allowed_methods,
        allow_headers=settings.allowed_headers,
        expose_headers=["X-Request-ID", "X-Response-Time"]
    )


# Utility functions for middleware configuration
def get_rate_limit_key(request: Request) -> str:
    """
    Generate rate limit key for request.
    
    Args:
        request: HTTP request
        
    Returns:
        str: Rate limit key
    """
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if not client_ip:
        client_ip = request.headers.get("X-Real-IP", "")
    if not client_ip:
        client_ip = request.client.host if request.client else "unknown"
    
    return f"rate_limit:{client_ip}"


def is_static_request(request: Request) -> bool:
    """
    Check if request is for static files.
    
    Args:
        request: HTTP request
        
    Returns:
        bool: True if request is for static files
    """
    static_extensions = {".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg"}
    path = str(request.url.path).lower()
    
    return any(path.endswith(ext) for ext in static_extensions)


# Export middleware classes and setup function
__all__ = [
    "RateLimitMiddleware",
    "SecurityHeadersMiddleware", 
    "RequestLoggingMiddleware",
    "TrustedHostMiddleware",
    "setup_middleware",
    "get_rate_limit_key",
    "is_static_request"
]