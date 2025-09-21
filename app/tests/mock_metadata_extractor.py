"""
Mock metadata extractor for testing purposes.

This module provides a mock implementation of the metadata extractor
that returns predefined responses without making actual HTTP requests.
"""

from typing import Dict, Any, Optional
from unittest.mock import AsyncMock


class MockMetadataExtractor:
    """Mock metadata extractor for testing."""
    
    def __init__(self):
        """Initialize mock extractor with predefined responses."""
        self.mock_responses = {
            "https://github.com": {
                "title": "GitHub: Let's build from here",
                "description": "GitHub is where over 100 million developers shape the future of software, together.",
                "image": "https://github.githubassets.com/images/modules/site/social-cards/github-social.png",
                "url": "https://github.com",
                "site_name": "GitHub",
                "type": "website",
                "status": "success"
            },
            "https://stackoverflow.com": {
                "title": "Stack Overflow - Where Developers Learn, Share, & Build Careers",
                "description": "Stack Overflow is the largest, most trusted online community for developers to learn, share their programming knowledge, and build their careers.",
                "image": "https://cdn.sstatic.net/Sites/stackoverflow/Img/apple-touch-icon@2.png",
                "url": "https://stackoverflow.com",
                "site_name": "Stack Overflow",
                "type": "website",
                "status": "success"
            },
            "https://developer.mozilla.org": {
                "title": "MDN Web Docs",
                "description": "The MDN Web Docs site provides information about Open Web technologies including HTML, CSS, and APIs for both Web sites and progressive web apps.",
                "image": "https://developer.mozilla.org/mdn-social-share.png",
                "url": "https://developer.mozilla.org",
                "site_name": "MDN Web Docs",
                "type": "website",
                "status": "success"
            },
            "https://example.com/invalid": {
                "status": "failed",
                "error": "Failed to fetch metadata"
            }
        }
    
    async def extract_metadata(self, url: str) -> Dict[str, Any]:
        """
        Mock metadata extraction.
        
        Args:
            url: URL to extract metadata from
            
        Returns:
            Mock metadata response
        """
        # Simulate some processing time (much faster than real requests)
        import asyncio
        await asyncio.sleep(0.01)  # 10ms instead of seconds
        
        # Return predefined response or default failure
        return self.mock_responses.get(url, {
            "status": "failed",
            "error": "No mock data available for this URL"
        })
    
    def extract_metadata_sync(self, url: str) -> Dict[str, Any]:
        """
        Mock synchronous metadata extraction.
        
        Args:
            url: URL to extract metadata from
            
        Returns:
            Mock metadata response
        """
        # Return predefined response or default failure
        return self.mock_responses.get(url, {
            "status": "failed",
            "error": "No mock data available for this URL"
        })


# Create a global mock instance for easy importing
mock_metadata_extractor = MockMetadataExtractor()


def create_mock_extractor_patch():
    """
    Create a mock patch for the metadata extractor.
    
    Returns:
        Mock object that can be used with pytest.patch
    """
    mock = AsyncMock()
    mock.extract_metadata.side_effect = mock_metadata_extractor.extract_metadata
    mock.extract_metadata_sync.side_effect = mock_metadata_extractor.extract_metadata_sync
    return mock