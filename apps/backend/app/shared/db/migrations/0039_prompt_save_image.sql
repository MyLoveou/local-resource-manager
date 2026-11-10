-- 0039 · 提示词存档带一张风格预览图（前端缩放到 384px 的 JPEG data URL）
ALTER TABLE prompt_saves ADD COLUMN image_data TEXT;
