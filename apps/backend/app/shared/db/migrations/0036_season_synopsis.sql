-- 0036 · 季简介

-- 站点档案（catalog_json）里没有简介字段，简介在资源上；季要单独保存
ALTER TABLE seasons ADD COLUMN synopsis TEXT;
