"""
Link preview metadata: title, description, image and site name.

A save never waits on the network. The route stores the resource, then
`refresh_resource_metadata` runs as a background task and fills
`Resource.link_metadata`. Fetching is guarded: http(s) only, public addresses
only (checked again on every redirect), a short timeout and a size cap.
"""

import asyncio
import ipaddress
import logging
import socket
from html.parser import HTMLParser
from typing import Any, Awaitable, Callable, Dict, Optional
from urllib.parse import urljoin, urlparse

import httpx

from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 5.0
MAX_BYTES = 1_000_000
MAX_REDIRECTS = 3
USER_AGENT = "SaveMyLinks/1.0 (link preview)"
FIELD_LIMITS = {"title": 300, "description": 1000, "image": 1000, "site_name": 200}

# Swapped out in tests so no test touches the network or the real database.
session_factory = AsyncSessionLocal


async def _fetch_with_default_client(url: str) -> Optional[Dict[str, Any]]:
    return await fetch_metadata(url)


# What background refreshes call. Tests replace it so they never reach the network.
preview_fetcher: Callable[[str], Awaitable[Optional[Dict[str, Any]]]] = _fetch_with_default_client


class UnsafeURLError(ValueError):
    """The URL is not http(s) or points at a non-public address."""


class _MetaParser(HTMLParser):
    """Collects <title> and <meta> tags from the document head."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: Dict[str, str] = {}
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (a.get("property") or a.get("name") or "").strip().lower()
            if key and "content" in a and key not in self.meta:
                self.meta[key] = a["content"].strip()

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


def _clean(value: Optional[str], limit: int) -> Optional[str]:
    if not value:
        return None
    value = " ".join(value.split())
    return value[:limit] or None


def parse_metadata(html: str, base_url: str) -> Dict[str, Any]:
    """Extract preview fields from HTML. Open Graph wins, then Twitter, then plain tags."""
    parser = _MetaParser()
    try:
        parser.feed(html)
    except Exception:  # malformed HTML: keep whatever was read
        logger.debug("HTML parse stopped early for %s", base_url)
    m = parser.meta

    def first(*keys: str) -> Optional[str]:
        return next((m[k] for k in keys if m.get(k)), None)

    image = first("og:image", "og:image:url", "twitter:image")
    if image:
        image = urljoin(base_url, image)
        if urlparse(image).scheme not in ("http", "https"):
            image = None

    data = {
        "title": _clean(first("og:title", "twitter:title") or parser.title, FIELD_LIMITS["title"]),
        "description": _clean(first("og:description", "twitter:description", "description"), FIELD_LIMITS["description"]),
        "image": _clean(image, FIELD_LIMITS["image"]),
        "site_name": _clean(first("og:site_name") or urlparse(base_url).hostname, FIELD_LIMITS["site_name"]),
    }
    return {k: v for k, v in data.items() if v}


async def assert_public_url(url: str) -> None:
    """Raise UnsafeURLError unless the URL is http(s) and every address it resolves to is public."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise UnsafeURLError(f"Not an http(s) URL: {url}")
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(parsed.hostname, parsed.port or None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Cannot resolve {parsed.hostname}") from exc
    for info in infos:
        address = ipaddress.ip_address(info[4][0].split("%")[0])
        if not address.is_global or address.is_multicast:
            raise UnsafeURLError(f"{parsed.hostname} resolves to a non-public address")


async def fetch_metadata(url: str, client: Optional[httpx.AsyncClient] = None) -> Optional[Dict[str, Any]]:
    """
    Fetch a page and return its preview fields, or None when it can't be read safely.

    Redirects are followed by hand so each hop passes the public-address check.
    """
    own_client = client is None
    client = client or httpx.AsyncClient(timeout=TIMEOUT_SECONDS, follow_redirects=False, headers={"User-Agent": USER_AGENT})
    try:
        for _ in range(MAX_REDIRECTS + 1):
            await assert_public_url(url)
            async with client.stream("GET", url) as response:
                if response.is_redirect and response.headers.get("location"):
                    url = urljoin(url, response.headers["location"])
                    continue
                if response.status_code != 200:
                    logger.info("Metadata fetch for %s returned %s", url, response.status_code)
                    return None
                if "html" not in response.headers.get("content-type", "html").lower():
                    return None
                body = b""
                async for chunk in response.aiter_bytes():
                    body += chunk
                    if len(body) >= MAX_BYTES:
                        break
                html = body[:MAX_BYTES].decode(response.encoding or "utf-8", errors="replace")
                return parse_metadata(html, url)
        logger.info("Too many redirects for %s", url)
        return None
    except UnsafeURLError as exc:
        logger.warning("Metadata fetch refused: %s", exc)
        return None
    except httpx.HTTPError as exc:
        logger.info("Metadata fetch failed for %s: %s", url, exc)
        return None
    finally:
        if own_client:
            await client.aclose()


async def refresh_resource_metadata(
    resource_id: int,
    url: str,
    fetcher: Optional[Callable[[str], Awaitable[Optional[Dict[str, Any]]]]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Fetch the preview for a saved resource's URL and store it.

    Safe to run as a background task: the database is touched only when there is
    a preview to store, and only if the resource still has that URL.
    """
    from app.models import Resource  # local import: models import the database module

    metadata = await (fetcher or preview_fetcher)(url)
    if not metadata:
        return None
    async with session_factory() as db:
        resource = await db.get(Resource, resource_id)
        if resource is None or resource.url != url:  # deleted or edited meanwhile
            return None
        resource.link_metadata = metadata
        await db.commit()
    return metadata
