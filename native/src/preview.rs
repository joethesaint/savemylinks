//! Link previews, the same rules as app/services/metadata.py: http(s) only, public
//! addresses only (checked again on every redirect), 5 s timeout, 1 MB cap, HTML only.
//! Open Graph wins, then Twitter, then plain tags.
use std::collections::HashMap;
use std::net::IpAddr;
use std::time::Duration;

use scraper::{Html, Selector};
use serde_json::{Map, Value};
use url::Url;

const MAX_BYTES: usize = 1_000_000;
const MAX_REDIRECTS: usize = 3;
const USER_AGENT: &str = "SaveMyLinks/1.0 (link preview)";

/// True for addresses on the public internet; false for loopback, private, link-local,
/// carrier NAT, documentation, multicast and the like (the SSRF guard).
pub fn is_public(ip: IpAddr) -> bool {
    match ip {
        IpAddr::V4(v4) => {
            let o = v4.octets();
            !(v4.is_loopback()
                || v4.is_private()
                || v4.is_link_local()
                || v4.is_broadcast()
                || v4.is_documentation()
                || v4.is_unspecified()
                || v4.is_multicast()
                || o[0] == 0
                || (o[0] == 100 && (o[1] & 0xc0) == 64)
                || o[0] >= 240
                || (o[0] == 192 && o[1] == 0 && o[2] == 0)
                || (o[0] == 198 && (o[1] & 0xfe) == 18))
        }
        IpAddr::V6(v6) => {
            if let Some(v4) = v6.to_ipv4_mapped() {
                return is_public(IpAddr::V4(v4));
            }
            let s = v6.segments();
            !(v6.is_loopback()
                || v6.is_unspecified()
                || v6.is_multicast()
                || (s[0] & 0xfe00) == 0xfc00
                || (s[0] & 0xffc0) == 0xfe80
                || (s[0] == 0x2001 && s[1] == 0x0db8))
        }
    }
}

async fn assert_public(url: &Url) -> Result<(), String> {
    if url.scheme() != "http" && url.scheme() != "https" {
        return Err("not http(s)".into());
    }
    let host = url.host_str().ok_or("no host")?;
    let host = host.trim_start_matches('[').trim_end_matches(']');
    let port = url.port_or_known_default().unwrap_or(80);
    let addrs = tokio::net::lookup_host((host, port)).await.map_err(|_| format!("cannot resolve {host}"))?;
    let mut any = false;
    for a in addrs {
        any = true;
        if !is_public(a.ip()) {
            return Err(format!("{host} resolves to a non-public address"));
        }
    }
    if any { Ok(()) } else { Err(format!("cannot resolve {host}")) }
}

fn clean(v: Option<String>, limit: usize) -> Option<String> {
    let s = v?.split_whitespace().collect::<Vec<_>>().join(" ");
    if s.is_empty() {
        return None;
    }
    Some(s.chars().take(limit).collect())
}

/// Preview fields from HTML; only the fields that were found.
pub fn parse_metadata(html: &str, base: &Url) -> Map<String, Value> {
    let doc = Html::parse_document(html);
    let mut meta: HashMap<String, String> = HashMap::new();
    let sel = Selector::parse("meta").unwrap();
    for m in doc.select(&sel) {
        let el = m.value();
        let key = el.attr("property").or_else(|| el.attr("name")).map(|k| k.to_lowercase());
        if let (Some(k), Some(c)) = (key, el.attr("content")) {
            meta.entry(k).or_insert_with(|| c.to_string());
        }
    }
    let title_sel = Selector::parse("title").unwrap();
    let page_title = doc.select(&title_sel).next().map(|t| t.text().collect::<String>());
    let first = |keys: &[&str]| keys.iter().find_map(|k| meta.get(*k).filter(|v| !v.trim().is_empty()).cloned());

    let image = first(&["og:image", "og:image:url", "twitter:image"])
        .and_then(|i| base.join(&i).ok())
        .filter(|u| u.scheme() == "http" || u.scheme() == "https")
        .map(|u| u.to_string());

    let mut out = Map::new();
    let fields = [
        ("title", clean(first(&["og:title", "twitter:title"]).or(page_title), 300)),
        ("description", clean(first(&["og:description", "twitter:description", "description"]), 1000)),
        ("image", clean(image, 1000)),
        ("site_name", clean(first(&["og:site_name"]).or_else(|| base.host_str().map(String::from)), 200)),
    ];
    for (k, v) in fields {
        if let Some(v) = v {
            out.insert(k.to_string(), Value::String(v));
        }
    }
    out
}

/// Fetch a page and return its preview, or None when it can't be read safely.
pub async fn fetch_metadata(raw: &str) -> Option<Map<String, Value>> {
    let client = reqwest::Client::builder()
        .redirect(reqwest::redirect::Policy::none())
        .timeout(Duration::from_secs(5))
        .user_agent(USER_AGENT)
        .build()
        .ok()?;
    let mut url = Url::parse(raw).ok()?;
    for _ in 0..=MAX_REDIRECTS {
        if assert_public(&url).await.is_err() {
            return None;
        }
        let mut resp = client.get(url.clone()).send().await.ok()?;
        if resp.status().is_redirection() {
            let loc = resp.headers().get(reqwest::header::LOCATION)?.to_str().ok()?.to_string();
            url = url.join(&loc).ok()?;
            continue;
        }
        if resp.status() != reqwest::StatusCode::OK {
            return None;
        }
        let ctype = resp.headers().get(reqwest::header::CONTENT_TYPE).and_then(|v| v.to_str().ok()).unwrap_or("html").to_lowercase();
        if !ctype.contains("html") {
            return None;
        }
        let mut body: Vec<u8> = Vec::new();
        while let Ok(Some(chunk)) = resp.chunk().await {
            body.extend_from_slice(&chunk);
            if body.len() >= MAX_BYTES {
                body.truncate(MAX_BYTES);
                break;
            }
        }
        let html = String::from_utf8_lossy(&body);
        return Some(parse_metadata(&html, &url));
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn public_and_private_addresses() {
        for bad in ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "100.64.0.1", "0.0.0.0", "::1", "fe80::1", "fd00::1", "::ffff:127.0.0.1"] {
            assert!(!is_public(bad.parse().unwrap()), "{bad} must be refused");
        }
        for good in ["93.184.216.34", "1.1.1.1", "2606:4700:4700::1111"] {
            assert!(is_public(good.parse().unwrap()), "{good} is public");
        }
    }

    #[test]
    fn open_graph_wins_and_images_resolve() {
        let base = Url::parse("https://example.com/a/b").unwrap();
        let html = r#"<html><head><title> Plain  title </title>
            <meta property="og:title" content="OG title">
            <meta name="description" content="Plain description">
            <meta property="og:image" content="/img.png">
            <meta property="og:image" content="javascript:alert(1)"></head></html>"#;
        let m = parse_metadata(html, &base);
        assert_eq!(m["title"], "OG title");
        assert_eq!(m["description"], "Plain description");
        assert_eq!(m["image"], "https://example.com/img.png");
        assert_eq!(m["site_name"], "example.com");
        let bad = parse_metadata(r#"<meta property="og:image" content="javascript:alert(1)">"#, &base);
        assert!(bad.get("image").is_none());
    }
}
