"""
Tests for bulk operations functionality.

This module tests the bulk operations features including
bulk delete, export, and import functionality.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import json

from app.main import app
from app.database import Base, get_db
from app.models import Resource


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def async_session():
    """Create an async database session for testing."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
    
    await engine.dispose()


@pytest_asyncio.fixture
async def client(async_session: AsyncSession):
    """Create an async HTTP client for testing."""
    async def override_get_db():
        yield async_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://test"
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_resources(client: AsyncClient):
    """Create sample resources for testing."""
    resources = []
    sample_data = [
        {
            "title": "GitHub",
            "url": "https://github.com",
            "description": "Code hosting platform",
            "category": "Development",
            "tags": ["git", "code", "collaboration"]
        },
        {
            "title": "Stack Overflow",
            "url": "https://stackoverflow.com",
            "description": "Programming Q&A site",
            "category": "Development",
            "tags": ["programming", "help", "community"]
        },
        {
            "title": "MDN Web Docs",
            "url": "https://developer.mozilla.org",
            "description": "Web development documentation",
            "category": "Documentation",
            "tags": ["web", "docs", "reference"]
        }
    ]
    
    for data in sample_data:
        response = await client.post("/api/resources/", json=data)
        assert response.status_code == 201
        resources.append(response.json())
    
    return resources


class TestBulkOperations:
    """Test cases for bulk operations."""

    @pytest.mark.asyncio
    async def test_bulk_delete_success(self, client: AsyncClient, sample_resources):
        """Test successful bulk deletion."""
        resource_ids = [r["id"] for r in sample_resources[:2]]  # Delete first 2
        
        response = await client.post("/api/resources/bulk/delete", json=resource_ids)
        
        assert response.status_code == 200
        data = response.json()
        assert "Successfully deleted 2 resource(s)" in data["message"]
        
        # Verify deletion
        for resource_id in resource_ids:
            response = await client.get(f"/api/resources/{resource_id}")
            assert response.status_code == 404
        
        # Verify remaining resource still exists
        remaining_id = sample_resources[2]["id"]
        response = await client.get(f"/api/resources/{remaining_id}")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_bulk_delete_partial_success(self, client: AsyncClient, sample_resources):
        """Test bulk deletion with some non-existent IDs."""
        existing_id = sample_resources[0]["id"]
        non_existent_ids = [999, 1000]
        all_ids = [existing_id] + non_existent_ids
        
        response = await client.post("/api/resources/bulk/delete", json=all_ids)
        
        assert response.status_code == 200
        data = response.json()
        assert "Successfully deleted 1 resource(s)" in data["message"]
        assert "Resources not found: [999, 1000]" in data["message"]

    @pytest.mark.asyncio
    async def test_export_json_comprehensive(self, client: AsyncClient, sample_resources):
        """Test comprehensive JSON export functionality."""
        response = await client.get("/api/resources/export?format=json")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify export structure
        assert "export_info" in data
        assert "resources" in data
        
        export_info = data["export_info"]
        assert export_info["total_resources"] == 3
        assert export_info["export_format"] == "json"
        assert export_info["category_filter"] is None
        assert export_info["search_filter"] is None
        
        # Verify resource data
        resources = data["resources"]
        assert len(resources) == 3
        
        for resource in resources:
            assert "id" in resource
            assert "title" in resource
            assert "url" in resource
            assert "description" in resource
            assert "category" in resource
            assert "tags" in resource
            assert "created_at" in resource
            assert "updated_at" in resource

    @pytest.mark.asyncio
    async def test_export_csv_format(self, client: AsyncClient, sample_resources):
        """Test CSV export format."""
        response = await client.get("/api/resources/export?format=csv")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "csv_data" in data
        csv_content = data["csv_data"]
        
        # Verify CSV structure
        lines = csv_content.strip().split('\n')
        assert len(lines) >= 4  # Header + 3 resources
        
        # Verify header
        header = lines[0]
        expected_columns = ["ID", "Title", "URL", "Description", "Category", "Tags", "Created At", "Updated At"]
        for column in expected_columns:
            assert column in header
        
        # Verify data rows contain expected content
        for i, resource in enumerate(sample_resources):
            row = lines[i + 1]  # Skip header
            assert resource["title"] in row
            assert resource["url"] in row
            assert resource["category"] in row

    @pytest.mark.asyncio
    async def test_export_with_category_filter(self, client: AsyncClient, sample_resources):
        """Test export with category filtering."""
        response = await client.get("/api/resources/export?format=json&category=Development")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["export_info"]["category_filter"] == "Development"
        
        # Should only include Development category resources
        resources = data["resources"]
        development_resources = [r for r in resources if r["category"] == "Development"]
        assert len(development_resources) == 2  # GitHub and Stack Overflow

    @pytest.mark.asyncio
    async def test_export_with_search_filter(self, client: AsyncClient, sample_resources):
        """Test export with search filtering."""
        response = await client.get("/api/resources/export?format=json&search=documentation")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["export_info"]["search_filter"] == "documentation"
        
        # Should include resources matching search term
        resources = data["resources"]
        assert len(resources) >= 1
        
        # Verify search results contain the search term
        found_match = False
        for resource in resources:
            if "documentation" in resource["description"].lower() or "documentation" in resource["title"].lower():
                found_match = True
                break
        assert found_match

    @pytest.mark.asyncio
    async def test_export_unsupported_format(self, client: AsyncClient):
        """Test export with unsupported format."""
        response = await client.get("/api/resources/export?format=xml")
        
        assert response.status_code == 400
        error_data = response.json()
        assert "Invalid format" in error_data["detail"]
        assert "json, csv" in error_data["detail"]

    @pytest.mark.asyncio
    async def test_bulk_delete_validation_errors(self, client: AsyncClient):
        """Test bulk delete validation scenarios."""
        # Test empty list
        response = await client.post("/api/resources/bulk/delete", json=[])
        assert response.status_code == 400
        assert "No resource IDs provided" in response.json()["detail"]
        
        # Test invalid JSON
        response = await client.post("/api/resources/bulk/delete", json="invalid")
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_export_headers(self, client: AsyncClient, sample_resources):
        """Test export response headers."""
        # Test JSON export headers
        response = await client.get("/api/resources/export?format=json")
        assert response.status_code == 200
        assert "attachment; filename=savemylinks_export.json" in response.headers.get("content-disposition", "")
        
        # Test CSV export headers
        response = await client.get("/api/resources/export?format=csv")
        assert response.status_code == 200
        assert "attachment; filename=savemylinks_export.csv" in response.headers.get("content-disposition", "")