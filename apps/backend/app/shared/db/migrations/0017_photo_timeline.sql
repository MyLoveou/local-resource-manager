-- 0017 · 照片时间线/地图：可见性三态 + EXIF GPS
-- timeline_visible: NULL=按 EXIF 自动；1=强制计入；0=强制排除
-- exif_lat/exif_lng: WGS84 十进制度（primary 文件）

ALTER TABLE resources ADD COLUMN timeline_visible INTEGER;
ALTER TABLE files ADD COLUMN exif_lat REAL;
ALTER TABLE files ADD COLUMN exif_lng REAL;
