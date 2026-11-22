//! The library: one SQLite file, the same "resources" table as the Python app.
use rusqlite::{params, Connection, OptionalExtension, Row};
use serde_json::{json, Map, Value};

pub struct Store {
    conn: Connection,
}

#[derive(Default)]
pub struct Fields {
    pub title: Option<String>,
    pub url: Option<String>,
    pub description: Option<Option<String>>,
    pub category: Option<Option<String>>,
}

pub enum Write {
    Ok(Value),
    Duplicate,
    NotFound,
}

fn now() -> String {
    chrono::Utc::now().format("%Y-%m-%dT%H:%M:%S%.6f").to_string()
}

fn to_json(r: &Row) -> rusqlite::Result<Value> {
    let meta: Option<String> = r.get("link_metadata")?;
    Ok(json!({
        "id": r.get::<_, i64>("id")?,
        "title": r.get::<_, String>("title")?,
        "url": r.get::<_, String>("url")?,
        "description": r.get::<_, Option<String>>("description")?,
        "category": r.get::<_, Option<String>>("category")?,
        "link_metadata": meta.and_then(|m| serde_json::from_str::<Value>(&m).ok()),
        "created_at": r.get::<_, String>("created_at")?,
        "updated_at": r.get::<_, String>("updated_at")?,
    }))
}

const COLS: &str = "id, title, url, description, category, link_metadata, created_at, updated_at";

impl Store {
    pub fn open(path: &str) -> rusqlite::Result<Store> {
        let conn = Connection::open(path)?;
        conn.execute_batch(
            "PRAGMA journal_mode=WAL;
             CREATE TABLE IF NOT EXISTS resources (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               title VARCHAR(200) NOT NULL,
               url VARCHAR(500) NOT NULL UNIQUE,
               description TEXT,
               category VARCHAR(100),
               link_metadata JSON,
               created_at DATETIME NOT NULL,
               updated_at DATETIME NOT NULL);
             CREATE INDEX IF NOT EXISTS ix_resources_title ON resources (title);
             CREATE INDEX IF NOT EXISTS ix_resources_category ON resources (category);",
        )?;
        Ok(Store { conn })
    }

    pub fn get(&self, id: i64) -> rusqlite::Result<Option<Value>> {
        self.conn.query_row(&format!("SELECT {COLS} FROM resources WHERE id = ?1"), [id], to_json).optional()
    }

    pub fn get_by_url(&self, url: &str) -> rusqlite::Result<Option<Value>> {
        self.conn.query_row(&format!("SELECT {COLS} FROM resources WHERE url = ?1"), [url], to_json).optional()
    }

    /// Newest first; search is case-insensitive in title and description; category is exact.
    pub fn list(&self, page: i64, per_page: i64, category: Option<&str>, search: Option<&str>) -> rusqlite::Result<(Vec<Value>, i64)> {
        let mut filter = String::from("WHERE 1=1");
        let mut args: Vec<String> = vec![];
        if let Some(c) = category.filter(|c| !c.is_empty()) {
            args.push(c.to_string());
            filter += &format!(" AND category = ?{}", args.len());
        }
        if let Some(s) = search.filter(|s| !s.is_empty()) {
            args.push(format!("%{s}%"));
            filter += &format!(" AND (title LIKE ?{n} OR description LIKE ?{n})", n = args.len());
        }
        let total: i64 = self.conn.query_row(&format!("SELECT count(id) FROM resources {filter}"), rusqlite::params_from_iter(args.iter()), |r| r.get(0))?;
        let sql = format!("SELECT {COLS} FROM resources {filter} ORDER BY created_at DESC, id DESC LIMIT {per_page} OFFSET {}", (page - 1) * per_page);
        let mut stmt = self.conn.prepare(&sql)?;
        let rows = stmt.query_map(rusqlite::params_from_iter(args.iter()), to_json)?.collect::<rusqlite::Result<Vec<_>>>()?;
        Ok((rows, total))
    }

    pub fn categories(&self) -> rusqlite::Result<Vec<String>> {
        let mut stmt = self.conn.prepare("SELECT DISTINCT category FROM resources WHERE category IS NOT NULL ORDER BY category")?;
        let v = stmt.query_map([], |r| r.get(0))?.collect();
        v
    }

    pub fn create(&self, title: &str, url: &str, description: Option<&str>, category: Option<&str>) -> rusqlite::Result<Write> {
        if self.get_by_url(url)?.is_some() {
            return Ok(Write::Duplicate);
        }
        let t = now();
        self.conn.execute(
            "INSERT INTO resources (title, url, description, category, created_at, updated_at) VALUES (?1, ?2, ?3, ?4, ?5, ?5)",
            params![title, url, description, category, t],
        )?;
        Ok(Write::Ok(self.get(self.conn.last_insert_rowid())?.unwrap_or(Value::Null)))
    }

    /// A changed URL clears the old preview (it described another page).
    pub fn update(&self, id: i64, f: Fields) -> rusqlite::Result<Write> {
        let Some(cur) = self.get(id)? else { return Ok(Write::NotFound) };
        if let Some(u) = &f.url {
            if let Some(other) = self.get_by_url(u)? {
                if other["id"].as_i64() != Some(id) {
                    return Ok(Write::Duplicate);
                }
            }
        }
        let url_changed = f.url.as_deref().is_some_and(|u| cur["url"].as_str() != Some(u));
        let title = f.title.unwrap_or_else(|| cur["title"].as_str().unwrap_or_default().to_string());
        let url = f.url.unwrap_or_else(|| cur["url"].as_str().unwrap_or_default().to_string());
        let description = f.description.unwrap_or_else(|| cur["description"].as_str().map(String::from));
        let category = f.category.unwrap_or_else(|| cur["category"].as_str().map(String::from));
        let meta: Option<String> = if url_changed { None } else { cur.get("link_metadata").filter(|m| !m.is_null()).map(|m| m.to_string()) };
        self.conn.execute(
            "UPDATE resources SET title=?1, url=?2, description=?3, category=?4, link_metadata=?5, updated_at=?6 WHERE id=?7",
            params![title, url, description, category, meta, now(), id],
        )?;
        Ok(Write::Ok(self.get(id)?.unwrap_or(Value::Null)))
    }

    pub fn delete(&self, id: i64) -> rusqlite::Result<bool> {
        Ok(self.conn.execute("DELETE FROM resources WHERE id = ?1", [id])? > 0)
    }

    /// Store a preview only if the resource still has that URL (not deleted or edited meanwhile).
    pub fn set_metadata(&self, id: i64, url: &str, meta: &Map<String, Value>) -> rusqlite::Result<()> {
        self.conn.execute(
            "UPDATE resources SET link_metadata = ?1 WHERE id = ?2 AND url = ?3",
            params![Value::Object(meta.clone()).to_string(), id, url],
        )?;
        Ok(())
    }

    pub fn export(&self) -> rusqlite::Result<Vec<Value>> {
        let mut stmt = self.conn.prepare(&format!("SELECT {COLS} FROM resources ORDER BY id"))?;
        let v = stmt.query_map([], to_json)?.collect();
        v
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn create_list_update_delete() {
        let s = Store::open(":memory:").unwrap();
        assert!(matches!(s.create("A", "https://a.com/", Some("note"), Some("Web")).unwrap(), Write::Ok(_)));
        assert!(matches!(s.create("dup", "https://a.com/", None, None).unwrap(), Write::Duplicate));
        s.create("B", "https://b.com/", None, Some("Python")).unwrap();
        let (rows, total) = s.list(1, 10, None, Some("NOTE")).unwrap();
        assert_eq!((rows.len(), total), (1, 1), "search is case-insensitive");
        assert_eq!(s.categories().unwrap(), vec!["Python", "Web"]);
        let mut m = Map::new();
        m.insert("title".into(), Value::String("t".into()));
        s.set_metadata(1, "https://a.com/", &m).unwrap();
        assert!(s.get(1).unwrap().unwrap()["link_metadata"].is_object());
        let f = Fields { url: Some("https://c.com/".into()), ..Default::default() };
        let Write::Ok(r) = s.update(1, f).unwrap() else { panic!() };
        assert!(r["link_metadata"].is_null(), "a new URL clears the preview");
        assert!(matches!(s.update(1, Fields { url: Some("https://b.com/".into()), ..Default::default() }).unwrap(), Write::Duplicate));
        assert!(s.delete(1).unwrap());
        assert!(!s.delete(1).unwrap());
    }
}
