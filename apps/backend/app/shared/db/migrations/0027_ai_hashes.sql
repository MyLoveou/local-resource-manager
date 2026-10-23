-- 0027: perceptual hashes for near-duplicate image search.

CREATE TABLE ai_hashes (
  resource_id INTEGER PRIMARY KEY REFERENCES resources(id) ON DELETE CASCADE,
  dhash       TEXT NOT NULL,
  updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
