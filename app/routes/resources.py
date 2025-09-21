"""
API routes for resource management in SaveMyLinks application.

This module defines FastAPI routes for CRUD operations on resources
with link preview metadata support and bulk operations.
"""

import logging
from typing import List, Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import json
import csv
import io
import socket
import ipaddress
from urllib.parse import urlparse, urljoin
import httpx
from bs4 import BeautifulSoup

from app.database import get_db
from app.crud import resource_crud
from app.schemas import (
    Resource, 
    ResourceCreate, 
    ResourceUpdate, 
    ResourceList, 
    MessageResponse,
    LinkPreviewMetadata,
    ErrorResponse,
    URLRequest,
    MetadataResponse
)
from app.services.background_tasks import extract_metadata_background, refresh_metadata_background

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/resources", tags=["resources"])


@router.post(
    "/",
    response_model=Resource,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse, "description": "URL already exists"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Create a new resource",
    description="Create a new link resource with optional automatic metadata extraction from the provided URL."
)
async def create_resource(
    resource_data: ResourceCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    extract_metadata: bool = Query(True, description="Whether to extract metadata from URL")
) -> Resource:
    """
    Create a new resource with optional metadata extraction.
    
    Args:
        resource_data: Resource creation data
        background_tasks: FastAPI background tasks
        db: Database session
        extract_metadata: Whether to extract metadata (default: True)
        
    Returns:
        Created resource with metadata if extraction was successful
        
    Raises:
        HTTPException: If URL already exists (409) or validation fails (422)
    """
    try:
        # Create resource with optional immediate metadata extraction
        resource = await resource_crud.create(
            db, 
            obj_in=resource_data, 
            extract_metadata=extract_metadata
        )
        
        # If metadata extraction is enabled but no metadata exists,
        # schedule it as a background task
        if extract_metadata and not resource.link_metadata:
            background_tasks.add_task(extract_metadata_background, resource.id)
        
        return resource
        
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Integrity error creating resource: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A resource with this URL already exists"
        )
    except ValueError as e:
        logger.error(f"Validation error creating resource: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error creating resource: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the resource"
        )


@router.get(
    "/",
    response_model=ResourceList,
    responses={
        200: {"model": ResourceList, "description": "List of resources"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Get paginated resources",
    description="Retrieve a paginated list of resources with optional filtering by category and search terms.",
    tags=["resources"]
)
async def get_resources(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Resources per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    db: AsyncSession = Depends(get_db)
) -> ResourceList:
    """
    Get paginated list of resources with optional filtering.
    
    Args:
        page: Page number (starts from 1)
        per_page: Number of resources per page (1-100)
        category: Optional category filter
        search: Optional search term for title and description
        db: Database session
        
    Returns:
        Paginated list of resources with metadata
        
    Raises:
        HTTPException: If database error occurs
    """
    try:
        resources = await resource_crud.get_multi_with_filters(
            db, 
            skip=(page - 1) * per_page, 
            limit=per_page,
            category=category,
            search=search
        )
        
        total = await resource_crud.count_with_filters(
            db, 
            category=category, 
            search=search
        )
        
        return ResourceList(
            resources=[Resource.model_validate(resource) for resource in resources],
            total=total,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        logger.error(f"Error retrieving resources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving resources"
        )


@router.get(
    "/tags",
    response_model=list[str],
    responses={
        200: {"model": list[str], "description": "List of unique tags"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Get all tags",
    description="Retrieve a list of all unique tags used across resources for filtering and organization.",
    tags=["tags"]
)
async def get_tags(db: AsyncSession = Depends(get_db)) -> list[str]:
    """
    Get all unique tags.
    
    Args:
        db: Database session
        
    Returns:
        List of unique tags
        
    Raises:
        HTTPException: If database error occurs
    """
    try:
        return await resource_crud.get_tags(db)
    except Exception as e:
        logger.error(f"Error retrieving tags: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving tags"
        )


@router.get(
    "/categories",
    response_model=list[str],
    responses={
        200: {"model": list[str], "description": "List of unique categories"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Get all categories",
    description="Retrieve a list of all unique categories used across resources for filtering and organization.",
    tags=["categories"]
)
async def get_categories(db: AsyncSession = Depends(get_db)) -> list[str]:
    """
    Get all unique categories.
    
    Args:
        db: Database session
        
    Returns:
        List of unique categories
        
    Raises:
        HTTPException: If database error occurs
    """
    try:
        return await resource_crud.get_categories(db)
    except Exception as e:
        logger.error(f"Error retrieving categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving categories"
        )


@router.get(
    "/export",
    summary="Export resources",
    description="Export all resources in JSON or CSV format with optional filtering by category and search terms.",
    tags=["export"],
    responses={
        200: {"description": "Exported data in requested format"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def export_resources(
    format: Literal["json", "csv"] = Query("json", description="Export format (json or csv)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    db: AsyncSession = Depends(get_db)
):
    """
    Export resources in JSON or CSV format.
    
    Args:
        format: Export format (json or csv)
        category: Optional category filter
        search: Optional search term
        db: Database session
        
    Returns:
        Exported data in requested format
    """
    
    # Get all resources (no pagination for export)
    resources, _ = await resource_crud.get_all(
        db, skip=0, limit=10000, category=category, search=search
    )
    
    if format == "json":
        # Export as JSON
        export_data = [Resource.model_validate(resource).model_dump() for resource in resources]
        return JSONResponse(
            content=export_data,
            headers={"Content-Disposition": "attachment; filename=savemylinks_export.json"}
        )
    
    elif format == "csv":
        # Export as CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(["id", "title", "url", "description", "category", "created_at", "updated_at"])
        
        # Write data
        for resource in resources:
            writer.writerow([
                resource.id,
                resource.title,
                resource.url,
                resource.description or "",
                resource.category or "",
                resource.created_at.isoformat() if resource.created_at else "",
                resource.updated_at.isoformat() if resource.updated_at else ""
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=savemylinks_export.csv"}
        )


@router.get(
    "/{resource_id}",
    response_model=Resource,
    responses={
        404: {"model": ErrorResponse, "description": "Resource not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Get resource by ID",
    description="Retrieve a specific resource by its unique identifier.",
    tags=["resources"]
)
async def get_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db)
) -> Resource:
    """
    Get a resource by ID.
    
    Args:
        resource_id: Resource ID
        db: Database session
        
    Returns:
        Resource data
        
    Raises:
        HTTPException: If resource not found
    """
    db_resource = await resource_crud.get_by_id(db, resource_id)
    if not db_resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )
    
    return Resource.model_validate(db_resource)


@router.put(
    "/{resource_id}",
    response_model=Resource,
    responses={
        404: {"model": ErrorResponse, "description": "Resource not found"},
        409: {"model": ErrorResponse, "description": "URL already exists"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Update resource",
    description="Update an existing resource with optional metadata refresh if the URL is changed.",
    tags=["resources"]
)
async def update_resource(
    resource_id: int,
    resource_data: ResourceUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    refresh_metadata: bool = Query(False, description="Whether to refresh metadata if URL changed")
) -> Resource:
    """
    Update an existing resource with optional metadata refresh.
    
    Args:
        resource_id: Resource ID to update
        resource_data: Resource update data
        background_tasks: FastAPI background tasks
        db: Database session
        refresh_metadata: Whether to refresh metadata if URL changed
        
    Returns:
        Updated resource instance
        
    Raises:
        HTTPException: If resource not found (404)
    """
    try:
        # Get existing resource
        resource = await resource_crud.get_by_id(db, resource_id=resource_id)
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found"
            )
        
        # Update resource
        updated_resource = await resource_crud.update(
            db, 
            db_obj=resource, 
            obj_in=resource_data,
            refresh_metadata=refresh_metadata
        )
        
        # If metadata refresh is enabled but failed during update,
        # schedule it as a background task
        if refresh_metadata and 'url' in resource_data.model_dump(exclude_unset=True):
            if not updated_resource.link_metadata or updated_resource.link_metadata.get('status') == 'failed':
                background_tasks.add_task(refresh_metadata_background, resource_id)
        
        return updated_resource
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Integrity error updating resource {resource_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A resource with this URL already exists"
        )
    except ValueError as e:
        logger.error(f"Validation error updating resource {resource_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error updating resource {resource_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating the resource"
        )


@router.post(
    "/{resource_id}/refresh-metadata", 
    response_model=Resource,
    summary="Refresh resource metadata",
    description="Manually refresh the link preview metadata for a specific resource. This is useful when metadata extraction failed initially or when the target page has been updated.",
    tags=["metadata"],
    responses={
        404: {"model": ErrorResponse, "description": "Resource not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def refresh_resource_metadata(
    resource_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> Resource:
    """
    Refresh metadata for an existing resource.
    
    This endpoint allows manual refresh of link preview metadata
    for resources that may have outdated or missing metadata.
    
    Args:
        resource_id: Resource ID to refresh metadata for
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        Resource with refreshed metadata
        
    Raises:
        HTTPException: If resource not found (404)
    """
    try:
        # Get existing resource
        resource = await resource_crud.get_by_id(db, resource_id=resource_id)
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found"
            )
        
        # Schedule metadata refresh as background task
        background_tasks.add_task(refresh_metadata_background, resource_id)
        
        return resource
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error refreshing metadata for resource {resource_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while refreshing resource metadata"
        )


@router.get(
    "/{resource_id}/metadata", 
    response_model=Optional[LinkPreviewMetadata],
    summary="Get resource metadata",
    description="Retrieve the link preview metadata for a specific resource, including title, description, and image information.",
    tags=["metadata"],
    responses={
        200: {"model": Optional[LinkPreviewMetadata], "description": "Resource metadata or null if not available"},
        404: {"model": ErrorResponse, "description": "Resource not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_resource_metadata(
    resource_id: int,
    db: AsyncSession = Depends(get_db)
) -> Optional[LinkPreviewMetadata]:
    """
    Get link preview metadata for a specific resource.
    
    Args:
        resource_id: Resource ID to get metadata for
        db: Database session
        
    Returns:
        Link preview metadata or None if not available
        
    Raises:
        HTTPException: If resource not found (404)
    """
    resource = await resource_crud.get_by_id(db, resource_id=resource_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )
    
    if resource.link_metadata:
        try:
            return LinkPreviewMetadata(**resource.link_metadata)
        except Exception:
            return None
    
    return None


@router.delete(
    "/{resource_id}",
    response_model=MessageResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Resource not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Delete resource",
    description="Permanently delete a resource by its unique identifier.",
    tags=["resources"]
)
async def delete_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Delete a resource.
    
    Args:
        resource_id: Resource ID
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If resource not found
    """
    try:
        deleted = await resource_crud.delete(db, resource_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found"
            )
        
        return MessageResponse(message="Resource deleted successfully")
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error deleting resource {resource_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the resource"
        )


async def is_safe_url(url: str) -> bool:
    """
    Check if a URL is safe to fetch (prevents SSRF attacks).
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL is safe to fetch, False otherwise
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        
        if not hostname:
            return False
            
        # Resolve hostname to IP address
        try:
            ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip)
            
            # Check if IP is private, reserved, or loopback
            if (ip_obj.is_private or 
                ip_obj.is_reserved or 
                ip_obj.is_loopback or 
                ip_obj.is_multicast or
                ip_obj.is_link_local):
                return False
                
        except (socket.gaierror, ValueError):
            return False
            
        # Additional hostname checks
        hostname_lower = hostname.lower()
        blocked_hosts = [
            'localhost', '127.0.0.1', '0.0.0.0',
            'metadata.google.internal',  # GCP metadata
            '169.254.169.254',  # AWS/Azure metadata
        ]
        
        if hostname_lower in blocked_hosts:
            return False
            
        return True
        
    except Exception:
        return False


async def fetch_metadata(url: str) -> dict:
    """
    Fetch and extract metadata from a URL with security checks.
    
    Args:
        url: URL to extract metadata from
        
    Returns:
        Dictionary containing extracted metadata
        
    Raises:
        HTTPException: If URL is unsafe or extraction fails
    """
    # Security check
    if not await is_safe_url(url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL is not allowed for security reasons"
        )
    
    try:
        async with httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; SaveMyLinks/1.0; +https://github.com/joethesaint/savemylinks)"
            },
            follow_redirects=True,
            timeout=10.0
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Extract metadata with fallback hierarchy
            metadata = {}
            
            # Title extraction: og:title -> twitter:title -> <title>
            title = None
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content')
            else:
                twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
                if twitter_title:
                    title = twitter_title.get('content')
                else:
                    title_tag = soup.find('title')
                    if title_tag:
                        title = title_tag.get_text().strip()
            
            metadata['title'] = title
            
            # Description extraction: og:description -> twitter:description -> meta description
            description = None
            og_desc = soup.find('meta', property='og:description')
            if og_desc:
                description = og_desc.get('content')
            else:
                twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
                if twitter_desc:
                    description = twitter_desc.get('content')
                else:
                    meta_desc = soup.find('meta', attrs={'name': 'description'})
                    if meta_desc:
                        description = meta_desc.get('content')
            
            metadata['description'] = description
            
            # Image extraction: og:image -> twitter:image
            image = None
            og_image = soup.find('meta', property='og:image')
            if og_image:
                image = og_image.get('content')
            else:
                twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
                if twitter_image:
                    image = twitter_image.get('content')
            
            # Convert relative URLs to absolute
            if image:
                image = urljoin(url, image)
            metadata['image'] = image
            
            # Favicon extraction: link rel="icon" -> link rel="shortcut icon" -> /favicon.ico
            favicon = None
            icon_link = soup.find('link', rel='icon')
            if icon_link:
                favicon = icon_link.get('href')
            else:
                shortcut_icon = soup.find('link', rel='shortcut icon')
                if shortcut_icon:
                    favicon = shortcut_icon.get('href')
                else:
                    # Fallback to /favicon.ico
                    parsed_url = urlparse(url)
                    favicon = f"{parsed_url.scheme}://{parsed_url.netloc}/favicon.ico"
            
            # Convert relative URLs to absolute
            if favicon:
                favicon = urljoin(url, favicon)
            metadata['favicon'] = favicon
            
            return metadata
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Request timeout while fetching URL"
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"HTTP error {e.response.status_code} while fetching URL"
        )
    except Exception as e:
        logger.error(f"Error extracting metadata from {url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract metadata from URL"
        )


@router.post(
    "/extract-metadata",
    response_model=MetadataResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid URL or security restriction"},
        408: {"model": ErrorResponse, "description": "Request timeout"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Extract metadata from URL",
    description="Extract title, description, image, and favicon from a given URL with security protections against SSRF attacks."
)
async def extract_url_metadata(request: URLRequest) -> MetadataResponse:
    """
    Extract metadata from a URL for link preview functionality.
    
    Args:
        request: URL request containing the URL to extract metadata from
        
    Returns:
        Extracted metadata including title, description, image, and favicon
        
    Raises:
        HTTPException: If URL is unsafe, unreachable, or extraction fails
    """
    metadata = await fetch_metadata(str(request.url))
    return MetadataResponse(**metadata)