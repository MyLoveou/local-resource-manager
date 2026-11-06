"""导入建议仓储（S1 · smart-import）。"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

HIGH_CONFIDENCE = 0.85


def dump_value(value: dict | None) -> str | None:
    """建议值统一序列化；插入与查询必须用同一份实现，否则分组匹配不上。"""
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


class SuggestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def set_source_name(self, resource_id: int, name: str | None) -> None:
        """源名称只写一次（首次导入时），后续采纳改名不覆盖。"""
        if not name:
            return
        await self.session.execute(
            text(
                "UPDATE resources SET source_name = :name "
                "WHERE id = :id AND (source_name IS NULL OR source_name = '')"
            ),
            {"name": name, "id": resource_id},
        )
        await self.session.flush()

    async def insert_many(self, job_id, resource_id: int, suggestions: list) -> int:
        written = 0
        for item in suggestions:
            await self.session.execute(
                text(
                    "INSERT INTO import_suggestions "
                    "(resource_id, job_id, field, value, confidence, source, reason) "
                    "VALUES (:rid, :job, :field, :value, :conf, :src, :reason)"
                ),
                {
                    "rid": resource_id,
                    "job": job_id,
                    "field": item.field,
                    "value": dump_value(item.value),
                    "conf": float(item.confidence),
                    "src": item.source,
                    "reason": item.reason,
                },
            )
            written += 1
        if written:
            await self.session.commit()
        return written

    async def list_pending(
        self, job_id: str | None = None, *, cap: int = 5000
    ) -> list[Any]:
        sql = (
            "SELECT id, resource_id, field, value, confidence, source, reason "
            "FROM import_suggestions WHERE status = 'pending'"
        )
        params: dict[str, Any] = {"cap": cap}
        if job_id:
            sql += " AND job_id = :job"
            params["job"] = job_id
        sql += " ORDER BY id LIMIT :cap"
        result = await self.session.execute(text(sql), params)
        return list(result.mappings().all())

    async def summary(self) -> dict[str, int]:
        row = (
            await self.session.execute(
                text(
                    "SELECT COUNT(*) AS pending, "
                    "       SUM(CASE WHEN confidence >= :high THEN 1 ELSE 0 END) AS high, "
                    "       COUNT(DISTINCT job_id) AS jobs "
                    "FROM import_suggestions WHERE status = 'pending'"
                ),
                {"high": HIGH_CONFIDENCE},
            )
        ).mappings().first()
        return {
            "pending": int(row["pending"] or 0) if row else 0,
            "highConfidence": int(row["high"] or 0) if row else 0,
            "jobs": int(row["jobs"] or 0) if row else 0,
        }

    async def _targets(
        self,
        ids: list[int] | None,
        groups: list[tuple[str, dict | None]] | None,
        min_confidence: float | None,
    ) -> list[Any]:
        if ids:
            result = await self.session.execute(
                text(
                    "SELECT id, resource_id, field, value, confidence FROM import_suggestions "
                    "WHERE status = 'pending' AND id IN :ids"
                ).bindparams(bindparam("ids", expanding=True)),
                {"ids": ids},
            )
            return list(result.mappings().all())

        rows: list[Any] = []
        for field, value in groups or []:
            sql = (
                "SELECT id, resource_id, field, value, confidence FROM import_suggestions "
                "WHERE status = 'pending' AND field = :field AND value = :value"
            )
            params: dict[str, Any] = {"field": field, "value": dump_value(value)}
            if min_confidence is not None:
                sql += " AND confidence >= :min"
                params["min"] = float(min_confidence)
            result = await self.session.execute(text(sql), params)
            rows.extend(result.mappings().all())
        return rows

    async def apply(
        self,
        ids: list[int] | None = None,
        groups: list[tuple[str, dict | None]] | None = None,
        min_confidence: float | None = None,
    ) -> dict[str, int]:
        rows = await self._targets(ids, groups, min_confidence)
        accepted = 0
        skipped = 0
        touched: set[int] = set()

        for row in rows:
            if row["field"] != "title":
                # 分类建议在 S2 落地；此处不静默采纳其它字段
                skipped += 1
                continue
            text_value = json.loads(row["value"] or "{}").get("text")
            if not text_value:
                skipped += 1
                continue
            await self.session.execute(
                text(
                    "UPDATE resources SET title = :title, updated_at = datetime('now') "
                    "WHERE id = :id"
                ),
                {"title": text_value, "id": row["resource_id"]},
            )
            await self.session.execute(
                text(
                    "UPDATE import_suggestions SET status = 'accepted', "
                    "decided_at = datetime('now') WHERE id = :id"
                ),
                {"id": row["id"]},
            )
            touched.add(int(row["resource_id"]))
            accepted += 1

        await self.session.commit()
        return {"accepted": accepted, "skipped": skipped, "updated_resources": len(touched)}

    async def reject(
        self,
        ids: list[int] | None = None,
        groups: list[tuple[str, dict | None]] | None = None,
        reject_all: bool = False,
    ) -> dict[str, int]:
        if reject_all and not ids and not groups:
            result = await self.session.execute(
                text(
                    "UPDATE import_suggestions SET status = 'rejected', "
                    "decided_at = datetime('now') WHERE status = 'pending'"
                )
            )
            await self.session.commit()
            return {"rejected": int(result.rowcount or 0)}

        rows = await self._targets(ids, groups, None)
        if not rows:
            await self.session.commit()
            return {"rejected": 0}
        await self.session.execute(
            text(
                "UPDATE import_suggestions SET status = 'rejected', "
                "decided_at = datetime('now') WHERE id IN :ids"
            ).bindparams(bindparam("ids", expanding=True)),
            {"ids": [int(row["id"]) for row in rows]},
        )
        await self.session.commit()
        return {"rejected": len(rows)}
