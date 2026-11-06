-- 0032 · 智能导入：源名称 + 建议

-- 采纳改名后仍需可查原始名称（D-20261025-02 · Q1）
ALTER TABLE resources ADD COLUMN source_name TEXT;

CREATE TABLE IF NOT EXISTS import_suggestions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  job_id      TEXT,
  field       TEXT NOT NULL
              CHECK (field IN ('title','category','season','episode','aiAnalysis')),
  value       TEXT,
  confidence  REAL NOT NULL DEFAULT 0,
  source      TEXT NOT NULL
              CHECK (source IN ('rule','scrape','ai','history')),
  reason      TEXT NOT NULL DEFAULT '',
  status      TEXT NOT NULL DEFAULT 'pending'
              CHECK (status IN ('pending','accepted','rejected')),
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  decided_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_suggestions_job
  ON import_suggestions(job_id, status);
CREATE INDEX IF NOT EXISTS idx_suggestions_resource
  ON import_suggestions(resource_id, status);
