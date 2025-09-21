"""
SQLAlchemy models for SaveMyLinks application.

This module defines the database models using SQLAlchemy 2.0 declarative style
with Mapped and mapped_column for type safety.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Text, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Resource(Base):
    """
    Resource model representing a saved link/resource.
    
    Attributes:
        id: Primary key identifier
        title: Display title for the resource
        url: The actual URL/link
        description: Optional description of the resource
        category: Optional category for organization
        tags: List of tags for organization and filtering
        link_metadata: JSON field storing link preview metadata (title, description, image, etc.)
        created_at: Timestamp when resource was created
        updated_at: Timestamp when resource was last updated
    """
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        default=list,
        comment="List of tags for organization and filtering"
    )
    link_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, 
        nullable=True,
        comment="Stores link preview metadata: title, description, image, site_name, etc."
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<Resource(id={self.id}, title='{self.title}', url='{self.url}')>"