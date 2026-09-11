-- 0002 · files.role：primary / cover / 后续 sidecar
ALTER TABLE files ADD COLUMN role TEXT NOT NULL DEFAULT 'primary';
