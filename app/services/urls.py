"""
URL normalization for one-click saves.

Two addresses that open the same page should be saved once. normalize_url keeps
everything that changes the page and drops what doesn't: the #fragment,
tracking parameters, default ports and letter case in the scheme and host.
"""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PREFIXES = ("utm_",)
TRACKING_PARAMS = {"fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid", "igshid", "ref_src"}
DEFAULT_PORTS = {"http": 80, "https": 443}


class UnsupportedURLError(ValueError):
    """Not an http(s) address: browser pages, files, javascript: and the like."""


def normalize_url(raw: str) -> str:
    """Return the canonical form of an http(s) URL, or raise UnsupportedURLError."""
    parts = urlsplit(raw.strip())
    scheme = parts.scheme.lower()
    if scheme not in DEFAULT_PORTS or not parts.hostname:
        raise UnsupportedURLError(f"Only http and https pages can be saved, not {scheme or 'this address'}.")

    host = parts.hostname.lower()
    if ":" in host:  # IPv6 literal
        host = f"[{host}]"
    if parts.port and parts.port != DEFAULT_PORTS[scheme]:
        host = f"{host}:{parts.port}"
    if parts.username:
        raise UnsupportedURLError("Addresses with a user name or password can't be saved.")

    query = [
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith(TRACKING_PREFIXES) and k.lower() not in TRACKING_PARAMS
    ]
    return urlunsplit((scheme, host, parts.path or "/", urlencode(query, doseq=True), ""))


def fallback_title(url: str) -> str:
    """A readable title when the page sent none: the host plus the last path segment."""
    parts = urlsplit(url)
    host = (parts.hostname or url).removeprefix("www.")
    last = [p for p in parts.path.split("/") if p]
    return f"{last[-1].replace('-', ' ').replace('_', ' ')} ({host})" if last else host
