-- 0001 · 初始 schema（对齐 docs/design/02-数据模型.md）
-- 表结构：resources / files / tags / resource_tags / scrape_jobs / candidates / download_tasks / settings / adapters

CREATE TABLE resources (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  type          TEXT NOT NULL CHECK (type IN ('image','video')),
  title         TEXT NOT NULL DEFAULT '',
  description   TEXT,
  rating        REAL CHECK (rating BETWEEN 0 AND 10),
  cover_path    TEXT,
  status        TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active','trashed','lost')),
  deleted_at    TEXT,
  last_scraped_at TEXT,
  scraped_source TEXT,
  extra         TEXT NOT NULL DEFAULT '{}',
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_resources_type   ON resources(type);
CREATE INDEX idx_resources_status ON resources(status);

CREATE TABLE files (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  path        TEXT NOT NULL,
  sha256      TEXT,
  size        INTEGER,
  format      TEXT,
  duration    REAL,
  width       INTEGER,
  height      INTEGER,
  codec       TEXT,
  exif_taken_at TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (path),
  UNIQUE (sha256)
);
CREATE INDEX idx_files_resource ON files(resource_id);

CREATE TABLE tags (
  id   INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE resource_tags (
  resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  tag_id      INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  PRIMARY KEY (resource_id, tag_id)
);

CREATE TABLE scrape_jobs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  status      TEXT NOT NULL DEFAULT 'queued'
              CHECK (status IN ('queued','running','done','failed')),
  started_at  TEXT,
  finished_at TEXT,
  error       TEXT,
  match_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE candidates (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id        INTEGER NOT NULL REFERENCES scrape_jobs(id) ON DELETE CASCADE,
  title         TEXT NOT NULL,
  url           TEXT NOT NULL,
  thumbnail_url TEXT,
  source        TEXT NOT NULL,
  relevance     REAL,
  selected      INTEGER NOT NULL DEFAULT 0,
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE download_tasks (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  url               TEXT NOT NULL,
  protocol          TEXT NOT NULL,
  engine            TEXT NOT NULL,
  status            TEXT NOT NULL DEFAULT 'queued'
                    CHECK (status IN ('queued','running','paused','done','failed')),
  save_path         TEXT,
  downloaded_bytes  INTEGER NOT NULL DEFAULT 0,
  total_bytes       INTEGER,
  speed             INTEGER NOT NULL DEFAULT 0,
  error             TEXT,
  target_resource_id INTEGER REFERENCES resources(id) ON DELETE SET NULL,
  created_at        TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_tasks_status ON download_tasks(status);

CREATE TABLE settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE adapters (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  key     TEXT NOT NULL UNIQUE,
  enabled INTEGER NOT NULL DEFAULT 1,
  config  TEXT NOT NULL DEFAULT '{}'
);
