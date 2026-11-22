//! SaveMyLinks as one program. Serves the app's own pages (built from app/templates by
//! demo/build.py --app) and the same JSON API as the FastAPI app, on 127.0.0.1 only.
//!
//!   savemylinks                 start on port 8000 and open the browser
//!   --port 8123 --db my.db      another port or library file (env: SAVEMYLINKS_PORT, SAVEMYLINKS_DB)
//!   --no-browser                don't open a browser window (env: SAVEMYLINKS_NO_BROWSER=1)
mod db;
mod preview;
mod urls;

use std::sync::{Arc, Mutex};

use axum::{
    body::Body,
    extract::{rejection::PathRejection, Path, Query, State},
    http::{header, StatusCode, Uri},
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use rust_embed::RustEmbed;
use serde::Deserialize;
use serde_json::{json, Value};

use db::{Fields, Store, Write};

#[derive(RustEmbed)]
#[folder = "site/"]
struct Site;

type AppState = Arc<Mutex<Store>>;

// ── errors in FastAPI's shapes, so the pages show their own messages ──
fn detail(status: StatusCode, msg: &str) -> Response {
    (status, Json(json!({ "detail": msg }))).into_response()
}
fn invalid(errors: Vec<Value>) -> Response {
    (StatusCode::UNPROCESSABLE_ENTITY, Json(json!({ "detail": errors }))).into_response()
}
fn field_error(loc: &str, field: &str, kind: &str, msg: String, input: &Value, ctx: Option<Value>) -> Value {
    let mut e = json!({ "type": kind, "loc": [loc, field], "msg": msg, "input": input });
    if let Some(c) = ctx {
        e["ctx"] = c;
    }
    e
}
fn internal(e: impl std::fmt::Display) -> Response {
    eprintln!("error: {e}");
    detail(StatusCode::INTERNAL_SERVER_ERROR, "Something went wrong on this computer. Try again.")
}

/// A non-integer id is a 422 naming the path parameter, as in FastAPI (axum alone would say 400).
fn path_id(p: Result<Path<i64>, PathRejection>) -> Result<i64, Response> {
    p.map(|Path(id)| id).map_err(|_| {
        invalid(vec![field_error("path", "resource_id", "int_parsing", "Input should be a valid integer, unable to parse string as an integer".into(), &Value::Null, None)])
    })
}

/// The body must be a JSON object ({} is a valid empty update); [] or null is a 422.
fn not_object(body: &Value) -> Option<Response> {
    (!body.is_object()).then(|| {
        invalid(vec![json!({ "type": "model_attributes_type", "loc": ["body"], "msg": "Input should be a valid dictionary or object to extract fields from", "input": body })])
    })
}

/// An optional string: absent or null is fine; otherwise a string of at most `max` characters.
fn check_opt(body: &Value, field: &str, max: usize, errs: &mut Vec<Value>) -> Option<String> {
    match body.get(field) {
        None | Some(Value::Null) => None,
        Some(Value::String(s)) if s.chars().count() <= max => Some(s.clone()),
        Some(Value::String(s)) => {
            errs.push(field_error("body", field, "string_too_long", format!("String should have at most {max} characters"), &json!(s), Some(json!({ "max_length": max }))));
            None
        }
        Some(other) => {
            errs.push(field_error("body", field, "string_type", "Input should be a valid string".into(), other, None));
            None
        }
    }
}

/// Check one string field like the Pydantic schema: required?, min 1 if present, max length.
fn check_str(body: &Value, field: &str, required: bool, max: usize, errs: &mut Vec<Value>) -> Option<Option<String>> {
    match body.get(field) {
        None if required => {
            errs.push(field_error("body", field, "missing", "Field required".into(), &Value::Null, None));
            None
        }
        None => None,
        Some(Value::Null) if required || field == "title" => {
            errs.push(field_error("body", field, "string_type", "Input should be a valid string".into(), &Value::Null, None));
            None
        }
        Some(Value::Null) => Some(None),
        Some(Value::String(s)) => {
            let n = s.chars().count();
            if field == "title" && n < 1 {
                errs.push(field_error("body", field, "string_too_short", "String should have at least 1 character".into(), &json!(s), Some(json!({ "min_length": 1 }))));
                None
            } else if n > max {
                errs.push(field_error("body", field, "string_too_long", format!("String should have at most {max} characters"), &json!(s), Some(json!({ "max_length": max }))));
                None
            } else {
                Some(Some(s.clone()))
            }
        }
        Some(other) => {
            errs.push(field_error("body", field, "string_type", "Input should be a valid string".into(), other, None));
            None
        }
    }
}

fn check_url(body: &Value, required: bool, errs: &mut Vec<Value>) -> Option<String> {
    match body.get("url") {
        None if !required => None,
        Some(Value::String(s)) => match urls::parse_http_url(s) {
            Some(u) if u.len() <= 2083 => Some(u),
            _ => {
                errs.push(field_error("body", "url", "url_parsing", "Input should be a valid URL".into(), &json!(s), None));
                None
            }
        },
        Some(other) => {
            errs.push(field_error("body", "url", "url_type", "URL input should be a string or URL".into(), other, None));
            None
        }
        None => {
            errs.push(field_error("body", "url", "missing", "Field required".into(), &Value::Null, None));
            None
        }
    }
}

/// Fetch the preview after the response, as FastAPI's BackgroundTasks does.
fn preview_later(state: AppState, id: i64, url: String) {
    tokio::spawn(async move {
        if let Some(meta) = preview::fetch_metadata(&url).await {
            let s = state.lock().unwrap();
            let _ = s.set_metadata(id, &url, &meta);
        }
    });
}

// ── routes ──
#[derive(Deserialize)]
struct ListQuery {
    page: Option<String>,
    per_page: Option<String>,
    category: Option<String>,
    search: Option<String>,
}

async fn list(State(st): State<AppState>, Query(q): Query<ListQuery>) -> Response {
    let mut errs = vec![];
    let mut int = |name: &str, raw: &Option<String>, dflt: i64, lo: i64, hi: i64| -> i64 {
        let Some(s) = raw else { return dflt };
        match s.parse::<i64>() {
            Ok(v) if v < lo => { errs.push(field_error("query", name, "greater_than_equal", format!("Input should be greater than or equal to {lo}"), &json!(s), Some(json!({ "ge": lo })))); dflt }
            Ok(v) if v > hi => { errs.push(field_error("query", name, "less_than_equal", format!("Input should be less than or equal to {hi}"), &json!(s), Some(json!({ "le": hi })))); dflt }
            Ok(v) => v,
            Err(_) => { errs.push(field_error("query", name, "int_parsing", "Input should be a valid integer, unable to parse string as an integer".into(), &json!(s), None)); dflt }
        }
    };
    let page = int("page", &q.page, 1, 1, i64::MAX / 1000);
    let per_page = int("per_page", &q.per_page, 20, 1, 100);
    if !errs.is_empty() {
        return invalid(errs);
    }
    let s = st.lock().unwrap();
    match s.list(page, per_page, q.category.as_deref(), q.search.as_deref()) {
        Ok((resources, total)) => Json(json!({ "resources": resources, "total": total, "page": page, "per_page": per_page })).into_response(),
        Err(e) => internal(e),
    }
}

async fn categories(State(st): State<AppState>) -> Response {
    match st.lock().unwrap().categories() {
        Ok(c) => Json(c).into_response(),
        Err(e) => internal(e),
    }
}

async fn create(State(st): State<AppState>, body: Option<Json<Value>>) -> Response {
    let Some(Json(body)) = body else { return invalid(vec![field_error("body", "body", "json_invalid", "JSON decode error".into(), &Value::Null, None)]) };
    if let Some(r) = not_object(&body) { return r; }
    let mut errs = vec![];
    let title = check_str(&body, "title", true, 200, &mut errs);
    let url = check_url(&body, true, &mut errs);
    let description = check_str(&body, "description", false, 1000, &mut errs);
    let category = check_str(&body, "category", false, 100, &mut errs);
    if !errs.is_empty() {
        return invalid(errs);
    }
    let (title, url) = (title.flatten().unwrap_or_default(), url.unwrap_or_default());
    let res = st.lock().unwrap().create(&title, &url, description.flatten().as_deref(), category.flatten().as_deref());
    match res {
        Ok(Write::Ok(r)) => {
            preview_later(st.clone(), r["id"].as_i64().unwrap_or(0), url);
            (StatusCode::CREATED, Json(r)).into_response()
        }
        Ok(Write::Duplicate) => detail(StatusCode::CONFLICT, "A resource with this URL already exists"),
        Ok(Write::NotFound) => detail(StatusCode::NOT_FOUND, "Resource not found"),
        Err(e) => internal(e),
    }
}

async fn read_one(State(st): State<AppState>, p: Result<Path<i64>, PathRejection>) -> Response {
    let id = match path_id(p) { Ok(id) => id, Err(r) => return r };
    match st.lock().unwrap().get(id) {
        Ok(Some(r)) => Json(r).into_response(),
        Ok(None) => detail(StatusCode::NOT_FOUND, "Resource not found"),
        Err(e) => internal(e),
    }
}

async fn update(State(st): State<AppState>, p: Result<Path<i64>, PathRejection>, body: Option<Json<Value>>) -> Response {
    let id = match path_id(p) { Ok(id) => id, Err(r) => return r };
    let Some(Json(body)) = body else { return invalid(vec![field_error("body", "body", "json_invalid", "JSON decode error".into(), &Value::Null, None)]) };
    if let Some(r) = not_object(&body) { return r; }
    let mut errs = vec![];
    let title = check_str(&body, "title", false, 200, &mut errs).flatten();
    let url = check_url(&body, false, &mut errs);
    let description = check_str(&body, "description", false, 1000, &mut errs);
    let category = check_str(&body, "category", false, 100, &mut errs);
    if !errs.is_empty() {
        return invalid(errs);
    }
    let res = st.lock().unwrap().update(id, Fields { title, url, description, category });
    match res {
        Ok(Write::Ok(r)) => {
            if r["link_metadata"].is_null() {
                preview_later(st.clone(), id, r["url"].as_str().unwrap_or_default().to_string());
            }
            Json(r).into_response()
        }
        Ok(Write::Duplicate) => detail(StatusCode::CONFLICT, "A resource with this URL already exists"),
        Ok(Write::NotFound) => detail(StatusCode::NOT_FOUND, "Resource not found"),
        Err(e) => internal(e),
    }
}

async fn remove(State(st): State<AppState>, p: Result<Path<i64>, PathRejection>) -> Response {
    let id = match path_id(p) { Ok(id) => id, Err(r) => return r };
    match st.lock().unwrap().delete(id) {
        Ok(true) => Json(json!({ "message": "Resource deleted successfully" })).into_response(),
        Ok(false) => detail(StatusCode::NOT_FOUND, "Resource not found"),
        Err(e) => internal(e),
    }
}

async fn refresh_metadata(State(st): State<AppState>, p: Result<Path<i64>, PathRejection>) -> Response {
    let id = match path_id(p) { Ok(id) => id, Err(r) => return r };
    let url = match st.lock().unwrap().get(id) {
        Ok(Some(r)) => r["url"].as_str().unwrap_or_default().to_string(),
        Ok(None) => return detail(StatusCode::NOT_FOUND, "Resource not found"),
        Err(e) => return internal(e),
    };
    if let Some(meta) = preview::fetch_metadata(&url).await {
        let _ = st.lock().unwrap().set_metadata(id, &url, &meta);
    }
    read_one(State(st), Ok(Path(id))).await
}

fn clip(text: Option<&str>, limit: usize) -> Option<String> {
    let t = text.unwrap_or_default().split_whitespace().collect::<Vec<_>>().join(" ");
    if t.is_empty() {
        return None;
    }
    if t.chars().count() > limit {
        Some(t.chars().take(limit - 1).collect::<String>() + "…")
    } else {
        Some(t)
    }
}

/// POST /api/save: the browser extension's one-click save. Never refuses a long or
/// repeated page: normalizes the URL, returns an existing link (200) or creates one (201).
async fn save(State(st): State<AppState>, body: Option<Json<Value>>) -> Response {
    let Some(Json(body)) = body else { return invalid(vec![field_error("body", "body", "json_invalid", "JSON decode error".into(), &Value::Null, None)]) };
    if let Some(r) = not_object(&body) { return r; }
    // Types and limits as SaveRequest; long titles and notes inside the limits are clipped below.
    let mut errs = vec![];
    let raw = match body.get("url") {
        None => { errs.push(field_error("body", "url", "missing", "Field required".into(), &Value::Null, None)); None }
        Some(Value::Null) => { errs.push(field_error("body", "url", "string_type", "Input should be a valid string".into(), &Value::Null, None)); None }
        _ => check_opt(&body, "url", 4000, &mut errs),
    };
    let title = check_opt(&body, "title", 4000, &mut errs);
    let note = check_opt(&body, "note", 10000, &mut errs);
    let category = check_opt(&body, "category", 100, &mut errs);
    if !errs.is_empty() {
        return invalid(errs);
    }
    let raw = raw.unwrap_or_default();
    let url = match urls::normalize_url(&raw) {
        Ok(u) => u,
        Err(msg) => return detail(StatusCode::UNPROCESSABLE_ENTITY, &msg),
    };
    if url.chars().count() > 500 {
        return detail(StatusCode::UNPROCESSABLE_ENTITY, "This address is longer than 500 characters and can't be saved.");
    }
    let store = st.lock().unwrap();
    match store.get_by_url(&url) {
        Ok(Some(r)) => return (StatusCode::OK, Json(json!({ "resource": r, "created": false }))).into_response(),
        Ok(None) => {}
        Err(e) => return internal(e),
    }
    let title = clip(title.as_deref(), 200).or_else(|| clip(Some(&urls::fallback_title(&url)), 200)).unwrap_or_default();
    match store.create(&title, &url, clip(note.as_deref(), 1000).as_deref(), clip(category.as_deref(), 100).as_deref()) {
        Ok(Write::Ok(r)) => {
            drop(store);
            preview_later(st.clone(), r["id"].as_i64().unwrap_or(0), url);
            (StatusCode::CREATED, Json(json!({ "resource": r, "created": true }))).into_response()
        }
        Ok(_) => match store.get_by_url(&url) {
            Ok(Some(r)) => (StatusCode::OK, Json(json!({ "resource": r, "created": false }))).into_response(),
            _ => internal("save raced"),
        },
        Err(e) => internal(e),
    }
}

async fn export(State(st): State<AppState>) -> Response {
    match st.lock().unwrap().export() {
        Ok(rows) => ([(header::CONTENT_DISPOSITION, "attachment; filename=\"savemylinks-export.json\"")], Json(rows)).into_response(),
        Err(e) => internal(e),
    }
}

async fn health() -> Json<Value> {
    Json(json!({ "status": "healthy", "service": "SaveMyLinks" }))
}

/// The pages and their files, embedded in the program. "/" is the library, "/add" the save page.
async fn static_file(uri: Uri) -> Response {
    let path = uri.path().trim_start_matches('/');
    let path = match path {
        "" => "index.html",
        "add" => "add.html",
        p => p,
    };
    match Site::get(path) {
        Some(f) => {
            let mime = mime_guess::from_path(path).first_or_octet_stream();
            ([(header::CONTENT_TYPE, mime.as_ref().to_string())], Body::from(f.data.into_owned())).into_response()
        }
        None => detail(StatusCode::NOT_FOUND, "Not Found"),
    }
}

pub fn app(store: Store) -> Router {
    let state: AppState = Arc::new(Mutex::new(store));
    Router::new()
        .route("/api/resources", get(list).post(create))
        .route("/api/resources/", get(list).post(create))
        .route("/api/resources/categories", get(categories))
        .route("/api/resources/:id", get(read_one).put(update).delete(remove))
        .route("/api/resources/:id/metadata", post(refresh_metadata))
        .route("/api/save", post(save))
        .route("/api/export", get(export))
        .route("/health", get(health))
        .fallback(static_file)
        .with_state(state)
}

fn default_db() -> String {
    let base = std::env::var("APPDATA")
        .map(|d| std::path::PathBuf::from(d).join("SaveMyLinks"))
        .or_else(|_| std::env::var("HOME").map(|h| std::path::PathBuf::from(h).join(".local/share/savemylinks")))
        .unwrap_or_else(|_| std::path::PathBuf::from("."));
    let _ = std::fs::create_dir_all(&base);
    base.join("savemylinks.db").to_string_lossy().into_owned()
}

fn arg(name: &str) -> Option<String> {
    let a: Vec<String> = std::env::args().collect();
    a.iter().position(|x| x == name).and_then(|i| a.get(i + 1).cloned())
}

#[tokio::main]
async fn main() {
    let port: u16 = arg("--port").or_else(|| std::env::var("SAVEMYLINKS_PORT").ok()).and_then(|p| p.parse().ok()).unwrap_or(8000);
    let db_path = arg("--db").or_else(|| std::env::var("SAVEMYLINKS_DB").ok()).unwrap_or_else(default_db);
    let no_browser = std::env::args().any(|a| a == "--no-browser") || std::env::var("SAVEMYLINKS_NO_BROWSER").is_ok();
    let store = Store::open(&db_path).unwrap_or_else(|e| {
        eprintln!("Can't open the library at {db_path}: {e}");
        std::process::exit(1);
    });
    let listener = tokio::net::TcpListener::bind(("127.0.0.1", port)).await.unwrap_or_else(|e| {
        eprintln!("Port {port} is busy ({e}). Is SaveMyLinks already running? Try --port 8123.");
        std::process::exit(1);
    });
    let addr = format!("http://127.0.0.1:{port}/");
    println!("SaveMyLinks is running at {addr}\nYour library: {db_path}\nClose this window (or press Ctrl+C) to stop.");
    if !no_browser {
        let _ = webbrowser::open(&addr);
    }
    axum::serve(listener, app(store))
        .with_graceful_shutdown(async { let _ = tokio::signal::ctrl_c().await; })
        .await
        .unwrap();
}
