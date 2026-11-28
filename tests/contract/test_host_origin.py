"""
Host and Origin: the native app and the FastAPI app refuse the same requests.

The server answers only to its own address (127.0.0.1 or localhost, with its port). A change
(POST, PUT, PATCH, DELETE) that names an Origin must come from the app's own pages or from the
browser extension. Run against either app; CI runs it against both:

    SAVEMYLINKS_URL=http://127.0.0.1:8765 python -m pytest tests/contract/test_host_origin.py
"""
import os
import urllib.parse
import uuid

import httpx
import pytest

BASE = os.environ.get("SAVEMYLINKS_URL")
pytestmark = pytest.mark.skipif(not BASE, reason="set SAVEMYLINKS_URL to a running server")


@pytest.fixture(scope="module")
def api():
    with httpx.Client(base_url=BASE, timeout=10) as c:
        yield c


@pytest.fixture(scope="module")
def port():
    return urllib.parse.urlsplit(BASE).port


def u():
    return f"https://example.com/{uuid.uuid4().hex[:10]}"


@pytest.mark.parametrize("host_of", [lambda p: f"127.0.0.1:{p}", lambda p: f"localhost:{p}"])
def test_own_address_is_served(api, port, host_of):
    r = api.get("/health", headers={"Host": host_of(port)})
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("host_of", [
    lambda p: "evil.example",                 # another site's name
    lambda p: f"evil.example:{p}",            # another site's name, our port
    lambda p: "127.0.0.1",                    # our address without the port
    lambda p: f"127.0.0.1:{p + 1}",           # our address, another port
])
def test_other_hosts_are_refused(api, port, host_of):
    r = api.get("/health", headers={"Host": host_of(port)})
    assert r.status_code == 400, r.text


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
def test_changes_from_another_site_are_refused(api, port, method):
    headers = {"Origin": "https://evil.example"}
    if method == "POST":
        r = api.post("/api/resources/", json={"title": "x", "url": u()}, headers=headers)
    elif method == "PUT":
        r = api.put("/api/resources/1", json={"title": "x"}, headers=headers)
    else:
        r = api.delete("/api/resources/1", headers=headers)
    assert r.status_code == 403, r.text


def test_change_from_our_own_origin_is_allowed(api, port):
    r = api.post("/api/resources/", json={"title": "mine", "url": u()},
                 headers={"Origin": f"http://127.0.0.1:{port}"})
    assert r.status_code == 201, r.text


def test_change_from_the_browser_extension_is_allowed(api, port):
    r = api.post("/api/resources/", json={"title": "from extension", "url": u()},
                 headers={"Origin": "chrome-extension://abcdefghijklmnop"})
    assert r.status_code == 201, r.text


def test_change_without_an_origin_is_allowed(api, port):
    # Command-line tools and the test client send no Origin header.
    r = api.post("/api/resources/", json={"title": "no origin", "url": u()})
    assert r.status_code == 201, r.text


def test_reads_from_another_origin_are_not_refused(api, port):
    # Only changes are refused by Origin; a read is still answered (same-origin policy covers reads).
    r = api.get("/api/resources/", headers={"Origin": "https://evil.example"})
    assert r.status_code == 200, r.text
