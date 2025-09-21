"""
Test-specific background tasks for the SaveMyLinks application.

This module provides background task functionality optimized for testing,
using the faster test_metadata_extractor instance.
"""

import asyncio
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.crud import resource_crud
from app.services.metadata_extractor import test_metadata_extractor

logger = logging.getLogger(__name__)


async def extract_metadata_background_test(resource_id: int) -> None:
    """
    Background task to extract metadata for a resource (test version).
    
    This task runs asynchronously after resource creation to avoid
    blocking the API response while metadata is being fetched.
    Uses the faster test_metadata_extractor for improved test performance.
    
    Args:
        resource_id: ID of the resource to extract metadata for
    """
    try:
        # Get a new database session for the background task
        async with AsyncSessionLocal() as db:
            # Fetch the resource
            resource = await resource_crud.get_by_id(db, resource_id=resource_id)
            if not resource:
                logger.warning(f"Resource {resource_id} not found for metadata extraction")
                return
            
            # Skip if metadata already exists
            if resource.link_metadata:
                logger.info(f"Metadata already exists for resource {resource_id}")
                return
            
            # Extract metadata using test extractor
            logger.info(f"Starting background metadata extraction for resource {resource_id}")
            metadata = await test_metadata_extractor.extract_metadata(resource.url)
            
            # Update the resource with metadata
            resource.link_metadata = metadata
            
            # Commit the changes
            await db.commit()
            
            logger.info(f"Background metadata extraction completed for resource {resource_id}")
            
    except Exception as e:
        logger.error(f"Background metadata extraction failed for resource {resource_id}: {str(e)}")
        # Don't re-raise to avoid breaking the background task