"""分类建议（闭集）：只从用户已有的分类里选。

做法：找与目标资源**共享标签**的其它资源，按它们所属分类投票。
不依赖模型，结果可解释（"和这批同标签的图在同一个分类"）。
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.infrastructure.model_store import MODEL_ID

DEFAULT_LIMIT = 2
MIN_VOTES = 2
MIN_SIMILARITY = 0.82
NEIGHBOURS = 8


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


async def vector_category_hints(
    session: AsyncSession,
    resource_ids: list[int],
    *,
    limit: int = DEFAULT_LIMIT,
    neighbours: int = NEIGHBOURS,
    min_similarity: float = MIN_SIMILARITY,
) -> dict[int, list[dict[str, Any]]]:
    """兜底：标签没命中时，用 CLIP 向量找视觉近邻，按邻居所属分类加权投票。"""
    if not resource_ids:
        return {}
    rows = (
        await session.execute(
            text("SELECT resource_id, vector FROM ai_vectors WHERE model_id = :model"),
            {"model": MODEL_ID},
        )
    ).all()
    if not rows:
        return {}
    ids: list[int] = []
    vectors: list[np.ndarray] = []
    for rid, raw in rows:
        ids.append(int(rid))
        vectors.append(np.frombuffer(bytes(raw), dtype="<f4").astype("float32"))
    if not vectors:
        return {}
    index_of = {rid: pos for pos, rid in enumerate(ids)}
    matrix = np.stack(vectors)

    cat_rows = (
        await session.execute(
            text(
                "SELECT rc.resource_id, c.id, c.name FROM resource_categories rc "
                "JOIN categories c ON c.id = rc.category_id "
                "JOIN resources r ON r.id = rc.resource_id "
                "WHERE r.status = 'active'"
            )
        )
    ).all()
    by_resource: dict[int, list[tuple[int, str]]] = {}
    for rid, cid, name in cat_rows:
        by_resource.setdefault(int(rid), []).append((int(cid), str(name)))

    hints: dict[int, list[dict[str, Any]]] = {}
    for target in resource_ids:
        pos = index_of.get(target)
        if pos is None:
            continue
        scores = matrix @ matrix[pos]
        order = np.argsort(-scores)
        own = {cid for cid, _ in by_resource.get(target, [])}
        weighted: dict[int, float] = {}
        names: dict[int, str] = {}
        taken = 0
        for neighbour in order:
            other = ids[int(neighbour)]
            if other == target:
                continue
            similarity = float(scores[int(neighbour)])
            if similarity < min_similarity:
                break
            for cid, name in by_resource.get(other, []):
                if cid in own:
                    continue
                weighted[cid] = weighted.get(cid, 0.0) + similarity
                names[cid] = name
            taken += 1
            if taken >= neighbours:
                break
        total = sum(weighted.values())
        if not total:
            continue
        ranked = sorted(weighted.items(), key=lambda item: -item[1])[:limit]
        hints[target] = [
            {"id": cid, "name": names[cid], "confidence": round(score / total, 2)}
            for cid, score in ranked
        ]
    return hints


async def suggest_categories(
    session: AsyncSession,
    resource_ids: list[int],
    *,
    limit: int = DEFAULT_LIMIT,
) -> dict[int, list[dict[str, Any]]]:
    """先按标签共现投票；没有命中的再用向量近邻兜底。"""
    hints = await category_hints(session, resource_ids, limit=limit)
    gaps = [rid for rid in resource_ids if rid not in hints]
    if gaps:
        hints.update(await vector_category_hints(session, gaps, limit=limit))
    return hints
