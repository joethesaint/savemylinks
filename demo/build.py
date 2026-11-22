"""Build the static SaveMyLinks demo (GitHub Pages) from the app's real templates and static files.

    python demo/build.py [out_dir]        default out_dir: _site

The pages are the app's own templates rendered once, with links made relative so they work under
any sub-path (https://<user>.github.io/savemylinks/). demo/demo-api.js loads before the app's
scripts and answers their /api/resources calls in the browser, so no server is needed.
Only jinja2 is required.
"""
import re
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
HERE = Path(__file__).resolve().parent

BANNER = (
    '<div class="demo-banner" role="note">'
    "<span><strong>Demo.</strong> Links you save here stay in this browser only. "
    'Previews are simulated. <a href="download.html">Download the full app</a> · <a href="https://github.com/joethesaint/savemylinks">Source</a></span>'
    '<button type="button" class="btn btn-ghost btn-sm" onclick="smlDemoReset()">Reset demo</button>'
    '<span data-app-detect><button type="button" class="btn btn-ghost btn-sm">Have the app? Open it</button></span>'
    "</div>"
)
BANNER_CSS = (
    "<style>.demo-banner{display:flex;flex-wrap:wrap;gap:.5rem 1rem;align-items:center;justify-content:center;"
    "padding:.5rem max(16px,env(safe-area-inset-left,0px));background:#2f6f7a;color:#fff;font-size:.875rem;text-align:center}"
    ".demo-banner a{color:inherit;text-decoration:underline}.demo-banner .btn{color:inherit;border-color:currentColor}</style>"
)

# (what the server-rendered page says, what the static page needs)
REWRITES = [
    ('href="/add"', 'href="add.html"'),
    ('href="/?', 'href="./?'),
    ('href="/"', 'href="./"'),
    ("location.href = '/'", "location.href = './'"),
    # "./" not bare "static/": import('static/x.js') is read as a package name and fails, which
    # silently stopped the assistant (Clippy) loading on the first demo.
    ("'/static/", "'./static/"),
    ("on your own server.", "on your own server. This demo keeps them in your browser."),
]


def render(name: str, active: str, app: bool = False) -> str:
    env = Environment(loader=FileSystemLoader(str(APP / "templates")), autoescape=True)
    env.globals["url_for"] = lambda _name, path: "static" + path
    html = env.get_template(name).render(request=None, active=active)
    for old, new in REWRITES:
        if app and old == "on your own server.":
            continue  # the real app does keep them on your own computer
        html = html.replace(old, new)
    if app:
        return html  # the native app (native/) answers /api itself: no stand-in, no banner
    # The stand-in API must patch fetch before the app's first script runs.
    html = html.replace('<script src="static/sml.js', '<script src="static/demo-api.js"></script>\n    <script src="static/app-detect.js"></script>\n    <script src="static/sml.js', 1)
    html = html.replace("</head>", BANNER_CSS + "\n</head>", 1)
    html = re.sub(r"(<body[^>]*>)", r"\1\n    " + BANNER, html, count=1)
    return html


def build(out: Path, app: bool = False) -> Path:
    """app=False: the static demo. app=True: the same pages for the native app (native/site)."""
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(APP / "static", out / "static")
    # The service worker sits at the root so its scope covers every page (installable app).
    shutil.copy(APP / "static" / "sw.js", out / "sw.js")
    if not app:
        shutil.copy(HERE / "demo-api.js", out / "static" / "demo-api.js")
        shutil.copy(HERE / "download.html", out / "download.html")
        shutil.copy(HERE / "app-detect.js", out / "static" / "app-detect.js")
    sml = out / "static" / "sml.js"
    sml.write_text(sml.read_text(encoding="utf-8").replace("'/?focus=search'", "'./?focus=search'"), encoding="utf-8")
    (out / "index.html").write_text(render("index.html", "library", app), encoding="utf-8")
    (out / "add.html").write_text(render("add.html", "add", app), encoding="utf-8")
    if not app:
        (out / ".nojekyll").write_text("", encoding="utf-8")
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--app"]
    app = "--app" in sys.argv
    target = build(Path(args[0]) if args else ROOT / ("native/site" if app else "_site"), app=app)
    print(f"{'App pages' if app else 'Demo'} built in {target}")
