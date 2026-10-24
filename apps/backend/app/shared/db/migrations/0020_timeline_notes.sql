-- 0020: timeline notes (global date notes + saved-view notes) and optional place name.
CREATE TABLE timeline_notes (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  scope         TEXT NOT NULL CHECK (scope IN ('date', 'saved_view')),
  date          TEXT,
  saved_view_id INTEGER REFERENCES saved_views(id) ON DELETE CASCADE,
  title         TEXT NOT NULL DEFAULT '',
  body          TEXT,
  location_name TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
  CHECK (
    (scope = 'date' AND date IS NOT NULL AND saved_view_id IS NULL) OR
    (scope = 'saved_view' AND date IS NULL AND saved_view_id IS NOT NULL)
  ),
  CHECK (date IS NULL OR length(date) = 10)
);

CREATE UNIQUE INDEX idx_timeline_notes_date
  ON timeline_notes(date) WHERE scope = 'date';
CREATE UNIQUE INDEX idx_timeline_notes_saved_view
  ON timeline_notes(saved_view_id) WHERE scope = 'saved_view';
