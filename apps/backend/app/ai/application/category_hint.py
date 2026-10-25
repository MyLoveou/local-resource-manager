"""分类建议（闭集）：只从用户已有的分类里选。

做法：找与目标资源**共享标签**的其它资源，按它们所属分类投票。
不依赖模型，结果可解释（"和这批同标签的图在同一个分类"）。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_LIMIT = 2
MIN_VOTES = 2


def _pick(candidates: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    total = sum(item["votes"] for item in candidates)
    if not total:
        return []
    picked: list[dict[str, Any]] = []
    for item in candidates[:limit]:
        if item["votes"] < MIN_VOTES:
            continue
        picked.append(
            {
                "id": item["id"],
                "name": item["name"],
                "confidence": round(item["votes"] / total, 2),
            }
        )
    return picked


async def category_hints(
    session: AsyncSession,
    resource_ids: list[int],
    *,
    limit: int = DEFAULT_LIMIT,
) -> dict[int, list[dict[str, Any]]]:
    """返回 {resource_id: [{id, name, confidence}]}；已属于该分类的不再建议。"""
    if not resource_ids:
        return {}
    params = {f"r{index}": rid for index, rid in enumerate(resource_ids)}
    placeholders = ", ".join(f":r{index}" for index in range(len(resource_ids)))
    rows = (
        await session.execute(
            text(
                "SELECT rt1.resource_id AS rid, c.id, c.name, "
                "       COUNT(DISTINCT rt2.resource_id) AS votes "
                "FROM resource_tags rt1 "
                "JOIN resource_tags rt2 "
                "  ON rt2.tag_id = rt1.tag_id AND rt2.resource_id <> rt1.resource_id "
                "JOIN resource_categories rc ON rc.resource_id = rt2.resource_id "
                "JOIN categories c ON c.id = rc.category_id "
                "JOIN resources r ON r.id = rt1.resource_id "
                f"WHERE rt1.resource_id IN ({placeholders}) "
                "  AND c.type = r.type "
                "  AND NOT EXISTS ("
                "    SELECT 1 FROM resource_categories rc2 "
                "    WHERE rc2.resource_id = rt1.resource_id AND rc2.category_id = c.id"
                "  ) "
                "GROUP BY rt1.resource_id, c.id, c.name "
                "ORDER BY rt1.resource_id, votes DESC"
            ),
            params,
        )
    ).mappings().all()

    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(int(row["rid"]), []).append(
            {
                "id": int(row["id"]),
                "name": str(row["name"]),
                "votes": int(row["votes"]),
            }
        )
    return {rid: picked for rid, picked in ((r, _pick(c, limit)) for r, c in grouped.items()) if picked}
