//! URL rules, the same as app/services/urls.py: one canonical form per page, so the same
//! page is saved once.
use url::Url;

const TRACKING_PARAMS: [&str; 8] = ["fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid", "igshid", "ref_src"];

/// Canonical http(s) URL: lowercase scheme and host, no default port, no #fragment,
/// no tracking parameters (utm_*, fbclid, ...). Errors are shown to the person as-is.
pub fn normalize_url(raw: &str) -> Result<String, String> {
    let mut url = Url::parse(raw.trim()).map_err(|_| "Only http and https pages can be saved, not this address.".to_string())?;
    let scheme = url.scheme().to_string();
    if (scheme != "http" && scheme != "https") || url.host_str().is_none() {
        return Err(format!("Only http and https pages can be saved, not {}.", if scheme.is_empty() { "this address" } else { &scheme }));
    }
    if !url.username().is_empty() || url.password().is_some() {
        return Err("Addresses with a user name or password can't be saved.".to_string());
    }
    url.set_fragment(None);
    let kept: Vec<(String, String)> = url
        .query_pairs()
        .filter(|(k, _)| {
            let k = k.to_lowercase();
            !k.starts_with("utm_") && !TRACKING_PARAMS.contains(&k.as_str())
        })
        .map(|(k, v)| (k.into_owned(), v.into_owned()))
        .collect();
    if kept.is_empty() {
        url.set_query(None);
    } else {
        let q = url::form_urlencoded::Serializer::new(String::new()).extend_pairs(kept).finish();
        url.set_query(Some(&q));
    }
    Ok(url.to_string())
}

/// A readable title when the page sent none: the last path segment plus the host.
pub fn fallback_title(url: &str) -> String {
    let Ok(u) = Url::parse(url) else { return url.to_string() };
    let host = u.host_str().unwrap_or(url).trim_start_matches("www.").to_string();
    match u.path_segments().and_then(|s| s.filter(|p| !p.is_empty()).last()) {
        Some(last) => format!("{} ({})", last.replace(['-', '_'], " "), host),
        None => host,
    }
}

/// Is this a valid http(s) URL as the create/edit form requires? Returns the stored form.
pub fn parse_http_url(raw: &str) -> Option<String> {
    let u = Url::parse(raw.trim()).ok()?;
    if (u.scheme() == "http" || u.scheme() == "https") && u.host_str().is_some() {
        Some(u.to_string())
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalizes_like_the_python_app() {
        assert_eq!(normalize_url("HTTPS://Example.COM:443/a?utm_source=x&b=1#top").unwrap(), "https://example.com/a?b=1");
        assert_eq!(normalize_url("http://example.com").unwrap(), "http://example.com/");
        assert_eq!(normalize_url("https://x.com/p?fbclid=1").unwrap(), "https://x.com/p");
        assert!(normalize_url("ftp://x.com/").is_err());
        assert!(normalize_url("https://u:p@x.com/").is_err());
        assert!(normalize_url("chrome://settings").is_err());
    }

    #[test]
    fn fallback_titles() {
        assert_eq!(fallback_title("https://www.example.com/my-great_post"), "my great post (example.com)");
        assert_eq!(fallback_title("https://example.com/"), "example.com");
    }
}
