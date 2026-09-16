-- 0008 · 作品级番剧/AV：放宽 resources.type CHECK；季/集/特典表
-- SQLite 不能改 CHECK，重建 resources。列序对齐 0001 + 0003 category_id + 0004 author。

PRAGMA foreign_keys=OFF;

CREATE TABLE resources_new (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  type          TEXT NOT NULL CHECK (type IN ('image','video','anime','av')),
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
  author        TEXT
);

INSERT INTO resources_new (
  id, type, title, description, rating, cover_path, status, deleted_at,
  last_scraped_at, scraped_source, extra, created_at, updated_at, category_id, author
)
SELECT
  id, type, title, description, rating, cover_path, status, deleted_at,
  last_scraped_at, scraped_source, extra, created_at, updated_at, category_id, author
FROM resources;

DROP TABLE resources;
ALTER TABLE resources_new RENAME TO resources;

CREATE INDEX idx_resources_type   ON resources(type);
CREATE INDEX idx_resources_status ON resources(status);
CREATE INDEX IF NOT EXISTS idx_resources_category ON resources(category_id);
CREATE INDEX IF NOT EXISTS idx_resources_status_type_created_id
  ON resources(status, type, created_at, id);

CREATE TABLE seasons (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  resource_id   INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  season_number INTEGER NOT NULL,
  title         TEXT,
  sort_index    INTEGER NOT NULL DEFAULT 0,
  UNIQUE (resource_id, season_number)
);
CREATE INDEX idx_seasons_resource ON seasons(resource_id);

CREATE TABLE episodes (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  season_id       INTEGER NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
  file_id         INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
  episode_number  INTEGER NOT NULL,
  title           TEXT,
  sort_index      INTEGER NOT NULL DEFAULT 0,
  status          TEXT NOT NULL DEFAULT 'active'
                  CHECK (status IN ('active','trashed')),
  UNIQUE (season_id, episode_number)
);
CREATE INDEX idx_episodes_season ON episodes(season_id);

CREATE TABLE extras (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  file_id     INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
  title       TEXT NOT NULL DEFAULT '',
  sort_index  INTEGER NOT NULL DEFAULT 0,
  status      TEXT NOT NULL DEFAULT 'active'
              CHECK (status IN ('active','trashed'))
);
CREATE INDEX idx_extras_resource ON extras(resource_id);

PRAGMA foreign_keys=ON;
