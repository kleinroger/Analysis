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
CREATE TABLE IF NOT EXISTS crawl_rules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  site TEXT NOT NULL,
  domain TEXT,
  title_xpath TEXT,
  content_xpath TEXT,
  headers TEXT,
  created_at TEXT,
  updated_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_crawl_rules_site ON crawl_rules(site);
CREATE TABLE IF NOT EXISTS ai_engines (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider TEXT NOT NULL,
  api_url TEXT NOT NULL,
  api_key TEXT,
  model_name TEXT NOT NULL,
  description TEXT,
  created_at TEXT,
  updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_ai_engines_provider ON ai_engines(provider);
CREATE TABLE IF NOT EXISTS ai_assistants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  engine_id INTEGER NOT NULL,
  system_prompt TEXT,
  created_at TEXT,
  updated_at TEXT,
  FOREIGN KEY(engine_id) REFERENCES ai_engines(id)
);
CREATE INDEX IF NOT EXISTS idx_ai_assistants_engine ON ai_assistants(engine_id);
CREATE TABLE IF NOT EXISTS ai_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  assistant_id INTEGER NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT,
  FOREIGN KEY(assistant_id) REFERENCES ai_assistants(id)
);
CREATE INDEX IF NOT EXISTS idx_ai_messages_asst ON ai_messages(assistant_id);
