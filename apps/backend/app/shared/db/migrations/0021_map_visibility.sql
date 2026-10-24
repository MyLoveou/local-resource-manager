-- 0021: independent map visibility for media resources.
-- map_visible: NULL=auto include when GPS exists; 1=force include; 0=force exclude.

ALTER TABLE resources ADD COLUMN map_visible INTEGER;

CREATE INDEX idx_resources_map_visible ON resources(map_visible);
