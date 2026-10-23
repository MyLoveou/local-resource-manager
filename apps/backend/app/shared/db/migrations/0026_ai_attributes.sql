-- 0026: structured image attributes for AI retrieval (person count, orientation).

CREATE TABLE ai_attributes (
  resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  feature     TEXT NOT NULL,
  value_json  TEXT NOT NULL,
  value_num   REAL,
  value_text  TEXT,
  confidence  REAL,
  model       TEXT,
  updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY(resource_id, feature)
);

CREATE INDEX idx_ai_attributes_feature_num
  ON ai_attributes(feature, value_num);

CREATE INDEX idx_ai_attributes_feature_text
  ON ai_attributes(feature, value_text);
