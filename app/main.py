"""
Main FastAPI application for SaveMyLinks.

This module sets up the FastAPI application with middleware, database initialization,
and route registration following the established architecture patterns.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.database import create_tables, drop_tables
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
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