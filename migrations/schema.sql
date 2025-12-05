PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS roles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  description TEXT
);
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role_id INTEGER,
  FOREIGN KEY(role_id) REFERENCES roles(id)
);
CREATE TABLE IF NOT EXISTS settings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  app_name TEXT,
  logo_path TEXT
);
CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT,
  body TEXT,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS crawl_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  keyword TEXT,
  title TEXT,
  summary TEXT,
  cover TEXT,
  original_url TEXT,
  source TEXT,
  created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_crawl_records_url ON crawl_records(original_url);
CREATE TABLE IF NOT EXISTS crawl_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  keyword TEXT,
  title TEXT,
  summary TEXT,
  cover TEXT,
  original_url TEXT,
  source TEXT,
  deep_crawled INTEGER DEFAULT 0,
  deep_content TEXT,
  detail_json TEXT,
  created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_crawl_items_url ON crawl_items(original_url);
