-- 0003 · 分类独立词表；资源单选一类
CREATE TABLE IF NOT EXISTS categories (
  id   INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

ALTER TABLE resources ADD COLUMN category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_resources_category ON resources(category_id);
