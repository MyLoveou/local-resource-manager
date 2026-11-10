"""Task summary, category, saved-view and timeline-note repositories."""

from __future__ import annotations

import json

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.domain.models import (
    Category,
    CategoryRule,
    ResourceType,
    SavedView,
    SavedViewFilters,
    TimelineNote,
)
from app.library.infrastructure.orm import (
    CategoryRow,
    ResourceCategoryRow,
    SavedViewRow,
    TimelineNoteRow,
)
from app.library.infrastructure.repositories_common import _category_to_domain
from app.scrape.infrastructure.orm import ScrapeJobRow
from app.shared.utils.time import db_now


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
        # 自建下载已移除（D-20261007-01）：下载计数恒为 0，字段保留兼容
        return {
            "running_scrape_jobs": int(running_scrape_jobs or 0),
            "failed_scrape_jobs": int(failed_scrape_jobs or 0),
            "active_downloads": 0,
        }


class CategoryRepository:
    """每类型分类树：读取、后代展开、计数与管理。"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, category_id: int) -> Category | None:
        row = await self._session.get(CategoryRow, category_id)
        return _category_to_domain(row) if row is not None else None

    async def list_rows(self, type_: ResourceType) -> list[CategoryRow]:
        return list((await self._session.execute(
            select(CategoryRow)
            .where(CategoryRow.type == type_.value)
            .order_by(CategoryRow.sort, CategoryRow.name, CategoryRow.id)
        )).scalars().all())

    async def list_all_rows(self) -> list[CategoryRow]:
        return list((await self._session.execute(
            select(CategoryRow).order_by(CategoryRow.type, CategoryRow.sort, CategoryRow.name)
        )).scalars().all())

    async def descendant_ids(self, category_ids: list[int]) -> list[int]:
        """返回节点自身及全部后代；按去重顺序。"""
        if not category_ids:
            return []
        rows = await self.list_all_rows()
        children: dict[int | None, list[int]] = {}
        for row in rows:
            children.setdefault(row.parent_id, []).append(row.id)
        out: list[int] = []
        seen: set[int] = set()
        stack = list(category_ids)
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            out.append(current)
            stack.extend(children.get(current, []))
        return out

    async def counts(self, type_: ResourceType) -> dict[int, int]:
        """每个节点（含后代）的去重 active 资源数。"""
        sql = text("""
            WITH RECURSIVE tree(ancestor_id, id) AS (
              SELECT id, id FROM categories WHERE type = :type
              UNION ALL
              SELECT tree.ancestor_id, child.id
              FROM categories child
              JOIN tree ON child.parent_id = tree.id
            )
            SELECT tree.ancestor_id, COUNT(DISTINCT rc.resource_id)
            FROM tree
            JOIN resource_categories rc ON rc.category_id = tree.id
            JOIN resources r ON r.id = rc.resource_id
            WHERE r.status = 'active'
            GROUP BY tree.ancestor_id
        """)
        rows = (await self._session.execute(sql, {"type": type_.value})).all()
        return {int(row[0]): int(row[1]) for row in rows}

    async def create(
        self, type_: ResourceType, parent_id: int | None, name: str, sort: int = 0
    ) -> Category:
        row = CategoryRow(
            type=type_.value, parent_id=parent_id, name=name.strip(), sort=sort
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _category_to_domain(row)

    async def update(
        self,
        category_id: int,
        *,
        name: str | None,
        parent_id: int | None,
        sort: int | None,
        update_parent: bool = False,
    ) -> Category | None:
        row = await self._session.get(CategoryRow, category_id)
        if row is None:
            return None
        if name is not None:
            row.name = name.strip()
        if update_parent:
            row.parent_id = parent_id
        if sort is not None:
            row.sort = sort
        await self._session.commit()
        await self._session.refresh(row)
        return _category_to_domain(row)

    async def delete(self, category_id: int) -> bool:
        row = await self._session.get(CategoryRow, category_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    async def has_children(self, category_id: int) -> bool:
        return bool(await self._session.scalar(
            select(func.count()).select_from(CategoryRow).where(
                CategoryRow.parent_id == category_id
            )
        ))

    async def has_resources(self, category_id: int) -> bool:
        return bool(await self._session.scalar(
            select(func.count()).select_from(ResourceCategoryRow).where(
                ResourceCategoryRow.category_id == category_id
            )
        ))

    async def name_exists(
        self, type_: ResourceType, parent_id: int | None, name: str, exclude_id: int | None = None
    ) -> bool:
        stmt = select(CategoryRow.id).where(
            CategoryRow.type == type_.value,
            CategoryRow.parent_id.is_(parent_id) if parent_id is None else CategoryRow.parent_id == parent_id,
            func.lower(CategoryRow.name) == name.strip().lower(),
        )
        if exclude_id is not None:
            stmt = stmt.where(CategoryRow.id != exclude_id)
        return (await self._session.execute(stmt)).first() is not None

    async def depth(self, category_id: int | None) -> int:
        """根为 1；None 为 0。"""
        depth = 0
        current = category_id
        seen: set[int] = set()
        while current is not None and current not in seen:
            seen.add(current)
            depth += 1
            row = await self._session.get(CategoryRow, current)
            current = row.parent_id if row is not None else None
        return depth

    async def subtree_height(self, category_id: int) -> int:
        """节点自身高度（叶子为 1）。"""
        rows = await self.list_all_rows()
        children: dict[int, list[int]] = {}
        for row in rows:
            if row.parent_id is not None:
                children.setdefault(row.parent_id, []).append(row.id)
        best = 1
        stack: list[tuple[int, int]] = [(category_id, 1)]
        seen: set[int] = set()
        while stack:
            current, height = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            best = max(best, height)
            for child in children.get(current, []):
                stack.append((child, height + 1))
        return best


class SavedViewRepository:
    """保存的时间线筛选器；无成员表。"""

    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _to_domain(row: SavedViewRow) -> SavedView:
        scope = row.type
        try:
            raw = json.loads(row.filters_json or "{}")
        except (ValueError, TypeError):
            raw = {}
        if "image" in raw or "video" in raw:
            try:
                filters = SavedViewFilters(**raw)
            except (ValueError, TypeError):
                filters = SavedViewFilters()
        else:
            legacy = [int(value) for value in raw.get("category_ids", []) if value is not None]
            filters = SavedViewFilters(
                image=CategoryRule(include=legacy if scope == "image" else []),
                video=CategoryRule(include=legacy if scope == "video" else []),
                tag_ids=[int(value) for value in raw.get("tag_ids", []) if value is not None],
                date_from=raw.get("date_from"),
                date_to=raw.get("date_to"),
                include_untimed=bool(raw.get("include_untimed", False)),
            )
        return SavedView(
            id=row.id,
            kind=row.kind,
            scope=scope,
            name=row.name,
            filters=filters,
            sort=row.sort,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def list(self, kind: str, scope: str | None = None) -> list[SavedView]:
        stmt = select(SavedViewRow).where(SavedViewRow.kind == kind)
        if scope:
            stmt = stmt.where(SavedViewRow.type == scope)
        rows = (await self._session.execute(
            stmt.order_by(SavedViewRow.updated_at.desc(), SavedViewRow.id.desc())
        )).scalars().all()
        return [self._to_domain(row) for row in rows]

    async def get(self, view_id: int) -> SavedView | None:
        row = await self._session.get(SavedViewRow, view_id)
        return self._to_domain(row) if row is not None else None

    async def create(
        self,
        *,
        kind: str,
        scope: str,
        name: str,
        filters: SavedViewFilters,
        sort: str,
    ) -> SavedView:
        now = db_now()
        row = SavedViewRow(
            kind=kind,
            type=scope,
            name=name.strip(),
            filters_json=filters.model_dump_json(),
            sort=sort,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_domain(row)

    async def update(
        self,
        view_id: int,
        *,
        scope: str | None = None,
        name: str | None,
        filters: SavedViewFilters | None,
        sort: str | None,
    ) -> SavedView | None:
        row = await self._session.get(SavedViewRow, view_id)
        if row is None:
            return None
        if scope is not None:
            row.type = scope
        if name is not None:
            row.name = name.strip()
        if filters is not None:
            row.filters_json = filters.model_dump_json()
        if sort is not None:
            row.sort = sort
        row.updated_at = db_now()
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_domain(row)

    async def delete(self, view_id: int) -> bool:
        row = await self._session.get(SavedViewRow, view_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    async def name_exists(
        self, kind: str, scope: str, name: str, exclude_id: int | None = None
    ) -> bool:
        stmt = select(SavedViewRow.id).where(
            SavedViewRow.kind == kind,
            SavedViewRow.type == scope,
            func.lower(SavedViewRow.name) == name.strip().lower(),
        )
        if exclude_id is not None:
            stmt = stmt.where(SavedViewRow.id != exclude_id)
        return (await self._session.execute(stmt)).first() is not None

    async def remove_category(self, category_id: int) -> int:
        """Remove a category id from include/exclude rules or legacy category_ids."""
        rows = (await self._session.execute(select(SavedViewRow))).scalars().all()
        changed = 0
        for row in rows:
            try:
                raw = json.loads(row.filters_json or "{}")
            except (ValueError, TypeError):
                continue
            touched = False
            for media_type in ("image", "video"):
                rule = raw.get(media_type)
                if not isinstance(rule, dict):
                    continue
                for field in ("include", "exclude"):
                    ids = rule.get(field)
                    if isinstance(ids, list) and category_id in ids:
                        rule[field] = [value for value in ids if int(value) != category_id]
                        touched = True
            legacy = raw.get("category_ids")
            if isinstance(legacy, list) and category_id in legacy:
                raw["category_ids"] = [value for value in legacy if int(value) != category_id]
                touched = True
            if touched:
                row.filters_json = json.dumps(raw, ensure_ascii=False)
                row.updated_at = db_now()
                changed += 1
        if changed:
            await self._session.commit()
        return changed




class TimelineNoteRepository:
    """日期备注 / 保存时间线备注。"""

    def __init__(self, session: AsyncSession):
        self._session = session

    def _to_domain(self, row: TimelineNoteRow) -> TimelineNote:
        return TimelineNote(
            id=row.id,
            scope=row.scope,
            date=row.date,
            saved_view_id=row.saved_view_id,
            title=row.title,
            body=row.body,
            location_name=row.location_name,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_date(self, date: str) -> TimelineNote | None:
        row = (await self._session.execute(
            select(TimelineNoteRow).where(
                TimelineNoteRow.scope == "date", TimelineNoteRow.date == date
            )
        )).scalars().first()
        return self._to_domain(row) if row is not None else None

    async def get_saved_view(self, saved_view_id: int) -> TimelineNote | None:
        row = (await self._session.execute(
            select(TimelineNoteRow).where(
                TimelineNoteRow.scope == "saved_view",
                TimelineNoteRow.saved_view_id == saved_view_id,
            )
        )).scalars().first()
        return self._to_domain(row) if row is not None else None

    async def list_dates(self, date_from: str | None, date_to: str | None) -> list[TimelineNote]:
        stmt = select(TimelineNoteRow).where(TimelineNoteRow.scope == "date")
        if date_from:
            stmt = stmt.where(TimelineNoteRow.date >= date_from[:10])
        if date_to:
            stmt = stmt.where(TimelineNoteRow.date <= date_to[:10])
        rows = (await self._session.execute(stmt.order_by(TimelineNoteRow.date))).scalars().all()
        return [self._to_domain(row) for row in rows]

    async def upsert_date(
        self, date: str, title: str, body: str | None, location_name: str | None
    ) -> TimelineNote:
        row = (await self._session.execute(
            select(TimelineNoteRow).where(
                TimelineNoteRow.scope == "date", TimelineNoteRow.date == date
            )
        )).scalars().first()
        if row is None:
            row = TimelineNoteRow(scope="date", date=date, title="")
            self._session.add(row)
        row.title = title
        row.body = body
        row.location_name = location_name
        row.updated_at = db_now()
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_domain(row)

    async def upsert_saved_view(
        self, saved_view_id: int, title: str, body: str | None, location_name: str | None
    ) -> TimelineNote:
        row = (await self._session.execute(
            select(TimelineNoteRow).where(
                TimelineNoteRow.scope == "saved_view",
                TimelineNoteRow.saved_view_id == saved_view_id,
            )
        )).scalars().first()
        if row is None:
            row = TimelineNoteRow(scope="saved_view", saved_view_id=saved_view_id, title="")
            self._session.add(row)
        row.title = title
        row.body = body
        row.location_name = location_name
        row.updated_at = db_now()
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_domain(row)

    async def delete_date(self, date: str) -> bool:
        row = (await self._session.execute(
            select(TimelineNoteRow).where(
                TimelineNoteRow.scope == "date", TimelineNoteRow.date == date
            )
        )).scalars().first()
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    async def delete_saved_view(self, saved_view_id: int) -> bool:
        row = (await self._session.execute(
            select(TimelineNoteRow).where(
                TimelineNoteRow.scope == "saved_view",
                TimelineNoteRow.saved_view_id == saved_view_id,
            )
        )).scalars().first()
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

from app.library.infrastructure.repositories_people import CharacterRepository, PersonRepository
