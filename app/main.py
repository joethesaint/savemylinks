"""
Main FastAPI application for SaveMyLinks.

This module sets up the FastAPI application with middleware, database initialization,
and route registration following the established architecture patterns.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.database import create_tables
from app.routes.resources import router as resources_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for the FastAPI application.
    Creates database tables on startup.
    """
    # Startup
    await create_tables()
    yield
    # Shutdown (if needed)


# Initialize FastAPI application
app = FastAPI(
    title="SaveMyLinks",
    description="A simple and elegant link management application",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS origins from environment variable
def get_cors_origins() -> list[str]:
    """
    Return the list of allowed CORS origins based on the ALLOWED_ORIGINS environment variable.
    
    If ALLOWED_ORIGINS is unset or empty, returns a development-safe default:
    ["http://localhost:8000", "http://127.0.0.1:8000"].
    
    ALLOWED_ORIGINS, when set, must be a comma-separated list of origins (whitespace is trimmed).
    Raises ValueError if the list contains the wildcard "*" because wildcard origins are not allowed
    when credentials are enabled.
    """
    origins_env = os.getenv("ALLOWED_ORIGINS", "")
    if not origins_env:
        # Safe default for local development
        return ["http://localhost:8000", "http://127.0.0.1:8000"]
    
    # Parse comma-separated origins from environment variable
    origins = [origin.strip() for origin in origins_env.split(",") if origin.strip()]
    
    # Security check: prevent wildcard with credentials
    if "*" in origins:
        raise ValueError(
            "Wildcard '*' in ALLOWED_ORIGINS is not allowed when credentials are enabled. "
            "Please specify explicit origins or disable credentials."
        )
    
    return origins


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (for CSS, JS, images)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

# Include API routes
app.include_router(resources_router)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Home page displaying all saved resources.
    
    Args:
        request: FastAPI request object
        
    Returns:
        HTML response with home page
    """
    return templates.TemplateResponse(
        request,
        "index.html",
        {"title": "SaveMyLinks - Home"}
    )


@app.get("/add", response_class=HTMLResponse)
async def add_resource_page(request: Request):
    """
    Add resource page with form.
    
    Args:
        request: FastAPI request object
        
    Returns:
        HTML response with add resource form
    """
    return templates.TemplateResponse(
        request,
        "add.html",
        {"title": "Add Resource - SaveMyLinks"}
    )


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Simple health status
    """
    return {"status": "healthy", "service": "SaveMyLinks"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )