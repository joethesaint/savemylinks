"""The static demo build: every page works under a sub-path and loads the stand-in API first."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import build  # noqa: E402


def test_build_makes_both_pages_and_static_files(tmp_path):
    out = build(tmp_path / "site")
    for f in ["index.html", "add.html", ".nojekyll", "static/demo-api.js", "static/sml.js", "static/sml.css", "static/agents/Clippy/agent.json"]:
        assert (out / f).exists(), f


def test_no_root_absolute_links_remain(tmp_path):
    out = build(tmp_path / "site")
    for page in ["index.html", "add.html"]:
        html = (out / page).read_text(encoding="utf-8")
        # Root-absolute links break under https://<user>.github.io/savemylinks/
        assert not re.search(r'(href|src)="/(?!/)', html), page
        assert "'/static/" not in html
        assert "location.href = '/'" not in html
    assert "'/?focus=search'" not in (out / "static" / "sml.js").read_text(encoding="utf-8")


def test_dynamic_imports_use_a_relative_path(tmp_path):
    # import('static/x.js') is a bare module name, not a file: the browser refuses it.
    out = build(tmp_path / "site")
    for page in ["index.html", "add.html"]:
        html = (out / page).read_text(encoding="utf-8")
        specs = re.findall(r"import\(\s*['\"]([^'\"]+)['\"]", html)
        assert specs, f"{page}: expected the assistant's dynamic import"
        for spec in specs:
            assert spec.startswith(("./", "../", "/", "http")), f"{page}: bare import specifier {spec!r}"
        assert (out / "static" / "modern-clippy.js").exists()


def test_app_build_has_no_demo_parts(tmp_path):
    out = build(tmp_path / "site", app=True)
    for page in ["index.html", "add.html"]:
        html = (out / page).read_text(encoding="utf-8")
        assert "demo-api.js" not in html and "Reset demo" not in html
        assert not re.search(r'(href|src)="/(?!/)', html), page
    assert not (out / "static" / "demo-api.js").exists()
    assert (out / "static" / "modern-clippy.js").exists()


def test_demo_api_loads_before_the_app_scripts(tmp_path):
    out = build(tmp_path / "site")
    for page in ["index.html", "add.html"]:
        html = (out / page).read_text(encoding="utf-8")
        assert html.index("static/demo-api.js") < html.index("static/sml.js")
        assert "Reset demo" in html


def test_installable_app_files(tmp_path):
    import json
    for app in (False, True):
        out = build(tmp_path / f"site-{app}", app=app)
        assert (out / "sw.js").exists(), "the service worker must sit at the root"
        m = json.loads((out / "static" / "manifest.webmanifest").read_text(encoding="utf-8"))
        assert m["share_target"]["params"] == {"title": "title", "text": "text", "url": "url"}
        for icon in m["icons"]:
            assert (out / "static" / icon["src"]).exists(), icon["src"]
        html = (out / "index.html").read_text(encoding="utf-8")
        assert 'rel="manifest"' in html and "./sw.js" in html


def test_download_page_is_demo_only_and_links_home(tmp_path):
    demo = build(tmp_path / "demo")
    page = (demo / "download.html").read_text(encoding="utf-8")
    for must in ["releases/latest", "LICENSE", "github.com/joethesaint/savemylinks", 'href="./"', "digest"]:
        assert must in page, must
    assert "download.html" in (demo / "index.html").read_text(encoding="utf-8"), "the demo banner links to it"
    assert not (build(tmp_path / "app", app=True) / "download.html").exists()


def test_pages_have_a_link_preview(tmp_path):
    out = build(tmp_path / "demo")
    for page in ["index.html", "add.html", "download.html"]:
        html = (out / page).read_text(encoding="utf-8")
        assert 'property="og:image" content="https://' in html, page
        assert 'name="twitter:card" content="summary_large_image"' in html, page
    assert (out / "static" / "art" / "social-card.png").exists()


def test_local_app_detection_is_demo_only(tmp_path):
    demo = build(tmp_path / "demo")
    for page in ["index.html", "download.html"]:
        html = (demo / page).read_text(encoding="utf-8")
        assert "static/app-detect.js" in html and "data-app-detect" in html, page
    assert (demo / "static" / "app-detect.js").exists()
    app = build(tmp_path / "app", app=True)
    assert "app-detect" not in (app / "index.html").read_text(encoding="utf-8"), "the real app never probes itself"


def test_phone_build_can_move_links_in_and_out(tmp_path):
    # Import/Export JSON (26 Nov 2026): the phone demo must carry the buttons and the script, or links can't be moved.
    out = build(tmp_path / "site")
    html = (out / "index.html").read_text(encoding="utf-8")
    assert 'id="importBtn"' in html and 'id="exportBtn"' in html and 'id="importFile"' in html
    assert "static/transfer.js" in html
    assert (out / "static" / "transfer.js").exists()


def test_clear_and_reset_take_two_clicks(tmp_path):
    # J03, 27 Nov: "Clear all" and "Reset demo" wipe the demo library, so they sit behind a "Demo options"
    # disclosure: one click opens it, a second click acts. No button that wipes is on the banner itself.
    out = build(tmp_path / "site")
    for page in ["index.html", "add.html"]:
        html = (out / page).read_text(encoding="utf-8")
        m = re.search(r'<details class="demo-actions">\s*<summary[^>]*>Demo options</summary>(.*?)</details>', html, re.S)
        assert m, f"{page}: no Demo options disclosure"
        inside = m.group(1)
        assert "smlDemoClear()" in inside and "smlDemoReset()" in inside, page
        outside = html.replace(m.group(0), "")
        assert "smlDemoClear()" not in outside and "smlDemoReset()" not in outside, f"{page}: a wipe button outside the disclosure"
