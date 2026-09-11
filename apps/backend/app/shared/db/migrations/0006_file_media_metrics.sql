-- 0006 · 视频帧率与码率（比特/秒）
ALTER TABLE files ADD COLUMN fps REAL;
ALTER TABLE files ADD COLUMN bitrate INTEGER;
