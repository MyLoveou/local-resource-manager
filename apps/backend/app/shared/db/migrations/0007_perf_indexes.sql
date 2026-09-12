-- 0007 · 列表与文件角色复合索引（app-performance）
CREATE INDEX IF NOT EXISTS idx_resources_status_type_created_id
  ON resources(status, type, created_at, id);
CREATE INDEX IF NOT EXISTS idx_files_resource_role
  ON files(resource_id, role);
