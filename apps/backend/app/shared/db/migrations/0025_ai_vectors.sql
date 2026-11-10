-- 0025: local AI image embeddings (Chinese-CLIP).

CREATE TABLE ai_vectors (
  resource_id INTEGER PRIMARY KEY REFERENCES resources(id) ON DELETE CASCADE,
  model_id    TEXT NOT NULL,
  dim         INTEGER NOT NULL,
  vector      BLOB NOT NULL,
  source_path TEXT,
  updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_ai_vectors_model ON ai_vectors(model_id);
