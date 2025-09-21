"""
Metadata extraction service for link previews.

This module provides functionality to extract metadata from URLs including
title, description, images, and other Open Graph/Twitter Card data.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """
    Service for extracting metadata from URLs for link previews.
    
    Supports Open Graph, Twitter Cards, and standard HTML meta tags.
    """
    
    def __init__(self, timeout: int = 10, max_retries: int = 3):
        """
        Initialize the metadata extractor.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set user agent to avoid blocking
        session.headers.update({
            'User-Agent': 'SaveMyLinks/1.0 (Link Preview Bot)'
        })
        
        return session
    
    async def extract_metadata(self, url: str) -> Dict[str, Any]:
        """
        Extract metadata from a URL asynchronously.
        
        Args:
            url: The URL to extract metadata from
            
        Returns:
            Dictionary containing extracted metadata
        """
        try:
            # Run the synchronous extraction in a thread pool
            loop = asyncio.get_event_loop()
            metadata = await loop.run_in_executor(
                None, self._extract_metadata_sync, url
            )
            return metadata
        except Exception as e:
            logger.error(f"Failed to extract metadata from {url}: {str(e)}")
            return self._create_fallback_metadata(url, error=str(e))
    
    def _extract_metadata_sync(self, url: str) -> Dict[str, Any]:
        """
        Synchronous metadata extraction.
        
        Args:
            url: The URL to extract metadata from
            
        Returns:
            Dictionary containing extracted metadata
        """
        # Handle None or empty URLs
        if not url:
            return self._create_fallback_metadata(url, error="Empty or None URL provided")
            
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract metadata
            metadata = {
                'url': url,
                'status': 'success',
                'title': self._extract_title(soup),
                'description': self._extract_description(soup),
                'image': self._extract_image(soup, url),
                'site_name': self._extract_site_name(soup),
                'type': self._extract_type(soup),
                'favicon': self._extract_favicon(soup, url),
                'extracted_at': time.time()
            }
            
            # Clean up empty values
            metadata = {k: v for k, v in metadata.items() if v is not None}
            
            logger.info(f"Successfully extracted metadata from {url}")
            return metadata
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed for {url}: {str(e)}")
            return self._create_fallback_metadata(url, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error extracting metadata from {url}: {str(e)}")
            return self._create_fallback_metadata(url, error=str(e))
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract title from HTML."""
        # Try Open Graph title first
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()
        
        # Try Twitter Card title
        twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
        if twitter_title and twitter_title.get('content'):
            return twitter_title['content'].strip()
        
        # Fall back to HTML title tag
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            return title_tag.string.strip()
        
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract description from HTML."""
        # Try Open Graph description first
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            return og_desc['content'].strip()
        
        # Try Twitter Card description
        twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
        if twitter_desc and twitter_desc.get('content'):
            return twitter_desc['content'].strip()
        
        # Try standard meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()
        
        return None
    
    def _extract_image(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Extract preview image from HTML."""
        # Try Open Graph image first
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return self._resolve_url(og_image['content'], base_url)
        
        # Try Twitter Card image
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image and twitter_image.get('content'):
            return self._resolve_url(twitter_image['content'], base_url)
        
        # Try to find a suitable image in the page
        images = soup.find_all('img', src=True)
        for img in images:
            src = img.get('src')
            if src and self._is_suitable_image(img):
                return self._resolve_url(src, base_url)
        
        return None
    
    def _extract_site_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract site name from HTML."""
        # Try Open Graph site name
        og_site = soup.find('meta', property='og:site_name')
        if og_site and og_site.get('content'):
            return og_site['content'].strip()
        
        # Try Twitter site
        twitter_site = soup.find('meta', attrs={'name': 'twitter:site'})
        if twitter_site and twitter_site.get('content'):
            return twitter_site['content'].strip().lstrip('@')
        
        return None
    
    def _extract_type(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract content type from HTML."""
        og_type = soup.find('meta', property='og:type')
        if og_type and og_type.get('content'):
            return og_type['content'].strip()
        
        return 'website'  # Default type
    
    def _extract_favicon(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Extract favicon URL from HTML."""
        # Try to find favicon link
        favicon_selectors = [
            'link[rel="icon"]',
            'link[rel="shortcut icon"]',
            'link[rel="apple-touch-icon"]'
        ]
        
        for selector in favicon_selectors:
            favicon = soup.select_one(selector)
            if favicon and favicon.get('href'):
                return self._resolve_url(favicon['href'], base_url)
        
        # Default favicon location
        parsed_url = urlparse(base_url)
        default_favicon = f"{parsed_url.scheme}://{parsed_url.netloc}/favicon.ico"
        return default_favicon
    
    def _resolve_url(self, url: str, base_url: str) -> str:
        """Resolve relative URLs to absolute URLs."""
        return urljoin(base_url, url)
    
    def _is_suitable_image(self, img_tag) -> bool:
        """Check if an image is suitable for preview."""
        # Check dimensions if available
        width = img_tag.get('width')
        height = img_tag.get('height')
        
        if width and height:
            try:
                w, h = int(width), int(height)
                # Prefer larger images
                return w >= 200 and h >= 200
            except ValueError:
                pass
        
        # Check for common preview image indicators
        src = img_tag.get('src', '').lower()
        alt = img_tag.get('alt', '').lower()
        
        # Skip common non-preview images
        skip_patterns = ['logo', 'icon', 'avatar', 'button', 'badge']
        if any(pattern in src or pattern in alt for pattern in skip_patterns):
            return False
        
        return True
    
    def _create_fallback_metadata(self, url: str, error: Optional[str] = None) -> Dict[str, Any]:
        """Create fallback metadata when extraction fails."""
        if url:
            parsed_url = urlparse(url)
        else:
            parsed_url = None
        
        # Use time.time() instead of asyncio.get_event_loop().time() to avoid event loop issues
        
        return {
            'url': url,
            'status': 'failed',
            'title': parsed_url.netloc or url if parsed_url else str(url),
            'description': None,
            'image': None,
            'site_name': parsed_url.netloc if parsed_url else None,
            'type': 'website',
            'favicon': f"{parsed_url.scheme}://{parsed_url.netloc}/favicon.ico" if parsed_url and parsed_url.netloc else None,
            'error': error,
            'extracted_at': time.time()
        }


# Create a singleton instance
metadata_extractor = MetadataExtractor()

# Test-specific extractor with faster timeouts for integration tests
test_metadata_extractor = MetadataExtractor(timeout=3, max_retries=1)