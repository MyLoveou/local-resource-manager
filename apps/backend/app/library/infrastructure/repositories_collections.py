"""Collection aggregate repository."""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.domain.media_types import FILE_ROLE_THUMBNAIL
from app.library.domain.models import Collection, Resource, ResourceStatus
from app.library.infrastructure.media_paths import file_content_url as _file_content_url
from app.library.infrastructure.orm import (
    CollectionItemRow,
    CollectionRow,
    FileRow,
    ResourceRow,
)
from app.library.infrastructure.repositories_common import _orm_to_resource
from app.library.infrastructure.repositories_resources import ResourceRepository
from app.shared.utils.time import db_now


class CollectionRepository:
    """合集仓储：CRUD + 成员增删排序。"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, title: str, description: str | None = None) -> Collection:
        row = CollectionRow(title=title.strip(), description=description)
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return Collection(id=row.id, title=row.title, description=row.description,
                          created_at=row.created_at, updated_at=row.updated_at)

    async def list(self) -> list[Collection]:
        rows = (await self._session.execute(
            select(CollectionRow).order_by(CollectionRow.updated_at.desc())
        )).scalars().all()
        ids = [row.id for row in rows]
        counts = await self._active_member_counts(ids)
        previews = await self._preview_thumbnails(ids)
        return [
            Collection(
                id=row.id,
                title=row.title,
                description=row.description,
                member_count=counts.get(row.id, 0),
                preview_thumbnails=previews.get(row.id, []),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    async def get(self, collection_id: int) -> Collection | None:
        row = await self._session.get(CollectionRow, collection_id)
        if row is None:
            return None
        counts = await self._active_member_counts([collection_id])
        previews = await self._preview_thumbnails([collection_id])
        return Collection(
            id=row.id,
            title=row.title,
            description=row.description,
            member_count=counts.get(collection_id, 0),
            preview_thumbnails=previews.get(collection_id, []),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def find_by_title(self, title: str) -> Collection | None:
        row = (await self._session.execute(
            select(CollectionRow).where(CollectionRow.title == title.strip()).limit(1)
        )).scalars().first()
        if row is None:
            return None
        return await self.get(row.id)

    async def rename(self, collection_id: int, title: str, description: str | None) -> Collection | None:
        row = await self._session.get(CollectionRow, collection_id)
        if row is None:
            return None
        row.title = title.strip()
        row.description = description
        row.updated_at = db_now()
        await self._session.commit()
        await self._session.refresh(row)
        return await self.get(row.id)

    async def delete(self, collection_id: int) -> bool:
        row = await self._session.get(CollectionRow, collection_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    async def add_item(self, collection_id: int, resource_id: int) -> bool:
        """加入成员；已存在则原位置保留（幂等成功）。"""
        existing = await self._session.get(CollectionItemRow, (collection_id, resource_id))
        if existing is not None:
            return True
        max_pos = await self._session.scalar(
            select(func.max(CollectionItemRow.position))
            .where(CollectionItemRow.collection_id == collection_id)
        )
        self._session.add(CollectionItemRow(
            collection_id=collection_id, resource_id=resource_id,
            position=int(max_pos or -1) + 1,
        ))
        await self._touch_collection(collection_id)
        await self._session.commit()
        return True

    async def add_items(self, collection_id: int, resource_ids: list[int]) -> tuple[int, int, int]:
        """批量加入：去重、跳过已存在/不存在；返回 (added, skipped, missing)。"""
        unique: list[int] = []
        seen: set[int] = set()
        for resource_id in resource_ids:
            if resource_id not in seen:
                seen.add(resource_id)
                unique.append(resource_id)
        if not unique:
            return 0, 0, 0

        member_ids = set((await self._session.scalars(
            select(CollectionItemRow.resource_id).where(
                CollectionItemRow.collection_id == collection_id,
                CollectionItemRow.resource_id.in_(unique),
            )
        )).all())
        known_ids = set((await self._session.scalars(
            select(ResourceRow.id).where(ResourceRow.id.in_(unique))
        )).all())
        max_pos = await self._session.scalar(
            select(func.max(CollectionItemRow.position))
            .where(CollectionItemRow.collection_id == collection_id)
        )
        next_pos = int(max_pos or -1) + 1
        added = skipped = missing = 0
        for resource_id in unique:
            if resource_id not in known_ids:
                missing += 1
                continue
            if resource_id in member_ids:
                skipped += 1
                continue
            self._session.add(CollectionItemRow(
                collection_id=collection_id, resource_id=resource_id,
                position=next_pos,
            ))
            next_pos += 1
            added += 1
        if added:
            await self._touch_collection(collection_id)
            await self._session.commit()
        return added, skipped, missing

    async def remove_item(self, collection_id: int, resource_id: int) -> bool:
        row = await self._session.get(CollectionItemRow, (collection_id, resource_id))
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.flush()
        await self._compact_positions(collection_id)
        await self._touch_collection(collection_id)
        await self._session.commit()
        return True

    async def members(self, collection_id: int) -> list[Resource]:
        rows = (await self._session.execute(
            select(ResourceRow)
            .join(CollectionItemRow, CollectionItemRow.resource_id == ResourceRow.id)
            .where(CollectionItemRow.collection_id == collection_id,
                   ResourceRow.status == ResourceStatus.ACTIVE.value)
            .order_by(CollectionItemRow.position)
        )).scalars().all()
        resources = [_orm_to_resource(row) for row in rows]
        await ResourceRepository(self._session).attach_categories(resources)
        return await self._attach_thumbnails(resources)

    async def member_ids(self, collection_id: int) -> list[int]:
        rows = (await self._session.execute(
            select(CollectionItemRow.resource_id)
            .join(ResourceRow, ResourceRow.id == CollectionItemRow.resource_id)
            .where(CollectionItemRow.collection_id == collection_id,
                   ResourceRow.status == ResourceStatus.ACTIVE.value)
            .order_by(CollectionItemRow.position)
        )).all()
        return [int(row[0]) for row in rows]

    async def move_item(self, collection_id: int, resource_id: int, direction: str) -> bool:
        """上移/下移一位。"""
        ids = await self.member_ids(collection_id)
        if resource_id not in ids or len(ids) < 2:
            return False
        index = ids.index(resource_id)
        target = index - 1 if direction == "up" else index + 1
        if target < 0 or target >= len(ids):
            return False
        ids[index], ids[target] = ids[target], ids[index]
        for position, rid in enumerate(ids):
            row = await self._session.get(CollectionItemRow, (collection_id, rid))
            if row is not None:
                row.position = position
        await self._touch_collection(collection_id)
        await self._session.commit()
        return True

    async def collections_of(self, resource_id: int) -> list[Collection]:
        rows = (await self._session.execute(
            select(CollectionRow)
            .join(CollectionItemRow, CollectionItemRow.collection_id == CollectionRow.id)
            .where(CollectionItemRow.resource_id == resource_id)
            .order_by(CollectionRow.updated_at.desc())
        )).scalars().all()
        return [Collection(id=row.id, title=row.title, description=row.description,
                           created_at=row.created_at, updated_at=row.updated_at)
                for row in rows]

    async def for_character(self, character_id: int) -> list[Collection]:
        collection_ids = select(CollectionItemRow.collection_id).join(
            ResourceCharacterRow,
            ResourceCharacterRow.resource_id == CollectionItemRow.resource_id,
        ).where(ResourceCharacterRow.character_id == character_id)
        rows = (await self._session.execute(
            select(CollectionRow)
            .where(CollectionRow.id.in_(collection_ids))
            .order_by(CollectionRow.updated_at.desc())
        )).scalars().all()
        ids = [row.id for row in rows]
        counts = await self._active_member_counts(ids)
        previews = await self._preview_thumbnails(ids)
        return [
            Collection(
                id=row.id,
                title=row.title,
                description=row.description,
                member_count=counts.get(row.id, 0),
                preview_thumbnails=previews.get(row.id, []),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    async def _active_member_counts(self, collection_ids: list[int]) -> dict[int, int]:
        if not collection_ids:
            return {}
        rows = (await self._session.execute(
            select(CollectionItemRow.collection_id, func.count())
            .join(ResourceRow, ResourceRow.id == CollectionItemRow.resource_id)
            .where(
                CollectionItemRow.collection_id.in_(collection_ids),
                ResourceRow.status == ResourceStatus.ACTIVE.value,
            )
            .group_by(CollectionItemRow.collection_id)
        )).all()
        return {int(row[0]): int(row[1]) for row in rows}

    async def _preview_thumbnails(self, collection_ids: list[int]) -> dict[int, list[str]]:
        if not collection_ids:
            return {}
        ranked = (
            select(
                CollectionItemRow.collection_id.label("collection_id"),
                FileRow.resource_id.label("resource_id"),
                FileRow.id.label("file_id"),
                func.row_number().over(
                    partition_by=CollectionItemRow.collection_id,
                    order_by=(CollectionItemRow.position, CollectionItemRow.resource_id),
                ).label("rn"),
            )
            .join(FileRow, FileRow.resource_id == CollectionItemRow.resource_id)
            .join(ResourceRow, ResourceRow.id == CollectionItemRow.resource_id)
            .where(
                CollectionItemRow.collection_id.in_(collection_ids),
                FileRow.role == FILE_ROLE_THUMBNAIL,
                ResourceRow.status == ResourceStatus.ACTIVE.value,
            )
            .subquery()
        )
        rows = (await self._session.execute(
            select(ranked.c.collection_id, ranked.c.resource_id, ranked.c.file_id)
            .where(ranked.c.rn <= 3)
            .order_by(ranked.c.collection_id, ranked.c.rn)
        )).all()
        out: dict[int, list[str]] = {}
        for collection_id, resource_id, file_id in rows:
            out.setdefault(int(collection_id), []).append(
                _file_content_url(int(resource_id), int(file_id))
            )
        return out

    async def _active_member_count(self, collection_id: int) -> int:
        value = await self._session.scalar(
            select(func.count())
            .select_from(CollectionItemRow)
            .join(ResourceRow, ResourceRow.id == CollectionItemRow.resource_id)
            .where(CollectionItemRow.collection_id == collection_id,
                   ResourceRow.status == ResourceStatus.ACTIVE.value)
        )
        return int(value or 0)

    async def _compact_positions(self, collection_id: int) -> None:
        ids = [int(row[0]) for row in (await self._session.execute(
            select(CollectionItemRow.resource_id)
            .where(CollectionItemRow.collection_id == collection_id)
            .order_by(CollectionItemRow.position)
        )).all()]
        for position, rid in enumerate(ids):
            row = await self._session.get(CollectionItemRow, (collection_id, rid))
            if row is not None:
                row.position = position

    async def _touch_collection(self, collection_id: int) -> None:
        row = await self._session.get(CollectionRow, collection_id)
        if row is not None:
            row.updated_at = db_now()

    async def _attach_thumbnails(self, resources: list[Resource]) -> list[Resource]:
        return await ResourceRepository(self._session).attach_listed(resources)
