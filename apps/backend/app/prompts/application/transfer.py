"""提示词存档的导入 / 导出。

两种格式都吃：
1. 本应用导出格式（version + saves + customTags + customPresets + settings）
2. PromptForge 的导出 JSON（尽力兼容：从 saves / favorites / custom 里找得到就取）
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.prompts.infrastructure import repo

EXPORT_VERSION = 1


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


async def export_all(session: AsyncSession) -> dict[str, Any]:
    saves = (
        await session.execute(
            text("SELECT * FROM prompt_saves ORDER BY updated_at DESC")
        )
    ).mappings().all()
    tags = (
        await session.execute(
            text("SELECT save_id, tag FROM prompt_save_tags")
        )
    ).mappings().all()
    by_save: dict[int, list[str]] = {}
    for row in tags:
        by_save.setdefault(row["save_id"], []).append(row["tag"])

    items = []
    for row in saves:
        data = dict(row)
        data["tags"] = by_save.get(data["id"], [])
        items.append(data)

    return {
        "version": EXPORT_VERSION,
        "app": "local-resource-manager",
        "exportedAt": _now(),
        "saves": items,
        "customTags": await repo.list_custom(session, "prompt_custom_tags"),
        "customPresets": await repo.list_custom(session, "prompt_custom_presets"),
        "settings": await repo.get_settings(session),
    }


def _pick(item: dict, *names: str, default: Any = None) -> Any:
    for name in names:
        if name in item and item[name] not in (None, ""):
            return item[name]
    return default


def _normalize_save(raw: dict) -> dict | None:
    """把外部 JSON 的一条记录归一成本应用字段；认不出就跳过。"""
    if not isinstance(raw, dict):
        return None
    positive = _pick(raw, "positive", "prompt", "text", "value", "content") or ""
    if not isinstance(positive, str) or not positive.strip():
        return None
    title = _pick(raw, "title", "name", "label") or "导入的提示词"
    negative = _pick(raw, "negative", "neg", "negative_prompt") or ""
    model = _pick(raw, "model", "engine") or "anima"
    tags = raw.get("tags") if isinstance(raw.get("tags"), list) else []
    return {
        "title": str(title)[:200],
        "model": str(model),
        "positive": positive,
        "negative": str(negative),
        "note": _pick(raw, "note", "desc", "description"),
        "favorite": bool(_pick(raw, "favorite", "fav", default=False)),
        "image_data": _pick(raw, "image_data", "image", "thumb"),
        "tags": [str(tag) for tag in tags][:60],
    }


async def import_payload(session: AsyncSession, payload: dict) -> dict[str, int]:
    if not isinstance(payload, dict):
        return {"saves": 0, "customTags": 0, "customPresets": 0, "skipped": 0}

    candidates: list[dict] = []
    if isinstance(payload.get("saves"), list):
        candidates.extend(item for item in payload["saves"] if isinstance(item, dict))
    # PromptForge：pg_saves_v1 的历史/收藏可能挂在别处
    for key in ("favorites", "history", "prompts", "items"):
        if isinstance(payload.get(key), list):
            candidates.extend(item for item in payload[key] if isinstance(item, dict))

    existing = {
        row[0].strip().lower()
        for row in (
            await session.execute(text("SELECT positive FROM prompt_saves"))
        ).all()
    }

    created = 0
    skipped = 0
    for raw in candidates:
        save = _normalize_save(raw)
        if save is None:
            skipped += 1
            continue
        if save["positive"].strip().lower() in existing:
            skipped += 1
            continue
        await repo.create_save(session, save, save.pop("tags"))
        existing.add(save["positive"].strip().lower())
        created += 1

    custom_tags = 0
    for raw in payload.get("customTags") or payload.get("custom_tags") or []:
        if not isinstance(raw, dict) or not _pick(raw, "en", "tag", "name"):
            continue
        await repo.add_custom(
            session,
            "prompt_custom_tags",
            {
                "en": str(_pick(raw, "en", "tag", "name")),
                "zh": _pick(raw, "zh", "cn"),
                "category": _pick(raw, "category", "cat") or "其他",
            },
        )
        custom_tags += 1

    custom_presets = 0
    for raw in payload.get("customPresets") or payload.get("custom_presets") or []:
        if not isinstance(raw, dict) or not _pick(raw, "name", "title"):
            continue
        await repo.add_custom(
            session,
            "prompt_custom_presets",
            {
                "name": str(_pick(raw, "name", "title")),
                "category": _pick(raw, "category", "cat"),
                "tags": _pick(raw, "tags", "text") or "",
            },
        )
        custom_presets += 1

    settings = payload.get("settings")
    if isinstance(settings, dict) and settings:
        await repo.put_settings(session, settings)

    return {
        "saves": created,
        "customTags": custom_tags,
        "customPresets": custom_presets,
        "skipped": skipped,
    }


def dump(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=1)
