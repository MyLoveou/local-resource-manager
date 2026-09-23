-- 0014 · 工作目录类型 + 消费记录
-- SQLite 不能改 CHECK，重建 resources。列对齐 0011（含 synopsis、storage_kind）。

PRAGMA foreign_keys=OFF;

CREATE TABLE resources_new (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  type          TEXT NOT NULL CHECK (type IN (
                  'image','video','anime','av','audio','novel','game','model','comic','work_directory'
                )),
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
  updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
  category_id   INTEGER REFERENCES categories(id) ON DELETE SET NULL,
  author        TEXT,
  storage_kind  TEXT NOT NULL DEFAULT 'owned'
                CHECK (storage_kind IN ('owned','indexed')),
  synopsis      TEXT
);

INSERT INTO resources_new (
  id, type, title, description, rating, cover_path, status, deleted_at,
  last_scraped_at, scraped_source, extra, created_at, updated_at, category_id, author,
  storage_kind, synopsis
)
SELECT
  id, type, title, description, rating, cover_path, status, deleted_at,
  last_scraped_at, scraped_source, extra, created_at, updated_at, category_id, author,
  storage_kind, synopsis
FROM resources;

DROP TABLE resources;
ALTER TABLE resources_new RENAME TO resources;

CREATE INDEX idx_resources_type ON resources(type);
CREATE INDEX idx_resources_status ON resources(status);
CREATE INDEX IF NOT EXISTS idx_resources_category ON resources(category_id);
CREATE INDEX IF NOT EXISTS idx_resources_status_type_created_id
  ON resources(status, type, created_at, id);

CREATE TABLE IF NOT EXISTS consumption_events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  action      TEXT NOT NULL,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_consumption_created ON consumption_events(created_at);

PRAGMA foreign_keys=ON;
