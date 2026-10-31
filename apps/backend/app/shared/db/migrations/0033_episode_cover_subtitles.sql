-- 0033 · 每集封面与字幕

-- 每集封面：指向 files 里 role='episode_cover' 的文件；为空则回退作品封面
ALTER TABLE episodes ADD COLUMN cover_file_id INTEGER REFERENCES files(id);

-- 字幕关联：episode_id 为空表示资源级（单文件视频用）
CREATE TABLE IF NOT EXISTS subtitle_tracks (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  file_id     INTEGER NOT NULL REFERENCES files(id)      ON DELETE CASCADE,
  episode_id  INTEGER          REFERENCES episodes(id)   ON DELETE CASCADE,
  language    TEXT,
  title       TEXT,
  is_default  INTEGER NOT NULL DEFAULT 0,
  sort_index  INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 同一字幕不可重复挂同一集；允许同一文件挂多集
CREATE UNIQUE INDEX IF NOT EXISTS ux_subtitle_tracks_file_episode
  ON subtitle_tracks(file_id, COALESCE(episode_id, 0));

CREATE INDEX IF NOT EXISTS ix_subtitle_tracks_episode
  ON subtitle_tracks(episode_id);
CREATE INDEX IF NOT EXISTS ix_subtitle_tracks_resource
  ON subtitle_tracks(resource_id);
