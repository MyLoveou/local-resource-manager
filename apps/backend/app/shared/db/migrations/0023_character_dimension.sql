-- 0023: character and work dimension for cosplay/library resources.

CREATE TABLE works (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT NOT NULL UNIQUE,
  description TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE characters (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  name              TEXT NOT NULL,
  work_id           INTEGER REFERENCES works(id) ON DELETE SET NULL,
  description       TEXT,
  cover_resource_id INTEGER REFERENCES resources(id) ON DELETE SET NULL,
  created_at        TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_characters_work ON characters(work_id);
CREATE INDEX idx_characters_name ON characters(name);

CREATE TABLE character_aliases (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
  alias        TEXT NOT NULL,
  UNIQUE(character_id, alias)
);

CREATE INDEX idx_character_aliases_character ON character_aliases(character_id);

CREATE TABLE resource_characters (
  resource_id  INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
  PRIMARY KEY(resource_id, character_id)
);

CREATE INDEX idx_resource_characters_character ON resource_characters(character_id);
