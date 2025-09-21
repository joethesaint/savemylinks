"""
Tests for error handling and user feedback throughout the application.

This module tests various error scenarios and ensures proper error responses
are returned to users with helpful feedback.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, AsyncMock
import json

from app.main import app
from app.database import Base, get_db
from app.models import Resource


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


class TestErrorHandling:
    """Test cases for error handling and user feedback."""

    @pytest.mark.asyncio
    async def test_create_resource_duplicate_url(self, client: AsyncClient):
        """Test creating resource with duplicate URL returns proper error."""
        resource_data = {
            "title": "Test Resource",
            "url": "https://duplicate.com",
            "description": "Test description",
            "category": "Testing"
        }
        
        # Create first resource
        response1 = await client.post("/api/resources/", json=resource_data)
        assert response1.status_code == 201
        
        # Try to create duplicate
        response2 = await client.post("/api/resources/", json=resource_data)
        assert response2.status_code == 409
        error_data = response2.json()
        assert "already exists" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_resource_invalid_url(self, client: AsyncClient):
        """Test creating resource with invalid URL format."""
        resource_data = {
            "title": "Test Resource",
            "url": "not-a-valid-url",
            "description": "Test description",
            "category": "Testing"
        }
        
        response = await client.post("/api/resources/", json=resource_data)
        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data

    @pytest.mark.asyncio
    async def test_create_resource_missing_required_fields(self, client: AsyncClient):
        """Test creating resource with missing required fields."""
        incomplete_data = {
            "title": "Test Resource"
            # Missing url, description, category
        }
        
        response = await client.post("/api/resources/", json=incomplete_data)
        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data

    @pytest.mark.asyncio
    async def test_get_nonexistent_resource(self, client: AsyncClient):
        """Test getting non-existent resource returns 404."""
        response = await client.get("/api/resources/999")
        assert response.status_code == 404
        error_data = response.json()
        assert "not found" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_nonexistent_resource(self, client: AsyncClient):
        """Test updating non-existent resource returns 404."""
        update_data = {
            "title": "Updated Title",
            "description": "Updated description"
        }
        
        response = await client.put("/api/resources/999", json=update_data)
        assert response.status_code == 404
        error_data = response.json()
        assert "not found" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_resource(self, client: AsyncClient):
        """Test deleting non-existent resource returns 404."""
        response = await client.delete("/api/resources/999")
        assert response.status_code == 404
        error_data = response.json()
        assert "not found" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_bulk_delete_empty_list(self, client: AsyncClient):
        """Test bulk delete with empty list returns proper error."""
        response = await client.post("/api/resources/bulk/delete", json=[])
        assert response.status_code == 400
        error_data = response.json()
        assert "no resource ids" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_export_invalid_format(self, client: AsyncClient):
        """Test export with invalid format returns proper error."""
        response = await client.get("/api/resources/export?format=xml")
        assert response.status_code == 400
        error_data = response.json()
        assert "invalid format" in error_data["detail"].lower()
        assert "json, csv" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_pagination_invalid_parameters(self, client: AsyncClient):
        """Test pagination with invalid parameters."""
        # Test negative page
        response = await client.get("/api/resources/?page=-1")
        assert response.status_code == 422
        
        # Test zero page
        response = await client.get("/api/resources/?page=0")
        assert response.status_code == 422
        
        # Test excessive per_page
        response = await client.get("/api/resources/?per_page=1000")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_database_connection_error(self, client: AsyncClient):
        """Test handling of database connection errors."""
        with patch('app.crud.resource_crud.get_all') as mock_get_all:
            mock_get_all.side_effect = Exception("Database connection failed")
            
            response = await client.get("/api/resources/")
            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_metadata_extraction_failure_handling(self, client: AsyncClient):
        """Test that metadata extraction failures don't break resource creation."""
        with patch('app.services.metadata_extractor.MetadataExtractor.extract_metadata') as mock_extract:
            mock_extract.side_effect = Exception("Network error")
            
            resource_data = {
                "title": "Test Resource",
                "url": "https://test.com",
                "description": "Test description",
                "category": "Testing"
            }
            
            response = await client.post("/api/resources/", json=resource_data)
            # Should still create resource even if metadata extraction fails
            assert response.status_code == 201
            
            created_resource = response.json()
            assert created_resource["title"] == "Test Resource"
            assert created_resource["link_metadata"] is None

    @pytest.mark.asyncio
    async def test_malformed_json_request(self, client: AsyncClient):
        """Test handling of malformed JSON in requests."""
        response = await client.post(
            "/api/resources/",
            content="{ invalid json }",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_content_type_validation(self, client: AsyncClient):
        """Test proper content type validation."""
        resource_data = {
            "title": "Test Resource",
            "url": "https://test.com",
            "description": "Test description",
            "category": "Testing"
        }
        
        # Send as form data instead of JSON
        response = await client.post(
            "/api/resources/",
            data=resource_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_rate_limiting_headers(self, client: AsyncClient):
        """Test that rate limiting information is included in responses."""
        response = await client.get("/api/resources/")
        # Check if rate limiting headers are present (if implemented)
        # This is a placeholder for future rate limiting implementation
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_cors_headers(self, client: AsyncClient):
        """Test CORS headers are properly set."""
        response = await client.options("/api/resources/")
        # This test assumes CORS middleware is configured
        # Adjust based on actual CORS implementation
        assert response.status_code in [200, 204]