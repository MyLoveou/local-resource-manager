-- 0035 · 按季挂元数据

-- 一部作品的多个季各自对应站点上的不同条目，元数据不能只挂在资源上
ALTER TABLE seasons ADD COLUMN catalog_json TEXT;
ALTER TABLE seasons ADD COLUMN cover_file_id INTEGER REFERENCES files(id);
