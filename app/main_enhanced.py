"""
Enhanced FastAPI application for SaveMyLinks.

This module sets up the FastAPI application with all enhancements:
- Configuration management with Pydantic settings
- Structured logging with rotation
- Custom exception handling
- Security middleware with rate limiting
- Caching system with TTL management
- Comprehensive monitoring and health checks
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Tuple

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import our enhanced modules
from app.config import get_settings, Settings
from app.logging_config import setup_logging, log_performance, log_security_event
from app.exceptions import (
    setup_exception_handlers,
    ValidationError,
    NotFoundError,
    RateLimitError
)
from app.middleware import (
    setup_security_middleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware,
    TrustedHostMiddleware
)

# Global list to track background tasks and their stop events
background_tasks: List[Tuple[asyncio.Task, asyncio.Event]] = []
from app.cache import (
    get_cache,
    CacheManager,
    cache_maintenance_task,
    cached
)
from app.database import create_tables
from app.routes.resources import router as resources_router

# Setup logging first
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Enhanced application lifespan manager.
    
    Handles startup and shutdown events with comprehensive initialization
    and cleanup procedures.
    """
    settings = get_settings()
    
    try:
        # Startup procedures
        logger.info("Starting SaveMyLinks application...")
        
        # Initialize database
        logger.info("Initializing database...")
        await create_tables()
        
        # Initialize cache
        if settings.CACHE_ENABLED:
            logger.info("Initializing cache system...")
            cache = get_cache()
            logger.info(f"Cache initialized with max_size={cache.max_size}, default_ttl={cache.default_ttl}")
        
        # Start background tasks
        if settings.CACHE_ENABLED:
            logger.info("Starting cache maintenance task...")
            # Create stop event and start cache maintenance task
            stop_event = asyncio.Event()
            task = asyncio.create_task(periodic_cache_maintenance(stop_event))
            background_tasks.append((task, stop_event))
        
        # Log security configuration
        log_security_event(
            "application_startup",
            {
                "environment": settings.ENVIRONMENT,
                "debug_mode": settings.DEBUG,
                "cors_origins": settings.ALLOWED_ORIGINS,
                "rate_limiting": settings.RATE_LIMIT_ENABLED
            }
        )
        
        logger.info("Application startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise
    
    finally:
        # Shutdown procedures
        logger.info("Shutting down SaveMyLinks application...")
        
        # Stop all background tasks
        if background_tasks:
            logger.info(f"Stopping {len(background_tasks)} background tasks...")
            for task, stop_event in background_tasks:
                stop_event.set()
            
            # Wait for all tasks to finish
            for task, stop_event in background_tasks:
                try:
                    await task
                except Exception as e:
                    logger.error(f"Error while stopping background task: {e}")
            
            # Clear the background tasks list
            background_tasks.clear()
            logger.info("All background tasks stopped")
        
        # Clear cache if needed
        if settings.CACHE_ENABLED:
            cache_stats = await CacheManager.get_cache_stats()
            logger.info(f"Final cache stats: {cache_stats}")
        
        logger.info("Application shutdown completed")


async def periodic_cache_maintenance(stop_event: asyncio.Event):
    """
    Background task for periodic cache maintenance.
    
    Args:
        stop_event: Event to signal when the task should stop
    """
    logger = logging.getLogger(__name__)
    
    while not stop_event.is_set():
        try:
            # Wait for either the stop event or timeout (5 minutes)
            await asyncio.wait_for(stop_event.wait(), timeout=300)
            # If we reach here, stop_event was set, so break the loop
            break
        except asyncio.TimeoutError:
            # Timeout occurred, perform maintenance and continue
            try:
                await cache_maintenance_task()
            except Exception as e:
                logger.error(f"Cache maintenance error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in cache maintenance: {e}")
            break
    
    logger.info("Cache maintenance task stopped")


def create_enhanced_app() -> FastAPI:
    """
    Create and configure the enhanced FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()
    
    # Initialize FastAPI application with enhanced configuration
    app = FastAPI(
        title=settings.APP_NAME,
        description="An enhanced link management application with enterprise features",
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
        # Disable docs in production for security
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    )
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Setup security middleware
    setup_security_middleware(app, settings)
    
    # Add CORS middleware with enhanced configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=settings.ALLOW_CREDENTIALS,
        allow_methods=settings.ALLOWED_METHODS,
        allow_headers=settings.ALLOWED_HEADERS,
    )
    
    # Mount static files if enabled
    if settings.STATIC_FILES_ENABLED:
        app.mount(
            "/static",
            StaticFiles(directory=settings.STATIC_DIRECTORY),
            name="static"
        )
    
    # Initialize templates
    templates = Jinja2Templates(directory=settings.TEMPLATES_DIRECTORY)
    
    # Include API routes
    app.include_router(resources_router)
    
    # Add enhanced routes
    add_enhanced_routes(app, templates, settings)
    
    return app


def add_enhanced_routes(app: FastAPI, templates: Jinja2Templates, settings: Settings):
    """Add enhanced routes with caching and monitoring."""
    
    @app.get("/", response_class=HTMLResponse)
    @cached(ttl=60)  # Cache home page for 1 minute
    async def home(request: Request):
        """
        Enhanced home page with caching and performance monitoring.
        """
        with log_performance("home_page_render"):
            return templates.TemplateResponse(
                request,
                "index.html",
                {
                    "title": "SaveMyLinks - Home",
                    "environment": settings.ENVIRONMENT,
                    "version": settings.APP_VERSION
                }
            )
    
    @app.get("/add", response_class=HTMLResponse)
    async def add_resource_page(request: Request):
        """
        Enhanced add resource page.
        """
        return templates.TemplateResponse(
            request,
            "add.html",
            {
                "title": "Add Resource - SaveMyLinks",
                "environment": settings.ENVIRONMENT
            }
        )
    
    @app.get("/health")
    async def enhanced_health_check():
        """
        Comprehensive health check endpoint with system status.
        """
        try:
            health_data = {
                "status": "healthy",
                "service": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "environment": settings.ENVIRONMENT,
                "timestamp": log_performance.get_current_time(),
            }
            
            # Add cache health if enabled
            if settings.CACHE_ENABLED:
                cache_health = await CacheManager.health_check()
                health_data["cache"] = cache_health
            
            # Add database health (basic check)
            try:
                # This would be replaced with actual database health check
                health_data["database"] = {"status": "healthy"}
            except Exception as e:
                health_data["database"] = {"status": "unhealthy", "error": str(e)}
                health_data["status"] = "degraded"
            
            return health_data
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "service": settings.APP_NAME,
                    "error": str(e)
                }
            )
    
    @app.get("/metrics")
    async def metrics_endpoint():
        """
        Metrics endpoint for monitoring and observability.
        """
        try:
            metrics = {
                "application": {
                    "name": settings.APP_NAME,
                    "version": settings.APP_VERSION,
                    "environment": settings.ENVIRONMENT,
                    "uptime": "calculated_uptime_here"  # Would implement actual uptime calculation
                }
            }
            
            # Add cache metrics if enabled
            if settings.CACHE_ENABLED:
                cache_stats = await CacheManager.get_cache_stats()
                metrics["cache"] = cache_stats
            
            return metrics
            
        except Exception as e:
            logger.error(f"Metrics collection failed: {e}")
            raise ValidationError("Failed to collect metrics")
    
    @app.post("/admin/cache/clear")
    async def clear_cache_endpoint():
        """
        Administrative endpoint to clear cache.
        """
        if not settings.CACHE_ENABLED:
            raise ValidationError("Cache is not enabled")
        
        try:
            await CacheManager.clear_all_cache()
            log_security_event("cache_cleared", {"admin_action": True})
            return {"message": "Cache cleared successfully"}
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            raise ValidationError("Failed to clear cache")
    
    @app.get("/admin/cache/stats")
    async def cache_stats_endpoint():
        """
        Administrative endpoint to get cache statistics.
        """
        if not settings.CACHE_ENABLED:
            raise ValidationError("Cache is not enabled")
        
        try:
            stats = await CacheManager.get_cache_stats()
            return stats
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            raise ValidationError("Failed to get cache statistics")
    
    @app.post("/admin/cache/cleanup")
    async def cleanup_cache_endpoint():
        """
        Administrative endpoint to cleanup expired cache entries.
        """
        if not settings.CACHE_ENABLED:
            raise ValidationError("Cache is not enabled")
        
        try:
            cleanup_stats = await CacheManager.cleanup_expired()
            return cleanup_stats
        except Exception as e:
            logger.error(f"Failed to cleanup cache: {e}")
            raise ValidationError("Failed to cleanup cache")


# Create the enhanced application instance
app = create_enhanced_app()


# Additional utility endpoints for development
@app.get("/debug/config")
async def debug_config_endpoint(settings: Settings = Depends(get_settings)):
    """
    Debug endpoint to view current configuration (development only).
    """
    if settings.ENVIRONMENT == "production":
        raise NotFoundError("Debug endpoints not available in production")
    
    # Return safe configuration (no secrets)
    safe_config = {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "host": settings.HOST,
        "port": settings.PORT,
        "cache_enabled": settings.CACHE_ENABLED,
        "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
        "static_files_enabled": settings.STATIC_FILES_ENABLED,
        "allowed_origins": settings.ALLOWED_ORIGINS,
        "log_level": settings.LOG_LEVEL
    }
    
    return safe_config


@app.get("/debug/test-error")
async def test_error_endpoint(settings: Settings = Depends(get_settings)):
    """
    Debug endpoint to test error handling (development only).
    """
    if settings.ENVIRONMENT == "production":
        raise NotFoundError("Debug endpoints not available in production")
    
    error_type = "validation"  # Could be made configurable
    
    if error_type == "validation":
        raise ValidationError("This is a test validation error")
    elif error_type == "not_found":
        raise NotFoundError("This is a test not found error")
    elif error_type == "rate_limit":
        raise RateLimitError("This is a test rate limit error")
    else:
        raise Exception("This is a test generic error")


if __name__ == "__main__":
    settings = get_settings()
    
    # Enhanced uvicorn configuration
    uvicorn_config = {
        "app": "app.main_enhanced:app",
        "host": settings.HOST,
        "port": settings.PORT,
        "reload": settings.RELOAD and settings.ENVIRONMENT == "development",
        "log_level": settings.LOG_LEVEL.lower(),
        "access_log": True,
        "use_colors": settings.ENVIRONMENT == "development",
    }
    
    # Add SSL configuration for production
    if settings.ENVIRONMENT == "production":
        # SSL configuration would go here
        # uvicorn_config.update({
        #     "ssl_keyfile": "/path/to/keyfile.pem",
        #     "ssl_certfile": "/path/to/certfile.pem",
        # })
        pass
    
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Server: {settings.HOST}:{settings.PORT}")
    
    uvicorn.run(**uvicorn_config)