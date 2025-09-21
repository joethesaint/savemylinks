"""
Pydantic schemas for SaveMyLinks application.

This module defines the data validation schemas for request bodies and response models.
Following the architecture rule: Use Pydantic schemas for all data validation,
never use ORM models directly in endpoints.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, HttpUrl, Field, ConfigDict


class URLRequest(BaseModel):
    """Schema for URL metadata extraction requests."""
    url: HttpUrl = Field(..., description="URL to extract metadata from")


class MetadataResponse(BaseModel):
    """Schema for metadata extraction response."""
    title: Optional[str] = Field(None, description="Page title")
    description: Optional[str] = Field(None, description="Page description")
    image: Optional[HttpUrl] = Field(None, description="Preview image URL")
    favicon: Optional[HttpUrl] = Field(None, description="Favicon URL")


class LinkPreviewMetadata(BaseModel):
    """Schema for link preview metadata."""
    
    model_config = ConfigDict(from_attributes=True)
    
    url: str
    status: str = Field(..., description="Extraction status: 'success' or 'failed'")
    title: Optional[str] = Field(None, description="Page title")
    description: Optional[str] = Field(None, description="Page description")
    image: Optional[HttpUrl] = Field(None, description="Preview image URL")
    site_name: Optional[str] = Field(None, description="Site name")
    type: Optional[str] = Field(None, description="Content type (e.g., 'website', 'article')")
    favicon: Optional[HttpUrl] = Field(None, description="Favicon URL")
    error: Optional[str] = Field(None, description="Error message if extraction failed")
    extracted_at: Optional[float] = Field(None, description="Timestamp when metadata was extracted")


class ResourceBase(BaseModel):
    """Base schema with common resource fields."""
    
    model_config = ConfigDict(from_attributes=True)
    
    title: str = Field(..., min_length=1, max_length=200, description="Resource title")
    url: HttpUrl = Field(..., description="Resource URL")
    description: Optional[str] = Field(None, max_length=1000, description="Resource description")
    category: Optional[str] = Field(None, max_length=50, description="Resource category")
    tags: Optional[list[str]] = Field(default_factory=list, description="List of tags for organization")
    link_metadata: Optional[Dict[str, Any]] = Field(None, description="Link preview metadata")


class ResourceCreate(ResourceBase):
    """Schema for creating a new resource."""
    pass


class ResourceUpdate(BaseModel):
    """Schema for updating an existing resource."""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Display title for the resource")
    url: Optional[HttpUrl] = Field(None, description="The actual URL/link")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description of the resource")
    category: Optional[str] = Field(None, max_length=100, description="Optional category for organization")
    tags: Optional[list[str]] = Field(None, description="List of tags for organization")


class Resource(ResourceBase):
    """Complete resource schema with all fields including ID and timestamps."""
    
    id: int = Field(..., description="Unique resource identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    @property
    def preview_metadata(self) -> Optional[LinkPreviewMetadata]:
        """Get parsed link preview metadata."""
        if self.link_metadata:
            try:
                return LinkPreviewMetadata(**self.link_metadata)
            except Exception:
                return None
        return None


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