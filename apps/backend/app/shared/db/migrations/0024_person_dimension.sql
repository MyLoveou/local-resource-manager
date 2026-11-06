-- 0024: cosplayer/person dimension with aliases and resource links.

CREATE TABLE persons (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  name              TEXT NOT NULL,
  description       TEXT,
  cover_resource_id INTEGER REFERENCES resources(id) ON DELETE SET NULL,
  created_at        TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_persons_name ON persons(name);

CREATE TABLE person_aliases (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  person_id INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
  alias     TEXT NOT NULL,
  UNIQUE(person_id, alias)
);

CREATE INDEX idx_person_aliases_person ON person_aliases(person_id);

CREATE TABLE resource_persons (
  resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  person_id   INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
  PRIMARY KEY(resource_id, person_id)
);

CREATE INDEX idx_resource_persons_person ON resource_persons(person_id);
