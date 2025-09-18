"""
Pydantic schemas for SaveMyLinks application.

This module defines the data validation schemas for request bodies and response models.
Following the architecture rule: Use Pydantic schemas for all data validation,
never use ORM models directly in endpoints.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl, Field, ConfigDict


class ResourceBase(BaseModel):
    """Base schema with common resource fields."""
    title: str = Field(..., min_length=1, max_length=200, description="Display title for the resource")
    url: HttpUrl = Field(..., description="The actual URL/link")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description of the resource")
    category: Optional[str] = Field(None, max_length=100, description="Optional category for organization")


class ResourceCreate(ResourceBase):
    """Schema for creating a new resource."""
    pass


class ResourceUpdate(BaseModel):
    """Schema for updating an existing resource."""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Display title for the resource")
    url: Optional[HttpUrl] = Field(None, description="The actual URL/link")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description of the resource")
    category: Optional[str] = Field(None, max_length=100, description="Optional category for organization")


class Resource(ResourceBase):
    """Schema for resource responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Unique identifier for the resource")
    created_at: datetime = Field(..., description="Timestamp when resource was created")
    updated_at: datetime = Field(..., description="Timestamp when resource was last updated")


class ResourceList(BaseModel):
    """Schema for paginated resource list responses."""
    resources: list[Resource] = Field(..., description="List of resources")
    total: int = Field(..., description="Total number of resources")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of resources per page")


class MessageResponse(BaseModel):
    """Schema for simple message responses."""
    message: str = Field(..., description="Response message")


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    detail: str = Field(..., description="Error detail message")