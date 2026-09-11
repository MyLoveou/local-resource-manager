"""资源库仓储实现（SQLAlchemy 2.0 async）。

ORM 行 ↔ Pydantic 领域模型；API camelCase 由 ApiModel 负责。
"""
import json
from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.db.orm import DownloadTaskRow, FileRow, ResourceRow, ScrapeJobRow
from app.shared.models import Resource, ResourceStatus, ResourceType


def _now() -> str:
    """与 SQLite datetime('now') 同格式的时间戳。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _orm_to_resource(row: ResourceRow) -> Resource:
    """ORM 行 → 领域模型。"""
    return Resource(
        id=row.id,
        type=ResourceType(row.type),
        title=row.title,
        description=row.description,
        rating=row.rating,
        cover_path=row.cover_path,
        status=ResourceStatus(row.status),
        deleted_at=row.deleted_at,
        last_scraped_at=row.last_scraped_at,
        scraped_source=row.scraped_source,
        extra=json.loads(row.extra or "{}"),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class ResourceRepository:
    """资源仓储：创建/查询/统计。"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, resource: Resource) -> Resource:
        """插入并返回带 id 的完整实体。"""
        ts = _now()
        row = ResourceRow(
            type=resource.type.value,
            title=resource.title,
            description=resource.description,
            rating=resource.rating,
            cover_path=resource.cover_path,
            status=resource.status.value,
            extra=json.dumps(resource.extra, ensure_ascii=False),
            created_at=ts,
            updated_at=ts,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _orm_to_resource(row)

    async def get(self, resource_id: int) -> Resource | None:
        row = await self._session.get(ResourceRow, resource_id)
        return _orm_to_resource(row) if row else None

    def _filter(
        self,
        stmt,
        type_: ResourceType | None,
        status: ResourceStatus | None,
    ):
        if type_ is not None:
            stmt = stmt.where(ResourceRow.type == type_.value)
        if status is not None:
            stmt = stmt.where(ResourceRow.status == status.value)
        return stmt

    async def count(
        self,
        type_: ResourceType | None = None,
        status: ResourceStatus | None = None,
    ) -> int:
        """与 list 相同过滤条件下的总数。"""
        stmt = self._filter(select(func.count()).select_from(ResourceRow), type_, status)
        total = await self._session.scalar(stmt)
        return int(total or 0)

    async def list(
        self,
        type_: ResourceType | None = None,
        status: ResourceStatus | None = None,
        limit: int = 50,
        offset: int = 0,
        order: str = "desc",
    ) -> list[Resource]:
        """条件列表查询（type/status 可空）。按创建时间 + id 排序，保证翻页稳定。"""
        stmt = self._filter(select(ResourceRow), type_, status)
        direction = desc if order == "desc" else asc
        stmt = stmt.order_by(direction(ResourceRow.created_at), direction(ResourceRow.id))
        stmt = stmt.limit(limit).offset(offset)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_orm_to_resource(r) for r in rows]

    async def create_many(self, resources: list[Resource]) -> int:
        """批量插入（演示 seed），一次提交。"""
        ts = _now()
        rows = [
            ResourceRow(
                type=r.type.value,
                title=r.title,
                description=r.description,
                rating=r.rating,
                cover_path=r.cover_path,
                status=r.status.value,
                extra=json.dumps(r.extra, ensure_ascii=False),
                created_at=ts,
                updated_at=ts,
            )
            for r in resources
        ]
        self._session.add_all(rows)
        await self._session.commit()
        return len(rows)

    async def rewrite_covers_starting_with(
        self,
        prefix: str,
        factory: Callable[[str, int], str],
    ) -> int:
        """将 cover_path 以 prefix 开头的行替换为 factory(type, id)。"""
        stmt = select(ResourceRow).where(ResourceRow.cover_path.like(f"{prefix}%"))
        rows = (await self._session.execute(stmt)).scalars().all()
        for row in rows:
            row.cover_path = factory(row.type, row.id)
        if rows:
            await self._session.commit()
        return len(rows)

    async def recent(self, limit: int = 12) -> list[Resource]:
        """最近入库的活跃资源。"""
        stmt = (
            select(ResourceRow)
            .where(ResourceRow.status == ResourceStatus.ACTIVE.value)
            .order_by(ResourceRow.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_orm_to_resource(r) for r in rows]

    async def stats(self) -> dict[str, Any]:
        """资源统计（供概览）：by_type + 库级指标。"""
        by_type_stmt = (
            select(ResourceRow.type, func.count())
            .where(ResourceRow.status == ResourceStatus.ACTIVE.value)
            .group_by(ResourceRow.type)
        )
        by_type_rows = (await self._session.execute(by_type_stmt)).all()
        by_type = {t: c for t, c in by_type_rows}

        trashed_count = await self._session.scalar(
            select(func.count())
            .select_from(ResourceRow)
            .where(ResourceRow.status == ResourceStatus.TRASHED.value)
        )
        lost_count = await self._session.scalar(
            select(func.count())
            .select_from(ResourceRow)
            .where(ResourceRow.status == ResourceStatus.LOST.value)
        )

        active_ids = select(ResourceRow.id).where(ResourceRow.status == ResourceStatus.ACTIVE.value)
        total_size_bytes = await self._session.scalar(
            select(func.coalesce(func.sum(FileRow.size), 0)).where(FileRow.resource_id.in_(active_ids))
        )

        return {
            "by_type": by_type,
            "total_size_bytes": int(total_size_bytes or 0),
            "trashed_count": int(trashed_count or 0),
            "lost_count": int(lost_count or 0),
        }


class TaskSummaryRepository:
    """进行中任务计数（跨 scrape/download 表，只读）。"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def summary(self) -> dict[str, int]:
        running_scrape_jobs = await self._session.scalar(
            select(func.count())
            .select_from(ScrapeJobRow)
            .where(ScrapeJobRow.status == "running")
        )
        failed_scrape_jobs = await self._session.scalar(
            select(func.count())
            .select_from(ScrapeJobRow)
            .where(ScrapeJobRow.status == "failed")
        )
        active_downloads = await self._session.scalar(
            select(func.count())
            .select_from(DownloadTaskRow)
            .where(DownloadTaskRow.status == "running")
        )
        return {
            "running_scrape_jobs": int(running_scrape_jobs or 0),
            "failed_scrape_jobs": int(failed_scrape_jobs or 0),
            "active_downloads": int(active_downloads or 0),
        }
