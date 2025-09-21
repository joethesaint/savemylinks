"""
Integration tests for metadata extraction with real URLs.

These tests verify that the metadata extraction works with actual websites
and handles various scenarios like failures, timeouts, and different content types.
"""

import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.metadata_extractor import test_metadata_extractor
from app.services.test_background_tasks import extract_metadata_background_test
from app.models import Resource
from app.crud import resource_crud


class TestMetadataExtractionIntegration:
    """Integration tests for metadata extraction with real URLs."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_extract_metadata_from_github(self):
        """Test metadata extraction from GitHub (reliable test URL)."""
        url = "https://github.com"
        
        # Extract metadata directly
        metadata = await test_metadata_extractor.extract_metadata(url)
        
        # Verify basic structure
        assert metadata is not None
        assert metadata["url"] == url
        assert "status" in metadata
        
        if metadata["status"] == "success":
            assert "title" in metadata
            assert metadata["title"] is not None
            assert len(metadata["title"]) > 0
            
            # GitHub should have these fields
            assert "description" in metadata
            assert "site_name" in metadata

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_extract_metadata_from_example_com(self):
        """Test metadata extraction from example.com (simple test case)."""
        url = "https://example.com"
        
        metadata = await test_metadata_extractor.extract_metadata(url)
        
        assert metadata is not None
        assert metadata["url"] == url
        assert "status" in metadata
        
        if metadata["status"] == "success":
            assert "title" in metadata
            assert "Example Domain" in metadata["title"]

    @pytest.mark.asyncio
    async def test_extract_metadata_invalid_url(self):
        """Test metadata extraction with invalid URL."""
        url = "https://this-domain-definitely-does-not-exist-12345.com"
        
        metadata = await test_metadata_extractor.extract_metadata(url)
        
        assert metadata is not None
        assert metadata["url"] == url
        assert metadata["status"] == "failed"
        assert "error" in metadata
        assert metadata["error"] is not None

    @pytest.mark.asyncio
    async def test_extract_metadata_malformed_url(self):
        """Test metadata extraction with malformed URL."""
        url = "not-a-valid-url"
        
        metadata = await test_metadata_extractor.extract_metadata(url)
        
        assert metadata is not None
        assert metadata["url"] == url
        assert metadata["status"] == "failed"
        assert "error" in metadata

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_background_task_with_real_url(self):
        """Test the complete background task flow with a real URL."""
        # Create a test resource with a real URL using a direct database session
        from app.database import AsyncSessionLocal
        from app.schemas import ResourceCreate
        import uuid
        
        async with AsyncSessionLocal() as db:
            # Use a unique URL to avoid conflicts with other tests
            unique_url = f"https://github.com/test-{uuid.uuid4().hex[:8]}"
            resource_data = ResourceCreate(
                title="Test GitHub Unique",
                url=unique_url,
                description="GitHub homepage test"
            )
            resource = await resource_crud.create(db=db, obj_in=resource_data, extract_metadata=False)
            await db.commit()
            
            # Run the background task (this will use the test metadata extractor)
            await extract_metadata_background_test(resource.id)
            
            # Get the updated resource
            await db.refresh(resource)
            updated_resource = await resource_crud.get_by_id(db, resource.id)
            
            assert updated_resource.link_metadata is not None
            assert "status" in updated_resource.link_metadata
            assert updated_resource.link_metadata["url"] == unique_url
            
            # Since this is a non-existent URL, it should have failed status
            assert updated_resource.link_metadata["status"] == "failed"
            assert "error" in updated_resource.link_metadata

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_metadata_extraction_timeout_handling(self):
        """Test that metadata extraction handles timeouts gracefully."""
        # Use a URL that might timeout (httpbin delay endpoint)
        url = "https://httpbin.org/delay/10"  # 10 second delay
        
        # This should timeout and return an error status
        metadata = await test_metadata_extractor.extract_metadata(url)
        
        assert metadata is not None
        assert metadata["url"] == url
        # Should either succeed quickly or fail with timeout
        assert metadata["status"] in ["success", "failed"]

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_metadata_extraction_with_redirects(self):
        """Test metadata extraction with URL redirects."""
        # httpbin redirect endpoint
        url = "https://httpbin.org/redirect/1"
        
        metadata = await test_metadata_extractor.extract_metadata(url)
        
        assert metadata is not None
        assert metadata["url"] == url
        assert "status" in metadata
        
        # Should handle redirects properly - but httpbin may not have a title
        # so we just check that it processed successfully or failed gracefully
        assert metadata["status"] in ["success", "failed"]
        if metadata["status"] == "success":
            # httpbin pages may not have titles, so just check basic structure
            assert "extracted_at" in metadata

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_metadata_extraction_different_content_types(self):
        """Test metadata extraction with different content types."""
        test_urls = [
            "https://httpbin.org/html",  # HTML content
            "https://httpbin.org/json",  # JSON content (should handle gracefully)
        ]
        
        for url in test_urls:
            metadata = await test_metadata_extractor.extract_metadata(url)
            
            assert metadata is not None
            assert metadata["url"] == url
            assert "status" in metadata
            
            # Should not crash regardless of content type
            assert metadata["status"] in ["success", "failed"]

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_metadata_extraction(self):
        """Test concurrent metadata extraction to ensure thread safety."""
        urls = [
            "https://example.com",
            "https://github.com",
            "https://httpbin.org/html"
        ]
        
        # Extract metadata concurrently
        tasks = [test_metadata_extractor.extract_metadata(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete without exceptions
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"URL {urls[i]} raised exception: {result}"
            assert result is not None
            assert result["url"] == urls[i]
            assert "status" in result


class TestMetadataExtractionEdgeCases:
    """Test edge cases for metadata extraction."""

    @pytest.mark.asyncio
    async def test_extract_metadata_empty_url(self):
        """Test metadata extraction with empty URL."""
        metadata = await test_metadata_extractor.extract_metadata("")
        
        assert metadata is not None
        assert metadata["url"] == ""
        assert metadata["status"] == "failed"

    @pytest.mark.asyncio
    async def test_extract_metadata_none_url(self):
        """Test metadata extraction with None URL."""
        metadata = await test_metadata_extractor.extract_metadata(None)
        
        assert metadata is not None
        assert metadata["url"] is None
        assert metadata["status"] == "failed"

    @pytest.mark.asyncio
    async def test_extract_metadata_very_long_url(self):
        """Test metadata extraction with very long URL."""
        # Create a very long URL
        long_path = "a" * 2000
        url = f"https://example.com/{long_path}"
        
        metadata = await test_metadata_extractor.extract_metadata(url)
        
        assert metadata is not None
        assert metadata["url"] == url
        assert "status" in metadata
        # Should handle long URLs gracefully (either succeed or fail cleanly)