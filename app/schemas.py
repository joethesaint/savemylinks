"""
Pydantic schemas for SaveMyLinks application.

This module defines the data validation schemas for request bodies and response models.
Following the architecture rule: Use Pydantic schemas for all data validation,
never use ORM models directly in endpoints.
"""

import re
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, HttpUrl, Field, ConfigDict, field_validator

TAG_MAX_LENGTH = 30
TAGS_MAX = 10


def normalize_tags(tags: Optional[list[str]]) -> Optional[list[str]]:
    """Tags as people type them -> one form: no leading #, no quotes or commas, lowercase,
    spaces as -, no empties, no repeats (first wins). The native app does exactly the same."""
    if tags is None:
        return None
    out: list[str] = []
    for raw in tags:
        t = raw.strip().lstrip("#").strip().replace('"', "").replace(",", "")
        t = re.sub(r"\s+", "-", t.lower())
        if not t:
            continue
        if len(t) > TAG_MAX_LENGTH:
            raise ValueError(f"Each tag should have at most {TAG_MAX_LENGTH} characters")
        if t not in out:
            out.append(t)
    return out


class ResourceBase(BaseModel):
    """Base schema with common resource fields."""
    title: str = Field(..., min_length=1, max_length=200, description="Display title for the resource")
    url: HttpUrl = Field(..., description="The actual URL/link")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description of the resource")
    category: Optional[str] = Field(None, max_length=100, description="Optional category for organization")
    tags: Optional[list[str]] = Field(None, max_length=TAGS_MAX, description="Tags: several per link, normalized")

    _tags = field_validator("tags")(classmethod(lambda cls, v: normalize_tags(v)))


class ResourceCreate(ResourceBase):
    """Schema for creating a new resource."""
    pass


class ResourceUpdate(BaseModel):
    """Schema for updating an existing resource."""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Display title for the resource")
    url: Optional[HttpUrl] = Field(None, description="The actual URL/link")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description of the resource")
    category: Optional[str] = Field(None, max_length=100, description="Optional category for organization")
    tags: Optional[list[str]] = Field(None, max_length=TAGS_MAX, description="Replaces the tags; [] or null clears them")

    _tags = field_validator("tags")(classmethod(lambda cls, v: normalize_tags(v)))


class Resource(ResourceBase):
    """Schema for resource responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Unique identifier for the resource")
    created_at: datetime = Field(..., description="Timestamp when resource was created")
    updated_at: datetime = Field(..., description="Timestamp when resource was last updated")
    link_metadata: Optional[Dict[str, Any]] = Field(None, description="Link preview: title, description, image, site_name. Filled in shortly after saving.")
    tags: list[str] = Field(default_factory=list, description="Tags, normalized; [] when none")

    @field_validator("tags", mode="before")
    @classmethod
    def _no_tags_is_empty(cls, v):
        return v or []


class Facet(BaseModel):
    name: str
    count: int


class Facets(BaseModel):
    """What the sidebar lists: every category and tag with how many links have it."""
    total: int
    categories: list[Facet]
    tags: list[Facet]


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