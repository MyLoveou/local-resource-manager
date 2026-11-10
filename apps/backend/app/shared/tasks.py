"""统一任务表：状态落库，重启后仍能显示"被中断"。

三种任务原先各有一套内存状态（刮削队列、导入 job、AI job），共同的问题是
进程一重启就什么都不知道了。这里只做一件事：把任务的生命周期写进 SQLite。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

KIND_SCRAPE = "scrape"
KIND_IMPORT = "import"
KIND_AI_INDEX = "ai_index"
KIND_COVER = "cover"

QUEUED = "queued"
RUNNING = "running"
DONE = "done"
FAILED = "failed"
CANCELLED = "cancelled"
INTERRUPTED = "interrupted"

ACTIVE_STATES = (QUEUED, RUNNING)
RETENTION_DAYS = 7


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


async def create(
    session: AsyncSession,
    *,
    kind: str,
    title: str,
    resource_id: int | None = None,
    dedupe_key: str | None = None,
    total: int = 0,
    payload: dict[str, Any] | None = None,
) -> str | None:
    """建任务；同 kind + dedupe_key 已有活动任务时返回 None（防重复）。"""
    task_id = uuid.uuid4().hex
    try:
        await session.execute(
            text(
                "INSERT INTO tasks (id, kind, resource_id, dedupe_key, title, state, total, payload, created_at)"
                " VALUES (:id, :kind, :rid, :key, :title, :state, :total, :payload, :now)"
            ),
            {
                "id": task_id,
                "kind": kind,
                "rid": resource_id,
                "key": dedupe_key,
                "title": title,
                "state": QUEUED,
                "total": total,
                "payload": json.dumps(payload, ensure_ascii=False) if payload else None,
                "now": _now(),
            },
        )
        await session.commit()
        return task_id
    except Exception:  # noqa: BLE001 - 唯一索引冲突即视为重复
        await session.rollback()
        return None


async def start(session: AsyncSession, task_id: str) -> None:
    await session.execute(
        text(
            "UPDATE tasks SET state = :state, started_at = :now, heartbeat_at = :now,"
            " attempts = attempts + 1 WHERE id = :id"
        ),
        {"state": RUNNING, "now": _now(), "id": task_id},
    )
    await session.commit()


async def progress(
    session: AsyncSession,
    task_id: str,
    *,
    done: int | None = None,
    total: int | None = None,
    percent: float | None = None,
) -> None:
    await session.execute(
        text(
            "UPDATE tasks SET"
            " done = COALESCE(:done, done),"
            " total = COALESCE(:total, total),"
            " percent = COALESCE(:percent, percent),"
            " heartbeat_at = :now"
            " WHERE id = :id"
        ),
        {"done": done, "total": total, "percent": percent, "now": _now(), "id": task_id},
    )
    await session.commit()


async def finish(session: AsyncSession, task_id: str) -> None:
    await session.execute(
        text(
            "UPDATE tasks SET state = :state, percent = 100, finished_at = :now,"
            " heartbeat_at = :now WHERE id = :id"
        ),
        {"state": DONE, "now": _now(), "id": task_id},
    )
    await session.commit()


async def fail(session: AsyncSession, task_id: str, reason: str) -> None:
    await session.execute(
        text(
            "UPDATE tasks SET state = :state, error = :error, finished_at = :now,"
            " heartbeat_at = :now WHERE id = :id"
        ),
        {"state": FAILED, "error": reason[:300], "now": _now(), "id": task_id},
    )
    await session.commit()


async def cancel(session: AsyncSession, task_id: str) -> None:
    await session.execute(
        text(
            "UPDATE tasks SET state = :state, finished_at = :now WHERE id = :id"
        ),
        {"state": CANCELLED, "now": _now(), "id": task_id},
    )
    await session.commit()


async def list_tasks(session: AsyncSession, *, states: tuple[str, ...] | None = None) -> list[dict]:
    sql = "SELECT * FROM tasks"
    params: dict[str, Any] = {}
    if states:
        placeholders = ", ".join(f":s{i}" for i in range(len(states)))
        sql += f" WHERE state IN ({placeholders})"
        params = {f"s{i}": state for i, state in enumerate(states)}
    sql += " ORDER BY created_at DESC LIMIT 200"
    rows = (await session.execute(text(sql), params)).mappings().all()
    return [dict(row) for row in rows]


async def recover_on_startup(session: AsyncSession) -> dict[str, int]:
    """上次进程留下的 running：一律标成 interrupted，绝不静默续跑。

    自动重排时**每个 dedupe_key 只放回一个**——唯一索引要求同类任务只能有一个
    活动行，一次放回多条会直接抛 IntegrityError 把启动搞崩（已踩过）。
    同一批次里的其余任务标记为 cancelled，避免它们永远停在 interrupted。
    """
    interrupted = 0
    requeued = 0
    superseded = 0
    try:
        result = await session.execute(
            text(
                "UPDATE tasks SET state = :interrupted, heartbeat_at = :now"
                " WHERE state = :running"
            ),
            {"interrupted": INTERRUPTED, "running": RUNNING, "now": _now()},
        )
        await session.commit()
        interrupted = result.rowcount or 0

        for kind in (KIND_SCRAPE, KIND_COVER):
            rows = (
                await session.execute(
                    text(
                        "SELECT id, dedupe_key FROM tasks"
                        " WHERE kind = :kind AND state = :interrupted"
                        " ORDER BY created_at DESC"
                    ),
                    {"kind": kind, "interrupted": INTERRUPTED},
                )
            ).mappings().all()
            seen: set[str] = set()
            for row in rows:
                key = row["dedupe_key"] or row["id"]
                if key in seen:
                    await session.execute(
                        text("UPDATE tasks SET state = :cancelled WHERE id = :id"),
                        {"cancelled": CANCELLED, "id": row["id"]},
                    )
                    superseded += 1
                    continue
                seen.add(key)
                await session.execute(
                    text("UPDATE tasks SET state = :queued WHERE id = :id"),
                    {"queued": QUEUED, "id": row["id"]},
                )
                requeued += 1
        await session.commit()
    except Exception:  # noqa: BLE001 - 恢复失败绝不能挡住启动
        await session.rollback()
    return {"interrupted": interrupted, "requeued": requeued, "superseded": superseded}

async def prune(session: AsyncSession, days: int = RETENTION_DAYS) -> int:
    """清理过期终态任务，避免表无限增长。"""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    result = await session.execute(
        text(
            "DELETE FROM tasks WHERE state IN (:done, :failed, :cancelled)"
            " AND COALESCE(finished_at, created_at) < :cutoff"
        ),
        {"done": DONE, "failed": FAILED, "cancelled": CANCELLED, "cutoff": cutoff},
    )
    await session.commit()
    return result.rowcount or 0
