-- 0031 · 播放进度 + 音轨元数据（video-management S1）
-- 进度按 file_id 记：episodes 挂在 file_id 上，一个番剧作品 = 1 Resource + N file。
-- 若按 resource_id 记，整部作品会共用一个播放位置。

CREATE TABLE IF NOT EXISTS playback_progress (
  file_id     INTEGER PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE,
  resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  position    REAL NOT NULL DEFAULT 0,
  duration    REAL,
  completed   INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
  updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_playback_updated  ON playback_progress(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_playback_resource ON playback_progress(resource_id);
CREATE INDEX IF NOT EXISTS idx_playback_resume   ON playback_progress(completed, updated_at DESC);

-- 音轨三列：S1 只采集，S3 才进筛选与展示
ALTER TABLE files ADD COLUMN audio_codec    TEXT;
ALTER TABLE files ADD COLUMN audio_channels INTEGER;
ALTER TABLE files ADD COLUMN audio_language TEXT;
