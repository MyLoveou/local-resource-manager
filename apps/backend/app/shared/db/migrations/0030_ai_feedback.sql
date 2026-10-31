-- 0030: search feedback for thresholding and lightweight learning-to-rank samples.

CREATE TABLE ai_search_feedback (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  query         TEXT NOT NULL,
  resource_id   INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  action        TEXT NOT NULL,
  source        TEXT NOT NULL DEFAULT 'search',
  score         REAL,
  position      INTEGER,
  features_json TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_ai_search_feedback_query
  ON ai_search_feedback(query, resource_id);

CREATE INDEX idx_ai_search_feedback_created
  ON ai_search_feedback(created_at);
