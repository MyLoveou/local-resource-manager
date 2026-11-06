-- 0018: per-type category tree, multi-category resources, legacy migration.
-- Keep resources.category_id for one rollback release; new code uses resource_categories only.
PRAGMA foreign_keys=OFF;

CREATE TABLE categories_new (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  type      TEXT NOT NULL,
  parent_id INTEGER REFERENCES categories_new(id) ON DELETE SET NULL,
  name      TEXT NOT NULL,
  sort      INTEGER NOT NULL DEFAULT 0,
  is_system INTEGER NOT NULL DEFAULT 0
);

CREATE TEMP TABLE old_category_types AS
SELECT c.id AS old_id, r.type AS type
FROM categories c
JOIN resources r ON r.category_id = c.id
GROUP BY c.id, r.type
UNION ALL
SELECT c.id, 'image'
FROM categories c
WHERE NOT EXISTS (SELECT 1 FROM resources r2 WHERE r2.category_id = c.id);

CREATE TEMP TABLE category_pairs AS
SELECT old_id, type,
       ROW_NUMBER() OVER (PARTITION BY old_id ORDER BY type) AS rn
FROM old_category_types;

CREATE TEMP TABLE category_pair_ids AS
SELECT p.old_id, p.type,
       CASE
         WHEN p.rn = 1 THEN p.old_id
         ELSE (SELECT COALESCE(MAX(id), 0) FROM categories)
              + ROW_NUMBER() OVER (ORDER BY p.old_id, p.type)
       END AS new_id
FROM category_pairs p;

INSERT INTO categories_new (id, type, parent_id, name, sort, is_system)
SELECT pi.new_id, pi.type, NULL, c.name, 0, 0
FROM category_pair_ids pi
JOIN categories c ON c.id = pi.old_id;

CREATE TEMP TABLE orphan_category_ids AS
SELECT pi.new_id
FROM category_pair_ids pi
WHERE pi.type = 'image'
  AND NOT EXISTS (SELECT 1 FROM resources r WHERE r.category_id = pi.old_id);

INSERT INTO categories_new (id, type, parent_id, name, sort, is_system)
SELECT (SELECT COALESCE(MAX(new_id), 0) FROM category_pair_ids) + 1,
       'image', NULL, '待整理分类', 0, 1
WHERE EXISTS (SELECT 1 FROM orphan_category_ids);

UPDATE categories_new
SET parent_id = (
  SELECT id FROM categories_new
  WHERE type = 'image' AND is_system = 1 AND name = '待整理分类'
  LIMIT 1
)
WHERE id IN (SELECT new_id FROM orphan_category_ids);

DROP TABLE categories;
ALTER TABLE categories_new RENAME TO categories;

CREATE TABLE resource_categories (
  resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
  PRIMARY KEY (resource_id, category_id)
);

INSERT OR IGNORE INTO resource_categories (resource_id, category_id)
SELECT r.id, pi.new_id
FROM resources r
JOIN category_pair_ids pi
  ON pi.old_id = r.category_id AND pi.type = r.type
WHERE r.category_id IS NOT NULL;

UPDATE resources
SET category_id = (
  SELECT pi.new_id FROM category_pair_ids pi
  WHERE pi.old_id = resources.category_id AND pi.type = resources.type
  LIMIT 1
)
WHERE category_id IS NOT NULL;

CREATE UNIQUE INDEX idx_categories_type_root_name
  ON categories(type, name) WHERE parent_id IS NULL;
CREATE UNIQUE INDEX idx_categories_type_parent_name
  ON categories(type, parent_id, name) WHERE parent_id IS NOT NULL;
CREATE INDEX idx_categories_type_parent ON categories(type, parent_id);
CREATE INDEX idx_resource_categories_category
  ON resource_categories(category_id, resource_id);
CREATE INDEX idx_resource_categories_resource
  ON resource_categories(resource_id);

DROP TABLE old_category_types;
DROP TABLE category_pairs;
DROP TABLE category_pair_ids;
DROP TABLE orphan_category_ids;

PRAGMA foreign_keys=ON;
