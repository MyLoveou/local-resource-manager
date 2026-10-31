-- 0028: VLM-generated image documents and normalized tags.

CREATE TABLE ai_documents (
  resource_id     INTEGER PRIMARY KEY REFERENCES resources(id) ON DELETE CASCADE,
  caption         TEXT NOT NULL DEFAULT '',
  short_caption   TEXT NOT NULL DEFAULT '',
  tags_json       TEXT NOT NULL DEFAULT '[]',
  attributes_json TEXT NOT NULL DEFAULT '{}',
  ocr_text        TEXT NOT NULL DEFAULT '',
  model_id        TEXT,
  prompt_version  TEXT,
  status          TEXT NOT NULL DEFAULT 'ready',
  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_ai_documents_model ON ai_documents(model_id);

CREATE TABLE ai_tags (
  resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  tag         TEXT NOT NULL,
  category    TEXT,
  confidence  REAL,
  source      TEXT NOT NULL DEFAULT 'vlm',
  model_id    TEXT,
  PRIMARY KEY(resource_id, tag)
);

CREATE INDEX idx_ai_tags_tag ON ai_tags(tag);
