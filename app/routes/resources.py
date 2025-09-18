"""
FastAPI routes for resource management.

This module implements REST API endpoints for CRUD operations on resources.
Following the architecture rule: Use async routes with proper dependency injection.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.crud import resource_crud
from app.schemas import (
    Resource,
    ResourceCreate,
    ResourceUpdate,
    ResourceList,
    MessageResponse,
    ErrorResponse
)

router = APIRouter(prefix="/api/resources", tags=["resources"])


@router.post(
    "/",
    response_model=Resource,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse, "description": "URL already exists"},
        422: {"model": ErrorResponse, "description": "Validation error"}
    }
)
async def create_resource(
    resource_data: ResourceCreate,
    db: AsyncSession = Depends(get_db)
) -> Resource:
    """
    Create a new resource.
    
    Args:
        resource_data: Resource creation data
        db: Database session
        
    Returns:
        Created resource
        
    Raises:
        HTTPException: If URL already exists or validation fails
    """
    try:
        db_resource = await resource_crud.create(db, resource_data)
        return Resource.model_validate(db_resource)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A resource with this URL already exists"
        )


@router.get(
    "/",
    response_model=ResourceList,
    responses={
        200: {"model": ResourceList, "description": "List of resources"}
    }
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
        page: Page number (1-based)
        per_page: Number of resources per page
        category: Optional category filter
        search: Optional search term
        db: Database session
        
    Returns:
        Paginated list of resources
    """
    skip = (page - 1) * per_page
    resources, total = await resource_crud.get_all(
        db, skip=skip, limit=per_page, category=category, search=search
    )
    
    return ResourceList(
        resources=[Resource.model_validate(resource) for resource in resources],
        total=total,
        page=page,
        per_page=per_page
    )


@router.get(
    "/categories",
    response_model=list[str],
    responses={
        200: {"model": list[str], "description": "List of unique categories"}
    }
)
async def get_categories(db: AsyncSession = Depends(get_db)) -> list[str]:
    """
    Get all unique categories.
    
    Args:
        db: Database session
        
    Returns:
        List of unique categories
    """
    return await resource_crud.get_categories(db)


@router.get(
    "/{resource_id}",
    response_model=Resource,
    responses={
        404: {"model": ErrorResponse, "description": "Resource not found"}
    }
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
        422: {"model": ErrorResponse, "description": "Validation error"}
    }
)
async def update_resource(
    resource_id: int,
    resource_data: ResourceUpdate,
    db: AsyncSession = Depends(get_db)
) -> Resource:
    """
    Update a resource.
    
    Args:
        resource_id: Resource ID
        resource_data: Resource update data
        db: Database session
        
    Returns:
        Updated resource
        
    Raises:
        HTTPException: If resource not found, URL conflict, or validation fails
    """
    try:
        db_resource = await resource_crud.update(db, resource_id, resource_data)
        if not db_resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found"
            )
        
        return Resource.model_validate(db_resource)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A resource with this URL already exists"
        )


@router.delete(
    "/{resource_id}",
    response_model=MessageResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Resource not found"}
    }
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
    deleted = await resource_crud.delete(db, resource_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )
    
    return MessageResponse(message="Resource deleted successfully")