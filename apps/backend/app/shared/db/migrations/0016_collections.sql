-- 0016 · 合集：collections / collection_items
-- 合集是"分组"，不是资源；成员是已有 resources.id 引用（可多对多、可跨类型、手动排序）

CREATE TABLE collections (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT NOT NULL CHECK (length(trim(title)) >= 1),
  description TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE collection_items (
  collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
  resource_id   INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  position      INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (collection_id, resource_id)
);
CREATE INDEX idx_collection_items_resource ON collection_items(resource_id);
