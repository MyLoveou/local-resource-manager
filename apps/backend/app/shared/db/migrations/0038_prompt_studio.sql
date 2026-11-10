-- 0038 · 提示词工作台

-- 保存的提示词（核心资产）
CREATE TABLE IF NOT EXISTS prompt_saves (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    model       TEXT NOT NULL DEFAULT 'anima',
    positive    TEXT NOT NULL DEFAULT '',
    negative    TEXT NOT NULL DEFAULT '',
    params_json TEXT,
    note        TEXT,
    categories_json TEXT,
    favorite    INTEGER NOT NULL DEFAULT 0,
    resource_id INTEGER REFERENCES resources(id) ON DELETE SET NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS ix_prompt_saves_updated ON prompt_saves(updated_at DESC);
CREATE INDEX IF NOT EXISTS ix_prompt_saves_favorite ON prompt_saves(favorite, updated_at DESC);

-- 从正向里抽出的标签，便于按标签筛存档
CREATE TABLE IF NOT EXISTS prompt_save_tags (
    save_id INTEGER NOT NULL REFERENCES prompt_saves(id) ON DELETE CASCADE,
    tag     TEXT NOT NULL,
    PRIMARY KEY (save_id, tag)
);
CREATE INDEX IF NOT EXISTS ix_prompt_save_tags_tag ON prompt_save_tags(tag);

-- 用户自建内容：升级内置库不会覆盖
CREATE TABLE IF NOT EXISTS prompt_custom_tags (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    en         TEXT NOT NULL,
    zh         TEXT,
    category   TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prompt_custom_presets (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    category   TEXT,
    tags_text  TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 复制/生成过的提示词历史（可置顶）
CREATE TABLE IF NOT EXISTS prompt_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    save_id    INTEGER REFERENCES prompt_saves(id) ON DELETE SET NULL,
    model      TEXT NOT NULL DEFAULT 'anima',
    positive   TEXT NOT NULL DEFAULT '',
    negative   TEXT NOT NULL DEFAULT '',
    pinned     INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prompt_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
