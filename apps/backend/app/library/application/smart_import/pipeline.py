"""智能导入 pipeline：跑动作、落建议、分组分页。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.library.application.smart_import import actions  # noqa: F401  触发动作注册
from app.library.application.smart_import.base import (
    ActionContext,
    Suggestion,
    actions_for,
)
from app.library.application.smart_import.title_ai import refine_suggestions
from app.library.domain.models import ResourceType
from app.library.infrastructure.repositories_suggestions import SuggestionRepository
from app.shared.log import logger


def evaluate(ctx: ActionContext) -> list[Suggestion]:
    """跑该类型的全部动作；单个动作失败不影响其它动作（L1 §8）。"""
    out: list[Suggestion] = []
    for action in actions_for(ctx.type):
        try:
            out.extend(action.evaluate(ctx))
        except Exception as exc:  # noqa: BLE001 - 建议失败不得中断导入
            logger.warning("导入动作失败 field=%s: %s", action.field, exc)
    return out


async def suggest_after_ingest(
    resources,
    *,
    job_id: str | None,
    resource_id: int,
    type_: ResourceType,
    source_name: str | None,
    dir_name: str | None = None,
) -> int:
    """导入收尾钩子：写源名称 + 产出建议。任何失败都只记日志。"""
    try:
        repo = SuggestionRepository(resources.session)
        await repo.set_source_name(resource_id, source_name)
        stem = Path(source_name).stem if source_name else ""
        ctx = ActionContext(
            resource_id=resource_id,
            type=type_,
            file_stem=stem,
            dir_name=dir_name,
        )
        suggestions = evaluate(ctx)
        suggestions = await refine_suggestions(ctx, suggestions)
        if not suggestions:
            return 0
        return await repo.insert_many(job_id, resource_id, suggestions)
    except Exception as exc:  # noqa: BLE001 - 建议失败不得中断导入
        logger.warning("智能导入建议生成失败 resource=%s: %s", resource_id, exc)
        return 0


def group_pending(rows: list[Any]) -> list[dict]:
    """按 (field, value) 聚合；组置信度取组内最小值（保守）。"""
    buckets: dict[tuple[str, str], dict] = {}
    for row in rows:
        raw_value = row["value"] or ""
        bucket = buckets.get((row["field"], raw_value))
        if bucket is None:
            bucket = {
                "field": row["field"],
                "value": json.loads(raw_value) if raw_value else None,
                "source": row["source"],
                "confidence": float(row["confidence"]),
                "count": 0,
                "reasons": [],
                "suggestion_ids": [],
                "sample_resource_ids": [],
            }
            buckets[(row["field"], raw_value)] = bucket
        bucket["count"] += 1
        bucket["confidence"] = min(bucket["confidence"], float(row["confidence"]))
        reason = row["reason"] or ""
        if reason and reason not in bucket["reasons"] and len(bucket["reasons"]) < 3:
            bucket["reasons"].append(reason)
        bucket["suggestion_ids"].append(int(row["id"]))
        if len(bucket["sample_resource_ids"]) < 3:
            bucket["sample_resource_ids"].append(int(row["resource_id"]))

    groups = list(buckets.values())
    groups.sort(key=lambda group: (-group["confidence"], -group["count"]))
    return groups


async def suggestion_page(
    repo: SuggestionRepository,
    *,
    job_id: str | None,
    limit: int,
    offset: int,
) -> dict:
    rows = await repo.list_pending(job_id)
    groups = group_pending(rows)
    total = sum(group["count"] for group in groups)
    return {
        "groups": groups[offset : offset + limit],
        "total": total,
    }
