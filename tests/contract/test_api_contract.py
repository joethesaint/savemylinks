"""
The API contract, checked against a running server: the FastAPI app and the native app must
both pass it unchanged, so the pages, the demo and the browser extension work with either.

    SAVEMYLINKS_URL=http://127.0.0.1:8765 python -m pytest tests/contract -p no:cacheprovider

Skipped when SAVEMYLINKS_URL is not set. Link previews need the network, so they are not
checked here (the native app's own tests cover the parser and the address guard).
"""
import os
import time
import uuid

import httpx
import pytest

BASE = os.environ.get("SAVEMYLINKS_URL")
pytestmark = pytest.mark.skipif(not BASE, reason="set SAVEMYLINKS_URL to a running server")


@pytest.fixture(scope="module")
def api():
    with httpx.Client(base_url=BASE, timeout=10) as c:
        yield c


def u(tag=""):
    return f"https://example.com/{tag}{uuid.uuid4().hex[:10]}"


def make(api, **kw):
    body = {"title": "A page", "url": u(), **kw}
    r = api.post("/api/resources/", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_health_and_pages(api):
    assert api.get("/health").json() == {"status": "healthy", "service": "SaveMyLinks"}
    for path in ["/", "/add"]:
        r = api.get(path)
        assert r.status_code == 200 and "SaveMyLinks" in r.text, path
    assert api.get("/static/sml.js").status_code == 200


def test_create_returns_the_resource(api):
    r = make(api, description="note", category="Contract")
    assert set(r) >= {"id", "title", "url", "description", "category", "link_metadata", "created_at", "updated_at"}
    assert (r["title"], r["description"], r["category"]) == ("A page", "note", "Contract")
    bare = api.post("/api/resources/", json={"title": "Bare", "url": f"https://{uuid.uuid4().hex[:8]}.example.com"})
    assert bare.status_code == 201 and bare.json()["url"].endswith(".example.com/"), "a bare host gets a trailing slash"


def test_duplicate_is_409(api):
    r = make(api)
    again = api.post("/api/resources/", json={"title": "Again", "url": r["url"]})
    assert again.status_code == 409
    assert again.json() == {"detail": "A resource with this URL already exists"}


@pytest.mark.parametrize("body,field", [
    ({"title": "x", "url": "not a url"}, "url"),
    ({"title": "x", "url": "ftp://example.com/f"}, "url"),
    ({"title": "", "url": "https://example.com/e"}, "title"),
    ({"url": "https://example.com/m"}, "title"),
    ({"title": "x" * 201, "url": "https://example.com/l"}, "title"),
    ({"title": "x", "url": "https://example.com/d", "description": "x" * 1001}, "description"),
])
def test_invalid_fields_are_422_naming_the_field(api, body, field):
    r = api.post("/api/resources/", json=body)
    assert r.status_code == 422
    fields = [e["loc"][-1] for e in r.json()["detail"]]
    assert field in fields
    if body.get("title", "") and len(body.get("title", "")) > 200:
        err = next(e for e in r.json()["detail"] if e["loc"][-1] == "title")
        assert err["ctx"]["max_length"] == 200


def test_list_search_category_and_paging(api):
    cat = f"Cat{uuid.uuid4().hex[:6]}"
    first = make(api, title="Older Zebra", category=cat)
    time.sleep(1.1)  # the FastAPI app stores whole seconds
    second = make(api, title="Newer zebra", category=cat, description="has NEEDLE inside")
    r = api.get("/api/resources/", params={"category": cat, "per_page": 10})
    body = r.json()
    assert body["total"] == 2 and body["page"] == 1 and body["per_page"] == 10
    assert [x["id"] for x in body["resources"]] == [second["id"], first["id"]], "newest first"
    hits = api.get("/api/resources/", params={"category": cat, "search": "needle"}).json()
    assert [x["id"] for x in hits["resources"]] == [second["id"]], "search is case-insensitive, title or description"
    one = api.get("/api/resources/", params={"category": cat, "per_page": 1, "page": 2}).json()
    assert one["total"] == 2 and [x["id"] for x in one["resources"]] == [first["id"]]
    assert api.get("/api/resources/", params={"per_page": 0}).status_code == 422
    assert api.get("/api/resources/", params={"per_page": 101}).status_code == 422


def test_categories_are_distinct_and_sorted(api):
    tag = uuid.uuid4().hex[:6]
    for c in [f"b{tag}", f"a{tag}", f"b{tag}"]:
        make(api, category=c)
    cats = api.get("/api/resources/categories").json()
    mine = [c for c in cats if c.endswith(tag)]
    assert mine == [f"a{tag}", f"b{tag}"]
    assert cats == sorted(cats)


def test_read_update_delete(api):
    r = make(api)
    assert api.get(f"/api/resources/{r['id']}").json()["id"] == r["id"]
    upd = api.put(f"/api/resources/{r['id']}", json={"title": "Renamed", "category": "Edited"})
    assert upd.status_code == 200 and upd.json()["title"] == "Renamed" and upd.json()["url"] == r["url"]
    other = make(api)
    clash = api.put(f"/api/resources/{r['id']}", json={"url": other["url"]})
    assert clash.status_code == 409
    assert api.put(f"/api/resources/{r['id']}", json={"title": ""}).status_code == 422
    assert api.delete(f"/api/resources/{r['id']}").json() == {"message": "Resource deleted successfully"}
    assert api.get(f"/api/resources/{r['id']}").status_code == 404
    assert api.delete(f"/api/resources/{r['id']}").status_code == 404
    assert api.put(f"/api/resources/{r['id']}", json={"title": "x"}).status_code == 404


def test_extension_save_normalizes_and_never_duplicates(api):
    path = uuid.uuid4().hex[:10]
    first = api.post("/api/save", json={"url": f"HTTPS://Example.COM/{path}?utm_source=x&keep=1#top", "title": "  Tab   title  "})
    assert first.status_code == 201, first.text
    res = first.json()
    assert res["created"] is True
    assert res["resource"]["url"] == f"https://example.com/{path}?keep=1"
    assert res["resource"]["title"] == "Tab title"
    again = api.post("/api/save", json={"url": f"https://example.com/{path}?keep=1"})
    assert again.status_code == 200 and again.json()["created"] is False
    assert again.json()["resource"]["id"] == res["resource"]["id"]
    untitled = api.post("/api/save", json={"url": f"https://www.example.com/my-{path}"})
    assert untitled.json()["resource"]["title"] == f"my {path} (example.com)"
    bad = api.post("/api/save", json={"url": "ftp://example.com/x"})
    assert bad.status_code == 422 and isinstance(bad.json()["detail"], str)


# ── from the first CodeRabbit review: the native app must reject these exactly as FastAPI does ──

def test_non_integer_id_is_422_on_every_route(api):
    for method in ["GET", "PUT", "DELETE"]:
        r = api.request(method, "/api/resources/not-a-number", json={} if method == "PUT" else None)
        assert r.status_code == 422, method
        assert isinstance(r.json()["detail"], list)
    assert api.post("/api/resources/not-a-number/metadata").status_code == 422


def test_update_body_must_be_an_object(api):
    r = make(api)
    for body in ["[]", "null", "42"]:
        res = api.put(f"/api/resources/{r['id']}", content=body, headers={"Content-Type": "application/json"})
        assert res.status_code == 422, body
    same = api.put(f"/api/resources/{r['id']}", json={})
    assert same.status_code == 200 and same.json()["title"] == r["title"], "{} is a valid empty update"


@pytest.mark.parametrize("extra,field", [
    ({"note": 42}, "note"),
    ({"title": ["x"]}, "title"),
    ({"category": "x" * 101}, "category"),
])
def test_extension_save_checks_types_and_limits(api, extra, field):
    r = api.post("/api/save", json={"url": f"https://example.com/{uuid.uuid4().hex[:8]}", **extra})
    assert r.status_code == 422
    assert field in [e["loc"][-1] for e in r.json()["detail"]]
    assert api.post("/api/save", json={"url": 42}).status_code == 422
    assert api.post("/api/save", content="[]", headers={"Content-Type": "application/json"}).status_code == 422
