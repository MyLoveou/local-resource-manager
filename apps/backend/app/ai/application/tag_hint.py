"""标签建议：把 AI 新词拆出来，并尝试归并到用户词表里的近义标签。

闭集原则：建议只允许写成「你词表里的标签」。AI 造的原始词单独一块展示，
若能匹配到近义标签就把匹配结果一起带出来，由用户决定用哪个。
"""

from __future__ import annotations

import asyncio
from typing import Any

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# 文本向量相似度门槛：低于此不认为同义
SIMILARITY_THRESHOLD = 0.86

_vocab_vectors: dict[str, Any] | None = None


def invalidate_vocab_vectors() -> None:
    """词表变化后清缓存（打标/删标签时调用）。"""
    global _vocab_vectors
    _vocab_vectors = None


async def vocabulary_vectors(session: AsyncSession) -> dict[str, Any]:
    """词表标签的文本向量；模型不可用时返回空字典（调用方降级）。"""
    global _vocab_vectors
    if _vocab_vectors is not None:
        return _vocab_vectors
    names = [
        str(row[0])
        for row in (await session.execute(text("SELECT name FROM tags"))).all()
        if row[0]
    ]
    if not names:
        _vocab_vectors = {}
        return _vocab_vectors
    try:
        from app.ai.infrastructure.runtime import runtime

        vectors = await asyncio.to_thread(runtime.encode_text, names)
    except Exception:  # noqa: BLE001 - 模型缺失/未安装时降级为纯列表
        _vocab_vectors = {}
        return _vocab_vectors
    _vocab_vectors = {
        name: np.asarray(vector, dtype="float32")
        for name, vector in zip(names, vectors)
        if vector is not None
    }
    return _vocab_vectors


def closest_vocabulary_tag(
    vector: Any, vocabulary: dict[str, Any]
) -> tuple[str, float] | None:
    """在词表里找最相近的标签；低于门槛返回 None。"""
    best: tuple[str, float] | None = None
    for name, candidate in vocabulary.items():
        score = float(np.dot(vector, candidate))
        if best is None or score > best[1]:
            best = (name, score)
    if best is None or best[1] < SIMILARITY_THRESHOLD:
        return None
    return best


async def new_tag_candidates(
    session: AsyncSession,
    resource_ids: list[int],
    *,
    limit: int = 6,
) -> dict[int, list[dict[str, Any]]]:
    """返回 AI 产出、但不在词表里的标签，附带最接近的词表标签（可能为空）。"""
    if not resource_ids:
        return {}
    params = {f"r{index}": rid for index, rid in enumerate(resource_ids)}
    placeholders = ", ".join(f":r{index}" for index in range(len(resource_ids)))
    rows = (
        await session.execute(
            text(
                "SELECT ai.resource_id, ai.tag FROM ai_tags ai "
                "JOIN resources r ON r.id = ai.resource_id "
                "WHERE ai.source IN ('vlm', 'wd14') AND r.status = 'active' "
                f"  AND ai.resource_id IN ({placeholders}) "
                "  AND NOT EXISTS (SELECT 1 FROM tags t WHERE t.name = ai.tag) "
                "ORDER BY ai.resource_id, ai.tag"
            ),
            params,
        )
    ).all()
    if not rows:
        return {}

    vocabulary = await vocabulary_vectors(session)
    encoded: dict[str, Any] = {}
    if vocabulary:
        try:
            from app.ai.infrastructure.runtime import runtime

            missing = sorted({str(tag) for _, tag in rows if str(tag) not in encoded})
            if missing:
                vectors = await asyncio.to_thread(runtime.encode_text, missing)
                encoded = {
                    name: np.asarray(vector, dtype="float32")
                    for name, vector in zip(missing, vectors)
                    if vector is not None
                }
        except Exception:  # noqa: BLE001 - 归并失败不影响展示
            encoded = {}

    grouped: dict[int, list[dict[str, Any]]] = {}
    for resource_id, tag in rows:
        rid = int(resource_id)
        name = str(tag)
        bucket = grouped.setdefault(rid, [])
        if len(bucket) >= limit:
            continue
        item: dict[str, Any] = {"name": name, "similar_to": None, "similarity": None}
        vector = encoded.get(name)
        if vector is not None:
            match = closest_vocabulary_tag(vector, vocabulary)
            if match is not None:
                item["similar_to"] = match[0]
                item["similarity"] = round(float(match[1]), 2)
        bucket.append(item)
    return grouped
