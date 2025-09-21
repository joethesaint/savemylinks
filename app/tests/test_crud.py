"""
Tests for CRUD operations.

This module tests the ResourceCRUD class functionality including
create, read, update, delete operations and metadata handling.
"""

import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import ResourceCRUD
from app.schemas import ResourceCreate, ResourceUpdate
from app.models import Resource


class TestResourceCRUDDelete:
    """Test delete operations in ResourceCRUD."""
    
    @pytest.fixture
    def resource_crud(self):
        """Create ResourceCRUD instance."""
        return ResourceCRUD(Resource)
    
    @pytest.mark.asyncio
    async def test_delete_success(self, resource_crud, async_session: AsyncSession):
        """Test successful resource deletion."""
        # Create a resource first
        resource_data = ResourceCreate(
            title="Test Resource",
            url="https://example.com",
            category="Testing"
        )
        
        created_resource = await resource_crud.create(
            async_session, obj_in=resource_data, extract_metadata=False
        )
        
        # Delete the resource
        result = await resource_crud.delete(async_session, id=created_resource.id)
        
        assert result is True
        
        # Verify resource is deleted
        deleted_resource = await resource_crud.get_by_id(async_session, id=created_resource.id)
        assert deleted_resource is None
    
    @pytest.mark.asyncio
    async def test_delete_not_found(self, resource_crud, async_session: AsyncSession):
        """Test deleting non-existent resource."""
        result = await resource_crud.delete(async_session, id=99999)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_rollback_on_error(self, resource_crud, async_session: AsyncSession):
        """Test rollback when delete operation fails."""
        # Create a resource first
        resource_data = ResourceCreate(
            title="Test Resource",
            url="https://example.com",
            category="Testing"
        )
        
        created_resource = await resource_crud.create(
            async_session, obj_in=resource_data, extract_metadata=False
        )
        
        # Mock session.delete to raise an exception
        with patch.object(async_session, 'delete', side_effect=Exception("Database error")):
            with patch.object(async_session, 'rollback', new_callable=AsyncMock) as mock_rollback:
                with pytest.raises(Exception, match="Database error"):
                    await resource_crud.delete(async_session, id=created_resource.id)
                
                # Verify rollback was called
                mock_rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_multiple_resources(self, resource_crud, async_session: AsyncSession):
        """Test deleting multiple resources."""
        # Create multiple resources
        resources = []
        for i in range(3):
            resource_data = ResourceCreate(
                title=f"Test Resource {i}",
                url=f"https://example{i}.com",
                category="Testing"
            )
            resource = await resource_crud.create(
                async_session, obj_in=resource_data, extract_metadata=False
            )
            resources.append(resource)
        
        # Delete each resource
        for resource in resources:
            result = await resource_crud.delete(async_session, id=resource.id)
            assert result is True
        
        # Verify all resources are deleted
        for resource in resources:
            deleted_resource = await resource_crud.get_by_id(async_session, id=resource.id)
            assert deleted_resource is None
    
    @pytest.mark.asyncio
    async def test_delete_with_zero_id(self, resource_crud, async_session: AsyncSession):
        """Test deleting resource with ID 0."""
        result = await resource_crud.delete(async_session, id=0)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_with_negative_id(self, resource_crud, async_session: AsyncSession):
        """Test deleting resource with negative ID."""
        result = await resource_crud.delete(async_session, id=-1)
        assert result is False


class TestResourceCRUDOperations:
    """Test additional CRUD operations."""
    
    @pytest.fixture
    def resource_crud(self):
        """Create ResourceCRUD instance."""
        return ResourceCRUD(Resource)
    
    @pytest.mark.asyncio
    async def test_create_with_metadata_extraction(self, resource_crud, async_session: AsyncSession):
        """Test creating resource with metadata extraction."""
        # Mock metadata extraction
        with patch('app.crud.metadata_extractor.extract_metadata') as mock_extract:
            mock_extract.return_value = {
                'title': 'Extracted Title',
                'description': 'Extracted Description',
                'status': 'success'
            }
            
            resource_data = ResourceCreate(
                title="Test Resource",
                url="https://example.com",
                category="Testing"
            )
            
            created_resource = await resource_crud.create(
                async_session, obj_in=resource_data, extract_metadata=True
            )
            
            assert created_resource.title == "Test Resource"
            assert str(created_resource.url) == "https://example.com/"  # URL normalization adds trailing slash
            assert created_resource.link_metadata is not None
            assert created_resource.link_metadata['title'] == 'Extracted Title'
            assert created_resource.link_metadata['description'] == 'Extracted Description'
            
            # Verify metadata extraction was called
            mock_extract.assert_called_once_with("https://example.com/")
    
    @pytest.mark.asyncio
    async def test_update_with_metadata_refresh(self, resource_crud, async_session: AsyncSession):
        """Test updating resource with metadata refresh."""
        # Create a resource first
        resource_data = ResourceCreate(
            title="Test Resource",
            url="https://example.com",
            category="Testing"
        )

        created_resource = await resource_crud.create(
            async_session, obj_in=resource_data, extract_metadata=False
        )

        # Mock metadata extraction for update
        with patch('app.crud.metadata_extractor.extract_metadata') as mock_extract:
            mock_extract.return_value = {
                'title': 'Updated Title',
                'description': 'Updated Description'
            }

            update_data = ResourceUpdate(url="https://updated-example.com")

            updated_resource = await resource_crud.update(
                async_session,
                db_obj=created_resource,
                obj_in=update_data,
                refresh_metadata=True
            )

            # URL normalization adds trailing slash
            assert str(updated_resource.url) == "https://updated-example.com/"
            assert updated_resource.link_metadata is not None
            assert updated_resource.link_metadata['title'] == 'Updated Title'
            assert updated_resource.link_metadata['description'] == 'Updated Description'
            
            # Verify metadata extraction was called with normalized URL
            mock_extract.assert_called_once_with("https://updated-example.com/")
    
    @pytest.mark.asyncio
    async def test_refresh_metadata(self, resource_crud, async_session: AsyncSession):
        """Test refreshing metadata for existing resource."""
        # Create a resource first
        resource_data = ResourceCreate(
            title="Test Resource",
            url="https://example.com",
            category="Testing"
        )

        created_resource = await resource_crud.create(
            async_session, obj_in=resource_data, extract_metadata=False
        )

        # Mock metadata extraction
        with patch('app.crud.metadata_extractor.extract_metadata') as mock_extract:
            mock_extract.return_value = {
                'title': 'Refreshed Title',
                'description': 'Refreshed Description',
                'status': 'success'
            }

            refreshed_resource = await resource_crud.refresh_metadata(
                async_session, db_obj=created_resource
            )

            assert refreshed_resource.link_metadata is not None
            assert refreshed_resource.link_metadata['title'] == 'Refreshed Title'
            assert refreshed_resource.link_metadata['description'] == 'Refreshed Description'
            assert refreshed_resource.link_metadata['status'] == 'success'
            
            # Verify metadata extraction was called
            mock_extract.assert_called_once_with(str(created_resource.url))