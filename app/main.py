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
    description="""
    ## SaveMyLinks - Link Management API
    
    A comprehensive link management application that allows you to save, organize, and manage your favorite links with automatic metadata extraction.
    
    ### Features
    - **Link Management**: Create, read, update, and delete links
    - **Automatic Metadata**: Extract titles, descriptions, and images from URLs
    - **Categorization**: Organize links with categories and tags
    - **Search & Filter**: Find links by title, description, category, or tags
    - **Bulk Operations**: Import/export and bulk delete functionality
    - **Link Preview**: Rich metadata display with thumbnails
    
    ### Authentication
    This API currently operates without authentication. In production, consider implementing proper authentication and authorization.
    
    ### Rate Limiting
    No rate limiting is currently implemented. Consider adding rate limiting for production use.
    
    ### Error Handling
    The API uses standard HTTP status codes and returns structured error responses with detailed messages.
    """,
    version="1.0.0",
    contact={
        "name": "SaveMyLinks Support",
        "email": "support@savemylinks.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "resources",
            "description": "Operations with links/resources. Create, read, update, delete, and manage your saved links.",
        },
        {
            "name": "metadata",
            "description": "Link metadata operations. Extract and refresh metadata from URLs.",
        },
        {
            "name": "categories",
            "description": "Category management. Get available categories for organizing links.",
        },
        {
            "name": "tags",
            "description": "Tag management. Get available tags for organizing links.",
        },
        {
            "name": "export",
            "description": "Data export operations. Export your links in various formats.",
        },
        {
            "name": "health",
            "description": "Health check and system status endpoints.",
        }
    ],
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
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


@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Simple health status with service information
    """
    return {"status": "healthy", "service": "SaveMyLinks", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )