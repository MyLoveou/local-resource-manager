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
from app.library.application.smart_import.preferences import is_ai_enabled
from app.library.application.smart_import.title_ai import ai_only_suggestion, refine_suggestions
from app.library.domain.models import ResourceType
from app.library.infrastructure.repositories_suggestions import SuggestionRepository
from app.shared.log import logger

# 规则没产出也值得问模型的类型：番剧/AV/视频的发布名长尾最多；
# 图片一次几百张，逐张调模型不划算，交给规则即可
_AI_UNSEEDED_TYPES = frozenset({ResourceType.ANIME, ResourceType.AV, ResourceType.VIDEO})


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
        if await is_ai_enabled(resources.session):
            suggestions = await refine_suggestions(ctx, suggestions, enabled=True)
            # 规则什么都没产出时，也要让模型给出标题；图片量太大，不在这里调模型
            if ctx.type in _AI_UNSEEDED_TYPES and not any(
                item.field == "title" for item in suggestions
            ):
                extra = await ai_only_suggestion(ctx)
                if extra is not None:
                    suggestions.append(extra)
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
