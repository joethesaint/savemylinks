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


def test_demo_api_loads_before_the_app_scripts(tmp_path):
    out = build(tmp_path / "site")
    for page in ["index.html", "add.html"]:
        html = (out / page).read_text(encoding="utf-8")
        assert html.index("static/demo-api.js") < html.index("static/sml.js")
        assert "Reset demo" in html
