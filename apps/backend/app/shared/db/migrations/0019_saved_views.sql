-- 0019 · 保存的时间线筛选器（无成员表）
CREATE TABLE saved_views (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  kind        TEXT NOT NULL,
  type        TEXT NOT NULL,
  name        TEXT NOT NULL,
  filters_json TEXT NOT NULL DEFAULT '{}',
  sort        TEXT NOT NULL DEFAULT 'takenAt',
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX idx_saved_views_kind_type_name
  ON saved_views(kind, type, name);
CREATE INDEX idx_saved_views_kind_type
  ON saved_views(kind, type);
