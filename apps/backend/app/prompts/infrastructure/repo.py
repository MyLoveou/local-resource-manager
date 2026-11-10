"""提示词存档的 SQLite 读写。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

MAX_LIMIT = 200


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _row_to_save(row: Any) -> dict:
    data = dict(row)
    for key in ("params", "categories"):
        raw = data.pop(f"{key}_json", None)
        if raw:
            try:
                data[key] = json.loads(raw)
            except json.JSONDecodeError:
                data[key] = None
        else:
            data[key] = None
    data["favorite"] = bool(data.get("favorite"))
    return data


async def list_saves(
    session: AsyncSession,
    *,
    query: str | None = None,
    tag: str | None = None,
    favorite: bool = False,
    limit: int = 100,
) -> list[dict]:
    sql = "SELECT * FROM prompt_saves"
    where: list[str] = []
    params: dict[str, Any] = {"limit": min(limit, MAX_LIMIT)}
    if query:
        where.append("(title LIKE :q OR positive LIKE :q OR note LIKE :q)")
        params["q"] = f"%{query}%"
    if tag:
        where.append("id IN (SELECT save_id FROM prompt_save_tags WHERE tag = :tag)")
        params["tag"] = tag
    if favorite:
        where.append("favorite = 1")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY favorite DESC, updated_at DESC LIMIT :limit"
    rows = (await session.execute(text(sql), params)).mappings().all()
    return [_row_to_save(row) for row in rows]


async def get_save(session: AsyncSession, save_id: int) -> dict | None:
    row = (
        await session.execute(
            text("SELECT * FROM prompt_saves WHERE id = :id"), {"id": save_id}
        )
    ).mappings().first()
    return _row_to_save(row) if row else None


async def _sync_tags(session: AsyncSession, save_id: int, tags: list[str]) -> None:
    await session.execute(
        text("DELETE FROM prompt_save_tags WHERE save_id = :id"), {"id": save_id}
    )
    for tag in {tag.strip() for tag in tags if tag.strip()}:
        await session.execute(
            text("INSERT OR IGNORE INTO prompt_save_tags (save_id, tag) VALUES (:id, :tag)"),
            {"id": save_id, "tag": tag},
        )


async def create_save(session: AsyncSession, payload: dict, tags: list[str]) -> int:
    now = _now()
    result = await session.execute(
        text(
            "INSERT INTO prompt_saves"
            " (title, model, positive, negative, params_json, note, categories_json,"
            "  favorite, resource_id, image_data, created_at, updated_at)"
            " VALUES (:title, :model, :positive, :negative, :params, :note, :categories,"
            "         :favorite, :rid, :image, :now, :now)"
        ),
        {
            "title": payload["title"],
            "model": payload.get("model") or "anima",
            "positive": payload.get("positive") or "",
            "negative": payload.get("negative") or "",
            "params": json.dumps(payload.get("params"), ensure_ascii=False)
            if payload.get("params")
            else None,
            "note": payload.get("note"),
            "categories": json.dumps(payload.get("categories"), ensure_ascii=False)
            if payload.get("categories")
            else None,
            "favorite": 1 if payload.get("favorite") else 0,
            "rid": payload.get("resource_id"),
            "image": payload.get("image_data"),
            "now": now,
        },
    )
    save_id = int(result.lastrowid or 0)
    await _sync_tags(session, save_id, tags)
    await session.commit()
    return save_id


async def update_save(
    session: AsyncSession, save_id: int, payload: dict, tags: list[str] | None
) -> bool:
    row = await get_save(session, save_id)
    if row is None:
        return False
    fields = {
        "title": payload.get("title", row["title"]),
        "model": payload.get("model", row["model"]),
        "positive": payload.get("positive", row["positive"]),
        "negative": payload.get("negative", row["negative"]),
        "note": payload.get("note", row["note"]),
        "favorite": 1 if payload.get("favorite", row["favorite"]) else 0,
        "image": payload.get("image_data", row.get("image_data")),
        "params": json.dumps(payload["params"], ensure_ascii=False)
        if payload.get("params") is not None
        else (json.dumps(row["params"], ensure_ascii=False) if row["params"] else None),
        "categories": json.dumps(payload["categories"], ensure_ascii=False)
        if payload.get("categories") is not None
        else (json.dumps(row["categories"], ensure_ascii=False) if row["categories"] else None),
        "now": _now(),
        "id": save_id,
    }
    await session.execute(
        text(
            "UPDATE prompt_saves SET title = :title, model = :model, positive = :positive,"
            " negative = :negative, note = :note, favorite = :favorite, params_json = :params,"
            " categories_json = :categories, image_data = :image, updated_at = :now WHERE id = :id"
        ),
        fields,
    )
    if tags is not None:
        await _sync_tags(session, save_id, tags)
    await session.commit()
    return True


async def delete_save(session: AsyncSession, save_id: int) -> bool:
    result = await session.execute(
        text("DELETE FROM prompt_saves WHERE id = :id"), {"id": save_id}
    )
    await session.commit()
    return bool(result.rowcount)


async def add_history(
    session: AsyncSession, *, model: str, positive: str, negative: str, save_id: int | None
) -> int:
    result = await session.execute(
        text(
            "INSERT INTO prompt_history (save_id, model, positive, negative, created_at)"
            " VALUES (:sid, :model, :positive, :negative, :now)"
        ),
        {"sid": save_id, "model": model, "positive": positive, "negative": negative, "now": _now()},
    )
    await session.execute(
        text(
            "DELETE FROM prompt_history WHERE pinned = 0 AND id NOT IN"
            " (SELECT id FROM prompt_history ORDER BY created_at DESC LIMIT 40)"
        )
    )
    await session.commit()
    return int(result.lastrowid or 0)


async def list_history(session: AsyncSession, limit: int = 40) -> list[dict]:
    rows = (
        await session.execute(
            text(
                "SELECT * FROM prompt_history ORDER BY pinned DESC, created_at DESC LIMIT :limit"
            ),
            {"limit": min(limit, MAX_LIMIT)},
        )
    ).mappings().all()
    items = []
    for row in rows:
        data = dict(row)
        data["pinned"] = bool(data.get("pinned"))
        items.append(data)
    return items


async def pin_history(session: AsyncSession, history_id: int, pinned: bool) -> bool:
    result = await session.execute(
        text("UPDATE prompt_history SET pinned = :pinned WHERE id = :id"),
        {"pinned": 1 if pinned else 0, "id": history_id},
    )
    await session.commit()
    return bool(result.rowcount)


async def list_custom(session: AsyncSession, table: str) -> list[dict]:
    if table not in ("prompt_custom_tags", "prompt_custom_presets"):
        raise ValueError("unsupported table")
    rows = (
        await session.execute(text(f"SELECT * FROM {table} ORDER BY created_at DESC LIMIT 500"))
    ).mappings().all()
    return [dict(row) for row in rows]


async def add_custom(session: AsyncSession, table: str, payload: dict) -> int:
    now = _now()
    if table == "prompt_custom_tags":
        result = await session.execute(
            text(
                "INSERT INTO prompt_custom_tags (en, zh, category, created_at)"
                " VALUES (:en, :zh, :category, :now)"
            ),
            {
                "en": payload["en"],
                "zh": payload.get("zh"),
                "category": payload.get("category") or "其他",
                "now": now,
            },
        )
    elif table == "prompt_custom_presets":
        result = await session.execute(
            text(
                "INSERT INTO prompt_custom_presets (name, category, tags_text, created_at)"
                " VALUES (:name, :category, :tags, :now)"
            ),
            {
                "name": payload["name"],
                "category": payload.get("category"),
                "tags": payload.get("tags") or "",
                "now": now,
            },
        )
    else:
        raise ValueError("unsupported table")
    await session.commit()
    return int(result.lastrowid or 0)


async def delete_custom(session: AsyncSession, table: str, item_id: int) -> bool:
    if table not in ("prompt_custom_tags", "prompt_custom_presets"):
        raise ValueError("unsupported table")
    result = await session.execute(
        text(f"DELETE FROM {table} WHERE id = :id"), {"id": item_id}
    )
    await session.commit()
    return bool(result.rowcount)


async def get_settings(session: AsyncSession) -> dict[str, Any]:
    rows = (await session.execute(text("SELECT key, value FROM prompt_settings"))).mappings().all()
    result: dict[str, Any] = {}
    for row in rows:
        try:
            result[row["key"]] = json.loads(row["value"])
        except json.JSONDecodeError:
            result[row["key"]] = row["value"]
    return result


async def put_settings(session: AsyncSession, values: dict[str, Any]) -> None:
    for key, value in values.items():
        await session.execute(
            text(
                "INSERT INTO prompt_settings (key, value) VALUES (:key, :value)"
                " ON CONFLICT(key) DO UPDATE SET value = excluded.value"
            ),
            {"key": key, "value": json.dumps(value, ensure_ascii=False)},
        )
    await session.commit()
