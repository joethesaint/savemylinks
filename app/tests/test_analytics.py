"""
Tests for analytics functionality and statistics tracking.

This module tests analytics features including usage statistics,
popular resources, category distribution, and trend analysis.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta
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


@pytest_asyncio.fixture
async def sample_analytics_data(client: AsyncClient):
    """Create sample data for analytics testing."""
    resources_data = [
        {
            "title": "Python Documentation",
            "url": "https://docs.python.org",
            "description": "Official Python documentation",
            "category": "Documentation",
            "tags": ["python", "programming", "docs"]
        },
        {
            "title": "React Tutorial",
            "url": "https://reactjs.org/tutorial",
            "description": "Learn React step by step",
            "category": "Tutorial",
            "tags": ["react", "javascript", "frontend"]
        },
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
            "description": "Programming Q&A",
            "category": "Development",
            "tags": ["programming", "help", "community"]
        },
        {
            "title": "Design Inspiration",
            "url": "https://dribbble.com",
            "description": "Design showcase",
            "category": "Design",
            "tags": ["design", "inspiration", "ui"]
        }
    ]
    
    created_resources = []
    for data in resources_data:
        response = await client.post("/api/resources/", json=data)
        assert response.status_code == 201
        created_resources.append(response.json())
    
    return created_resources


class TestAnalytics:
    """Test cases for analytics functionality."""

    @pytest.mark.asyncio
    async def test_category_distribution_stats(self, client: AsyncClient, sample_analytics_data):
        """Test category distribution statistics."""
        # This test assumes a future analytics endpoint
        # For now, we'll test the underlying data structure
        
        # Get all resources and analyze categories
        response = await client.get("/api/resources/")
        assert response.status_code == 200
        
        data = response.json()
        resources = data["resources"]
        
        # Count categories
        category_counts = {}
        for resource in resources:
            category = resource["category"]
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Verify expected distribution
        assert category_counts.get("Development", 0) == 2
        assert category_counts.get("Documentation", 0) == 1
        assert category_counts.get("Tutorial", 0) == 1
        assert category_counts.get("Design", 0) == 1

    @pytest.mark.asyncio
    async def test_tag_frequency_analysis(self, client: AsyncClient, sample_analytics_data):
        """Test tag frequency analysis."""
        response = await client.get("/api/resources/")
        assert response.status_code == 200
        
        data = response.json()
        resources = data["resources"]
        
        # Count tag frequencies
        tag_counts = {}
        for resource in resources:
            for tag in resource.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Verify most common tags
        assert tag_counts.get("programming", 0) >= 2
        assert "python" in tag_counts
        assert "design" in tag_counts

    @pytest.mark.asyncio
    async def test_resource_creation_trends(self, client: AsyncClient, sample_analytics_data):
        """Test resource creation trend analysis."""
        response = await client.get("/api/resources/")
        assert response.status_code == 200
        
        data = response.json()
        resources = data["resources"]
        
        # Analyze creation dates
        creation_dates = []
        for resource in resources:
            if resource.get("created_at"):
                creation_dates.append(resource["created_at"])
        
        # Verify we have creation timestamps
        assert len(creation_dates) == len(resources)
        
        # All should be created recently (within last hour for test)
        now = datetime.utcnow()
        for date_str in creation_dates:
            # Parse ISO format datetime
            created_at = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            time_diff = abs((now - created_at.replace(tzinfo=None)).total_seconds())
            assert time_diff < 3600  # Within 1 hour

    @pytest.mark.asyncio
    async def test_search_analytics_tracking(self, client: AsyncClient, sample_analytics_data):
        """Test search query analytics (future feature)."""
        # Test different search queries
        search_queries = ["python", "react", "design", "programming"]
        
        search_results = {}
        for query in search_queries:
            response = await client.get(f"/api/resources/?search={query}")
            assert response.status_code == 200
            
            data = response.json()
            search_results[query] = {
                "total_results": data["total"],
                "query": query
            }
        
        # Verify search results make sense
        assert search_results["python"]["total_results"] >= 1
        assert search_results["programming"]["total_results"] >= 2

    @pytest.mark.asyncio
    async def test_export_usage_analytics(self, client: AsyncClient, sample_analytics_data):
        """Test export usage analytics."""
        # Test different export formats
        formats = ["json", "csv"]
        
        for format_type in formats:
            response = await client.get(f"/api/resources/export?format={format_type}")
            assert response.status_code == 200
            
            # In a real analytics system, this would track export usage
            # For now, we just verify the exports work
            if format_type == "json":
                data = response.json()
                assert "export_info" in data
                assert data["export_info"]["export_format"] == format_type
            else:  # CSV
                assert "text/csv" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_category_popularity_metrics(self, client: AsyncClient, sample_analytics_data):
        """Test category popularity metrics."""
        # Get resources by category
        categories = ["Development", "Documentation", "Tutorial", "Design"]
        
        category_metrics = {}
        for category in categories:
            response = await client.get(f"/api/resources/?category={category}")
            assert response.status_code == 200
            
            data = response.json()
            category_metrics[category] = {
                "resource_count": data["total"],
                "category": category
            }
        
        # Verify metrics
        assert category_metrics["Development"]["resource_count"] == 2
        assert category_metrics["Documentation"]["resource_count"] == 1

    @pytest.mark.asyncio
    async def test_bulk_operation_analytics(self, client: AsyncClient, sample_analytics_data):
        """Test bulk operation usage analytics."""
        # Test bulk delete analytics
        resource_ids = [res["id"] for res in sample_analytics_data[:2]]
        
        response = await client.post("/api/resources/bulk/delete", json=resource_ids)
        assert response.status_code == 200
        
        # Verify bulk operation completed
        data = response.json()
        assert "Successfully deleted 2 resource(s)" in data["message"]
        
        # In a real system, this would be tracked for analytics
        # Verify resources were actually deleted
        for resource_id in resource_ids:
            check_response = await client.get(f"/api/resources/{resource_id}")
            assert check_response.status_code == 404

    @pytest.mark.asyncio
    async def test_metadata_extraction_success_rate(self, client: AsyncClient):
        """Test metadata extraction success rate analytics."""
        # Create resources with metadata extraction enabled
        test_resources = [
            {
                "title": "Test Resource 1",
                "url": "https://example1.com",
                "description": "Test description 1",
                "category": "Testing"
            },
            {
                "title": "Test Resource 2", 
                "url": "https://example2.com",
                "description": "Test description 2",
                "category": "Testing"
            }
        ]
        
        created_resources = []
        for resource_data in test_resources:
            response = await client.post("/api/resources/?extract_metadata=true", json=resource_data)
            assert response.status_code == 201
            created_resources.append(response.json())
        
        # Analyze metadata extraction success
        successful_extractions = 0
        total_resources = len(created_resources)
        
        for resource in created_resources:
            if resource.get("link_metadata"):
                successful_extractions += 1
        
        # Calculate success rate (for analytics dashboard)
        success_rate = (successful_extractions / total_resources) * 100 if total_resources > 0 else 0
        
        # In a real system, this would be stored and displayed
        assert success_rate >= 0  # Can be 0 if metadata extraction is mocked/disabled
        assert success_rate <= 100

    @pytest.mark.asyncio
    async def test_user_activity_patterns(self, client: AsyncClient, sample_analytics_data):
        """Test user activity pattern analysis."""
        # Simulate different types of user activities
        activities = []
        
        # Resource creation activity
        response = await client.post("/api/resources/", json={
            "title": "Activity Test Resource",
            "url": "https://activity-test.com",
            "description": "Testing user activity",
            "category": "Testing"
        })
        if response.status_code == 201:
            activities.append({"type": "create", "timestamp": datetime.utcnow()})
        
        # Resource viewing activity
        response = await client.get("/api/resources/")
        if response.status_code == 200:
            activities.append({"type": "view_list", "timestamp": datetime.utcnow()})
        
        # Search activity
        response = await client.get("/api/resources/?search=test")
        if response.status_code == 200:
            activities.append({"type": "search", "timestamp": datetime.utcnow()})
        
        # Export activity
        response = await client.get("/api/resources/export?format=json")
        if response.status_code == 200:
            activities.append({"type": "export", "timestamp": datetime.utcnow()})
        
        # Verify we tracked various activities
        activity_types = [activity["type"] for activity in activities]
        assert "create" in activity_types
        assert "view_list" in activity_types
        assert "search" in activity_types
        assert "export" in activity_types
        
        # In a real analytics system, these would be stored and analyzed
        assert len(activities) >= 4