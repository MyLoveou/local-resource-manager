-- 0034 · 特典封面

-- 与每集封面一致：指向 files 里 role='episode_cover' 的文件；为空回退作品封面
ALTER TABLE extras ADD COLUMN cover_file_id INTEGER REFERENCES files(id);
