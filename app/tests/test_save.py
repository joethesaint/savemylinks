"""Tests for POST /api/save (the extension's one-click save) and URL normalization."""

import pytest

from app.services.urls import UnsupportedURLError, fallback_title, normalize_url


class TestNormalizeUrl:
    @pytest.mark.parametrize("raw, expected", [
        ("HTTPS://Example.COM/Path?a=1#top", "https://example.com/Path?a=1"),
        ("https://example.com", "https://example.com/"),
        ("https://example.com:443/x", "https://example.com/x"),
        ("http://example.com:8080/x", "http://example.com:8080/x"),
        ("https://example.com/a?utm_source=x&id=7&fbclid=y&UTM_medium=z", "https://example.com/a?id=7"),
        ("  https://example.com/a  ", "https://example.com/a"),
    ])
    def test_canonical_form(self, raw, expected):
        assert normalize_url(raw) == expected

    @pytest.mark.parametrize("raw", [
        "chrome://extensions", "about:blank", "file:///C:/x.txt", "javascript:alert(1)",
        "ftp://example.com/f", "edge://settings", "https://user:pw@example.com/",
    ])
    def test_refuses_pages_that_are_not_web_pages(self, raw):
        with pytest.raises(UnsupportedURLError):
            normalize_url(raw)

    def test_fallback_title(self):
        assert fallback_title("https://www.example.com/blog/my-first_post") == "my first post (example.com)"
        assert fallback_title("https://example.com/") == "example.com"


class TestSaveEndpoint:
    async def test_new_page_is_created(self, async_client):
        res = await async_client.post("/api/save", json={"url": "https://example.com/a#x", "title": "A page"})
        assert res.status_code == 201
        body = res.json()
        assert body["created"] is True
        assert body["resource"]["url"] == "https://example.com/a"
        assert body["resource"]["title"] == "A page"

    async def test_same_page_again_is_returned_not_duplicated(self, async_client):
        first = (await async_client.post("/api/save", json={"url": "https://example.com/b"})).json()
        again = await async_client.post("/api/save", json={"url": "https://EXAMPLE.com/b?utm_source=news#top"})
        assert again.status_code == 200
        assert again.json()["created"] is False
        assert again.json()["resource"]["id"] == first["resource"]["id"]
        listing = (await async_client.get("/api/resources/")).json()
        assert listing["total"] == 1

    async def test_long_title_and_note_are_cut_not_refused(self, async_client):
        res = await async_client.post("/api/save", json={"url": "https://example.com/c", "title": "t" * 500, "note": "n" * 3000})
        assert res.status_code == 201
        r = res.json()["resource"]
        assert len(r["title"]) == 200 and r["title"].endswith("…")
        assert len(r["description"]) == 1000

    async def test_missing_title_uses_the_address(self, async_client):
        res = await async_client.post("/api/save", json={"url": "https://example.com/guides/getting-started"})
        assert res.json()["resource"]["title"] == "getting started (example.com)"

    @pytest.mark.parametrize("url", ["chrome://newtab", "javascript:alert(1)", "ftp://example.com/x", "about:blank"])
    async def test_non_web_pages_are_refused(self, async_client, url):
        res = await async_client.post("/api/save", json={"url": url})
        assert res.status_code == 422
        assert "http" in res.json()["detail"]

    async def test_category_is_kept(self, async_client):
        res = await async_client.post("/api/save", json={"url": "https://example.com/d", "category": "Reading"})
        assert res.json()["resource"]["category"] == "Reading"

    async def test_preview_is_fetched_for_new_saves_only(self, async_client, no_network_metadata):
        await async_client.post("/api/save", json={"url": "https://example.com/e"})
        await async_client.post("/api/save", json={"url": "https://example.com/e#again"})
        assert no_network_metadata == ["https://example.com/e"]
