-- 图片 EXIF 只读详情（机身/镜头/ISO/光圈/快门），不写回文件
ALTER TABLE files ADD COLUMN exif_camera TEXT;
ALTER TABLE files ADD COLUMN exif_lens TEXT;
ALTER TABLE files ADD COLUMN exif_iso INTEGER;
ALTER TABLE files ADD COLUMN exif_aperture TEXT;
ALTER TABLE files ADD COLUMN exif_shutter TEXT;
