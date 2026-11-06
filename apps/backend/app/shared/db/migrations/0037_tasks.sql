-- 0037 · 统一任务表

-- 进程内状态（刮削队列、导入 job）重启即丢；统一落库，重启后仍能显示"被中断"
CREATE TABLE IF NOT EXISTS tasks (
    id           TEXT PRIMARY KEY,
    kind         TEXT NOT NULL,
    resource_id  INTEGER,
    dedupe_key   TEXT,
    title        TEXT NOT NULL,
    state        TEXT NOT NULL,
    done         INTEGER NOT NULL DEFAULT 0,
    total        INTEGER NOT NULL DEFAULT 0,
    percent      REAL NOT NULL DEFAULT 0,
    attempts     INTEGER NOT NULL DEFAULT 0,
    error        TEXT,
    payload      TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    started_at   TEXT,
    finished_at  TEXT,
    heartbeat_at TEXT
);

-- 同一类任务、同一个去重键，只允许一个在跑（防重复点击）
CREATE UNIQUE INDEX IF NOT EXISTS ux_tasks_active
    ON tasks(kind, dedupe_key)
    WHERE state IN ('queued', 'running');

CREATE INDEX IF NOT EXISTS ix_tasks_state ON tasks(state, created_at);
