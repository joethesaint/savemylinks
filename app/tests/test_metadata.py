"""
Tests for link previews (app/services/metadata.py) and how saving uses them.

No test touches the internet: pages come from httpx.MockTransport, and hosts are
literal IP addresses so no DNS lookup happens.
"""

import httpx
import pytest
from sqlalchemy import create_engine, inspect, text

from app.database import Base, _add_missing_columns
from app.services import metadata

PUBLIC = "http://93.184.216.34"  # a public address; never contacted, the transport is mocked

PAGE = """<html><head>
<title>  Plain   title </title>
<meta property="og:title" content="OG title">
<meta property="og:description" content="OG description">
<meta property="og:image" content="/img/cover.png">
<meta property="og:site_name" content="Example Site">
<meta name="description" content="Plain description">
</head><body>Hi</body></html>"""


def client_for(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)


class TestParseMetadata:
    def test_open_graph_wins_and_image_is_made_absolute(self):
        data = metadata.parse_metadata(PAGE, f"{PUBLIC}/post")
        assert data == {
            "title": "OG title",
            "description": "OG description",
            "image": f"{PUBLIC}/img/cover.png",
            "site_name": "Example Site",
        }

    def test_falls_back_to_plain_tags_and_host(self):
        html = '<title> A  page </title><meta name="description" content="About it">'
        data = metadata.parse_metadata(html, "https://blog.example.org/x")
        assert data == {"title": "A page", "description": "About it", "site_name": "blog.example.org"}

    def test_drops_a_non_http_image(self):
        html = '<meta property="og:image" content="javascript:alert(1)">'
        assert "image" not in metadata.parse_metadata(html, f"{PUBLIC}/")

    def test_long_values_are_cut(self):
        html = f"<title>{'x' * 900}</title>"
        assert len(metadata.parse_metadata(html, f"{PUBLIC}/")["title"]) == metadata.FIELD_LIMITS["title"]


class TestPublicAddressGuard:
    @pytest.mark.parametrize("url", [
        "ftp://93.184.216.34/file",
        "javascript:alert(1)",
        "http://127.0.0.1/",
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/",
    ])
    async def test_refuses(self, url):
        with pytest.raises(metadata.UnsafeURLError):
            await metadata.assert_public_url(url)

    async def test_allows_a_public_address(self):
        await metadata.assert_public_url(f"{PUBLIC}/page")


class TestFetchMetadata:
    async def test_reads_an_html_page(self):
        def handler(request):
            return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text=PAGE)
        async with client_for(handler) as client:
            data = await metadata.fetch_metadata(f"{PUBLIC}/post", client=client)
        assert data["title"] == "OG title"

    async def test_follows_a_public_redirect(self):
        def handler(request):
            if request.url.path == "/old":
                return httpx.Response(301, headers={"location": "/new"})
            return httpx.Response(200, headers={"content-type": "text/html"}, text="<title>New</title>")
        async with client_for(handler) as client:
            assert (await metadata.fetch_metadata(f"{PUBLIC}/old", client=client))["title"] == "New"

    async def test_refuses_a_redirect_into_the_private_network(self):
        seen = []
        def handler(request):
            seen.append(str(request.url))
            return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data"})
        async with client_for(handler) as client:
            assert await metadata.fetch_metadata(f"{PUBLIC}/go", client=client) is None
        assert seen == [f"{PUBLIC}/go"], "the private address is never requested"

    @pytest.mark.parametrize("response", [
        httpx.Response(404, text="missing"),
        httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF"),
    ])
    async def test_returns_none_for_unusable_responses(self, response):
        async with client_for(lambda request: response) as client:
            assert await metadata.fetch_metadata(f"{PUBLIC}/x", client=client) is None

    async def test_returns_none_when_the_site_is_down(self):
        def handler(request):
            raise httpx.ConnectTimeout("timed out", request=request)
        async with client_for(handler) as client:
            assert await metadata.fetch_metadata(f"{PUBLIC}/x", client=client) is None

    async def test_stops_reading_at_the_size_cap(self, monkeypatch):
        monkeypatch.setattr(metadata, "MAX_BYTES", 40)
        body = "<title>Short</title>" + "x" * 5000 + "<title>Late</title>"
        handler = lambda request: httpx.Response(200, headers={"content-type": "text/html"}, text=body)
        async with client_for(handler) as client:
            assert (await metadata.fetch_metadata(f"{PUBLIC}/big", client=client))["title"] == "Short"


class TestSavingWithPreviews:
    async def test_save_returns_at_once_and_the_preview_follows(self, async_client, monkeypatch):
        async def fake_fetch(url):
            return {"title": "Fetched", "image": f"{PUBLIC}/i.png"}
        monkeypatch.setattr(metadata, "preview_fetcher", fake_fetch)

        created = await async_client.post("/api/resources/", json={"title": "Mine", "url": f"{PUBLIC}/a"})
        assert created.status_code == 201
        assert created.json()["link_metadata"] is None

        stored = (await async_client.get(f"/api/resources/{created.json()['id']}")).json()
        assert stored["link_metadata"] == {"title": "Fetched", "image": f"{PUBLIC}/i.png"}
        assert stored["title"] == "Mine", "the user's own title is never overwritten"

    async def test_a_failed_fetch_still_saves_the_link(self, async_client, no_network_metadata):
        created = await async_client.post("/api/resources/", json={"title": "Offline", "url": f"{PUBLIC}/b"})
        assert created.status_code == 201
        assert no_network_metadata == [f"{PUBLIC}/b"]
        assert (await async_client.get(f"/api/resources/{created.json()['id']}")).json()["link_metadata"] is None

    async def test_changing_the_url_replaces_the_preview(self, async_client, monkeypatch):
        async def fake_fetch(url):
            return {"title": url.rsplit("/", 1)[-1]}
        monkeypatch.setattr(metadata, "preview_fetcher", fake_fetch)

        rid = (await async_client.post("/api/resources/", json={"title": "T", "url": f"{PUBLIC}/first"})).json()["id"]
        updated = await async_client.put(f"/api/resources/{rid}", json={"url": f"{PUBLIC}/second"})
        assert updated.status_code == 200
        assert (await async_client.get(f"/api/resources/{rid}")).json()["link_metadata"] == {"title": "second"}

    async def test_refresh_endpoint(self, async_client, monkeypatch):
        rid = (await async_client.post("/api/resources/", json={"title": "T", "url": f"{PUBLIC}/c"})).json()["id"]

        async def fake_fetch(url):
            return {"title": "Now available"}
        monkeypatch.setattr(metadata, "preview_fetcher", fake_fetch)

        refreshed = await async_client.post(f"/api/resources/{rid}/metadata")
        assert refreshed.status_code == 200
        assert refreshed.json()["link_metadata"] == {"title": "Now available"}
        assert (await async_client.post("/api/resources/99999/metadata")).status_code == 404


def test_existing_database_gains_the_column_and_keeps_its_rows(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:  # the table as it was before link previews
        conn.execute(text(
            "CREATE TABLE resources (id INTEGER PRIMARY KEY, title VARCHAR(200) NOT NULL, url VARCHAR(500) NOT NULL UNIQUE,"
            " description TEXT, category VARCHAR(100), created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)"
        ))
        conn.execute(text("INSERT INTO resources VALUES (1, 'Old', 'https://old.example', NULL, NULL, '2025-01-01', '2025-01-01')"))

    with engine.begin() as conn:
        Base.metadata.create_all(conn)
        _add_missing_columns(conn)
        _add_missing_columns(conn)  # running again changes nothing

    with engine.connect() as conn:
        assert "link_metadata" in {c["name"] for c in inspect(conn).get_columns("resources")}
        assert conn.execute(text("SELECT title, link_metadata FROM resources")).all() == [("Old", None)]
    engine.dispose()
