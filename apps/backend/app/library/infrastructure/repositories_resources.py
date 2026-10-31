"""Resource aggregate repository: CRUD, filters and timeline reads."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from sqlalchemy import and_, asc, delete, desc, exists, func, literal, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.library.domain.media_types import (
    FILE_ROLE_PAGE,
    FILE_ROLE_PRIMARY,
    FILE_ROLE_THUMBNAIL,
    is_series_type,
)
from app.library.domain.models import (
    Category,
    CategoryRule,
    Collection,
    Character,
    CharacterBrief,
    Person,
    PersonBrief,
    Resource,
    ResourceFile,
    ResourceStatus,
    ResourceTodo,
    ResourceType,
    SavedView,
    SavedViewFilters,
    SeriesEpisode,
    SeriesExtra,
    SeriesSeason,
    StorageKind,
    Tag,
    TimelineNote,
    Work,
    WorkCatalog,
)
from app.library.infrastructure.media_paths import (
    episode_cover_url,
    file_content_url as _file_content_url,
    media_path as _media_path,
)
from app.library.infrastructure.repositories_series import attach_series_tree
from app.shared.media_auth import unsigned_media_path
from app.library.infrastructure.orm import (
    CategoryRow,
    CharacterAliasRow,
    CharacterRow,
    CollectionItemRow,
    CollectionRow,
    EpisodeRow,
    ExtraRow,
    FileRow,
    PersonAliasRow,
    PersonRow,
    ResourceCategoryRow,
    ResourceCharacterRow,
    ResourcePersonRow,
    ResourceRow,
    ResourceTagRow,
    ResourceTodoRow,
    SavedViewRow,
    SeasonRow,
    SubtitleTrackRow,
    TagRow,
    TimelineNoteRow,
    WorkRow,
)
from app.library.infrastructure.repositories_common import (
    _category_to_domain,
    _dump_extra,
    _file_to_domain,
    _orm_to_resource,
)
from app.scrape.infrastructure.orm import CandidateRow, ScrapeJobRow
from app.shared.utils.time import db_now, db_ts


class ResourceRepository:
    """资源仓储：创建/查询/统计。"""

    def __init__(self, session: AsyncSession):
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def attach_listed(self, resources: list[Resource]) -> list[Resource]:
        await self.attach_categories(resources)
        return await self._attach_thumbnail_paths(resources)

    async def attach_categories(self, resources: list[Resource]) -> list[Resource]:
        """批量附加分类，避免列表逐条查询。"""
        ids = [resource.id for resource in resources if resource.id is not None]
        if not ids:
            return resources
        rows = (await self._session.execute(
            select(ResourceCategoryRow.resource_id, CategoryRow)
            .join(CategoryRow, CategoryRow.id == ResourceCategoryRow.category_id)
            .where(ResourceCategoryRow.resource_id.in_(ids))
            .order_by(CategoryRow.type, CategoryRow.sort, CategoryRow.name)
        )).all()
        by_resource: dict[int, list[Category]] = {}
        for resource_id, category in rows:
            by_resource.setdefault(int(resource_id), []).append(_category_to_domain(category))
        for resource in resources:
            if resource.id is not None:
                resource.categories = by_resource.get(resource.id, [])
        return resources

    async def attach_characters(self, resources: list[Resource]) -> list[Resource]:
        """Attach lightweight character briefs for detail panels."""
        ids = [resource.id for resource in resources if resource.id is not None]
        if not ids:
            return resources
        rows = (await self._session.execute(
            select(ResourceCharacterRow.resource_id, CharacterRow, WorkRow.name)
            .join(CharacterRow, CharacterRow.id == ResourceCharacterRow.character_id)
            .outerjoin(WorkRow, WorkRow.id == CharacterRow.work_id)
            .where(ResourceCharacterRow.resource_id.in_(ids))
            .order_by(CharacterRow.name)
        )).all()
        by_resource: dict[int, list[CharacterBrief]] = {}
        for resource_id, character, work_name in rows:
            by_resource.setdefault(int(resource_id), []).append(
                CharacterBrief(
                    id=character.id,
                    name=character.name,
                    work_id=character.work_id,
                    work_name=work_name,
                )
            )
        for resource in resources:
            if resource.id is not None:
                resource.characters = by_resource.get(resource.id, [])
        return resources

    async def attach_persons(self, resources: list[Resource]) -> list[Resource]:
        """Attach lightweight person briefs for detail panels."""
        ids = [resource.id for resource in resources if resource.id is not None]
        if not ids:
            return resources
        rows = (await self._session.execute(
            select(ResourcePersonRow.resource_id, PersonRow)
            .join(PersonRow, PersonRow.id == ResourcePersonRow.person_id)
            .where(ResourcePersonRow.resource_id.in_(ids))
            .order_by(PersonRow.name)
        )).all()
        by_resource: dict[int, list[PersonBrief]] = {}
        for resource_id, person in rows:
            by_resource.setdefault(int(resource_id), []).append(
                PersonBrief(id=person.id, name=person.name)
            )
        for resource in resources:
            if resource.id is not None:
                resource.persons = by_resource.get(resource.id, [])
        return resources

    async def create(self, resource: Resource, *, commit: bool = True) -> Resource:
        """插入并返回带 id 的完整实体。"""
        ts = db_now()
        row = ResourceRow(
            type=resource.type.value,
            storage_kind=resource.storage_kind.value,
            title=resource.title,
            description=resource.description,
            synopsis=resource.synopsis,
            author=resource.author,
            rating=resource.rating,
            cover_path=unsigned_media_path(resource.cover_path),
            status=resource.status.value,
            extra=_dump_extra(resource),
            timeline_visible=(
                None if resource.timeline_visible is None else int(resource.timeline_visible)
            ),
            map_visible=(
                None if resource.map_visible is None else int(resource.map_visible)
            ),
            created_at=ts,
            updated_at=ts,
        )
        self._session.add(row)
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()
        await self._session.refresh(row)
        return _orm_to_resource(row)

    def _apply_resource(self, row: ResourceRow, resource: Resource) -> None:
        row.type = resource.type.value
        row.storage_kind = resource.storage_kind.value
        row.title = resource.title
        row.description = resource.description
        row.synopsis = resource.synopsis
        row.author = resource.author
        row.rating = resource.rating
        row.cover_path = unsigned_media_path(resource.cover_path)
        row.status = resource.status.value
        row.deleted_at = db_ts(resource.deleted_at)
        row.last_scraped_at = db_ts(resource.last_scraped_at)
        row.scraped_source = resource.scraped_source
        row.extra = _dump_extra(resource)
        row.timeline_visible = (
            None if resource.timeline_visible is None else int(resource.timeline_visible)
        )
        row.map_visible = (
            None if resource.map_visible is None else int(resource.map_visible)
        )
        row.updated_at = db_now()

    async def update(self, resource_id: int, resource: Resource, *, commit: bool = True) -> Resource | None:
        """按路径 id 更新可变字段；不存在则 None。"""
        row = await self._session.get(ResourceRow, resource_id)
        if row is None:
            return None
        self._apply_resource(row, resource)
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()
        await self._session.refresh(row)
        return await self._hydrate(row)

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def trash(self, resource_id: int) -> Resource | None:
        """软删：已在回收站则原样返回。"""
        existing = await self.get(resource_id)
        if existing is None:
            return None
        if existing.is_trashed:
            return existing
        existing.to_trash()
        return await self.update(resource_id, existing)

    async def restore(self, resource_id: int) -> Resource | None:
        """从回收站恢复；不存在则 None。非 trashed 由领域模型抛 InvalidStateError。"""
        existing = await self.get(resource_id)
        if existing is None:
            return None
        existing.restore()
        return await self.update(resource_id, existing)

    async def delete_row(self, resource_id: int) -> bool:
        """硬删除资源行（CASCADE files/todos/tags）。"""
        row = await self._session.get(ResourceRow, resource_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    async def _hydrate(self, row: ResourceRow) -> Resource:
        """详情：分类/标签/文件/待办一次加载（同 session 仍串行查询，避免 N 次 get）。"""
        resource = _orm_to_resource(row)
        tag_stmt = (
            select(TagRow)
            .join(ResourceTagRow, ResourceTagRow.tag_id == TagRow.id)
            .where(ResourceTagRow.resource_id == row.id)
            .order_by(TagRow.name)
        )
        file_stmt = select(FileRow).where(FileRow.resource_id == row.id).order_by(FileRow.id)
        todo_stmt = (
            select(ResourceTodoRow)
            .where(ResourceTodoRow.resource_id == row.id)
            .order_by(ResourceTodoRow.sort, ResourceTodoRow.id)
        )
        tags = (await self._session.execute(tag_stmt)).scalars().all()
        files = (await self._session.execute(file_stmt)).scalars().all()
        todos = (await self._session.execute(todo_stmt)).scalars().all()
        await self.attach_categories([resource])
        await self.attach_characters([resource])
        await self.attach_persons([resource])
        resource.tags = [Tag(id=t.id, name=t.name) for t in tags]
        resource.files = [_file_to_domain(f) for f in files]
        resource.todos = [
            ResourceTodo(
                id=t.id,
                resource_id=t.resource_id,
                content=t.content,
                done=bool(t.done),
                sort=t.sort,
                created_at=t.created_at,
            )
            for t in todos
        ]
        self._apply_thumbnail_path(resource)
        await self._attach_series_tree(resource)
        await self.attach_scrape_pending([resource])
        return resource

    async def _attach_series_tree(self, resource: Resource) -> None:
        """详情才装季集；列表不走 hydrate。"""
        if resource.id is None or not is_series_type(resource.type):
            return
        await attach_series_tree(self._session, resource)

    def _apply_thumbnail_path(self, resource: Resource) -> None:
        """从已加载 files 填 thumbnail_path，不改 cover_path。"""
        if resource.id is None:
            return
        thumb = next((f for f in resource.files if f.role == FILE_ROLE_THUMBNAIL and f.id is not None), None)
        if thumb is None:
            resource.thumbnail_path = None
            return
        resource.thumbnail_path = _file_content_url(resource.id, thumb.id)

    async def attach_primary_files(self, resources: list[Resource]) -> list[Resource]:
        """列表轻量补 primary 文件（宽高/时长/拍摄时间），供 Justified 布局使用。"""
        ids = [r.id for r in resources if r.id is not None]
        if not ids:
            return resources
        stmt = select(FileRow).where(
            FileRow.resource_id.in_(ids), FileRow.role == FILE_ROLE_PRIMARY
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        by_rid = {row.resource_id: row for row in rows}
        for resource in resources:
            if resource.id is None:
                continue
            file_row = by_rid.get(resource.id)
            resource.files = [_file_to_domain(file_row)] if file_row is not None else []
        return resources

    async def _attach_thumbnail_paths(self, resources: list[Resource]) -> list[Resource]:
        ids = [r.id for r in resources if r.id is not None]
        if not ids:
            return resources
        stmt = select(FileRow).where(FileRow.resource_id.in_(ids), FileRow.role == FILE_ROLE_THUMBNAIL)
        rows = (await self._session.execute(stmt)).scalars().all()
        by_rid = {row.resource_id: row for row in rows}
        for resource in resources:
            if resource.id is None:
                continue
            file_row = by_rid.get(resource.id)
            if file_row is None:
                continue
            resource.thumbnail_path = _file_content_url(resource.id, file_row.id)
        return resources

    async def get(self, resource_id: int) -> Resource | None:
        row = await self._session.get(ResourceRow, resource_id)
        if row is None:
            return None
        return await self._hydrate(row)

    def _file_agg(self, expr):
        return select(expr).where(FileRow.resource_id == ResourceRow.id).correlate(ResourceRow).scalar_subquery()

    def _sort_expr(self, sort: str):
        area = func.max(FileRow.width * FileRow.height)
        mapping = {
            "createdAt": ResourceRow.created_at,
            "updatedAt": ResourceRow.updated_at,
            "title": ResourceRow.title,
            "rating": ResourceRow.rating,
            "size": self._file_agg(func.sum(FileRow.size)),
            "width": self._file_agg(func.max(FileRow.width)),
            "height": self._file_agg(func.max(FileRow.height)),
            "duration": self._file_agg(func.max(FileRow.duration)),
            "bitrate": self._file_agg(func.max(FileRow.bitrate)),
            "takenAt": self._file_agg(func.max(FileRow.exif_taken_at)),
            "pixelArea": select(area)
            .where(
                FileRow.resource_id == ResourceRow.id,
                FileRow.width.is_not(None),
                FileRow.height.is_not(None),
            )
            .correlate(ResourceRow)
            .scalar_subquery(),
            "resolution": select(area)
            .where(
                FileRow.resource_id == ResourceRow.id,
                FileRow.width.is_not(None),
                FileRow.height.is_not(None),
            )
            .correlate(ResourceRow)
            .scalar_subquery(),
            "pageCount": select(func.count())
            .where(FileRow.resource_id == ResourceRow.id, FileRow.role == FILE_ROLE_PAGE)
            .correlate(ResourceRow)
            .scalar_subquery(),
            "episodeCount": (
                select(func.count())
                .select_from(EpisodeRow)
                .join(SeasonRow, EpisodeRow.season_id == SeasonRow.id)
                .where(SeasonRow.resource_id == ResourceRow.id)
                .correlate(ResourceRow)
                .scalar_subquery()
            ),
        }
        return mapping.get(sort, ResourceRow.created_at)

    def _search_filter(self, stmt, q: str | None, tag_ids: list[int] | None):
        from app.library.application.list_query import CLARITY_PX, like_pattern

        if q:
            pattern = like_pattern(q)
            file_conds = [
                func.lower(FileRow.path).like(pattern, escape="\\"),
                func.lower(func.coalesce(FileRow.format, "")).like(pattern, escape="\\"),
            ]
            if q.isdigit() and int(q) in CLARITY_PX:
                file_conds.append(or_(FileRow.width == int(q), FileRow.height == int(q)))
            file_hit = exists(
                select(FileRow.id).where(FileRow.resource_id == ResourceRow.id, or_(*file_conds))
            )
            tag_hit = exists(
                select(ResourceTagRow.resource_id)
                .join(TagRow, TagRow.id == ResourceTagRow.tag_id)
                .where(
                    ResourceTagRow.resource_id == ResourceRow.id,
                    func.lower(TagRow.name).like(pattern, escape="\\"),
                )
            )
            cat_hit = exists(
                select(ResourceCategoryRow.resource_id)
                .join(CategoryRow, CategoryRow.id == ResourceCategoryRow.category_id)
                .where(
                    ResourceCategoryRow.resource_id == ResourceRow.id,
                    func.lower(CategoryRow.name).like(pattern, escape="\\"),
                )
            )
            stmt = stmt.where(
                or_(
                    func.lower(ResourceRow.title).like(pattern, escape="\\"),
                    func.lower(func.coalesce(ResourceRow.author, "")).like(pattern, escape="\\"),
                    func.lower(func.coalesce(ResourceRow.description, "")).like(pattern, escape="\\"),
                    func.lower(func.coalesce(ResourceRow.synopsis, "")).like(pattern, escape="\\"),
                    cat_hit,
                    tag_hit,
                    file_hit,
                )
            )
        for tag_id in tag_ids or []:
            stmt = stmt.where(
                exists(
                    select(ResourceTagRow.resource_id).where(
                        ResourceTagRow.resource_id == ResourceRow.id,
                        ResourceTagRow.tag_id == tag_id,
                    )
                )
            )
        return stmt

    def _keyset_clause(self, sort_expr, order: str, after_key: str, after_id: int):
        from app.library.application.list_query import NULL_CURSOR

        is_desc = order == "desc"
        id_cmp = ResourceRow.id < after_id if is_desc else ResourceRow.id > after_id
        if after_key == NULL_CURSOR:
            return and_(sort_expr.is_(None), id_cmp)
        value_cmp = sort_expr < after_key if is_desc else sort_expr > after_key
        same = and_(sort_expr == after_key, id_cmp)
        if is_desc:
            return or_(and_(sort_expr.is_not(None), or_(value_cmp, same)), sort_expr.is_(None))
        return or_(and_(sort_expr.is_not(None), or_(value_cmp, same)), sort_expr.is_(None))

    def _taken_date_exists(self, date_value: str | None):
        conditions = [
            FileRow.resource_id == ResourceRow.id,
            FileRow.role == FILE_ROLE_PRIMARY,
        ]
        if date_value is None:
            conditions.append(FileRow.exif_taken_at.is_not(None))
        else:
            conditions.append(func.substr(FileRow.exif_taken_at, 1, 10) == date_value)
        return exists(select(FileRow.id).where(*conditions))

    def _timeline_visible_clause(self, visible: bool):
        has_taken = self._taken_date_exists(None)
        if visible:
            return or_(
                ResourceRow.timeline_visible == 1,
                and_(ResourceRow.timeline_visible.is_(None), has_taken),
            )
        return or_(
            ResourceRow.timeline_visible == 0,
            and_(ResourceRow.timeline_visible.is_(None), ~has_taken),
        )

    def _map_visible_clause(self, visible: bool):
        if visible:
            return ResourceRow.map_visible.is_not(0)
        return ResourceRow.map_visible == 0

    def _map_only_clause(self):
        return exists(
            select(FileRow.id).where(
                FileRow.resource_id == ResourceRow.id,
                FileRow.role == FILE_ROLE_PRIMARY,
                FileRow.exif_lat.is_not(None),
                FileRow.exif_lng.is_not(None),
            )
        )

    def _filter(
        self,
        stmt,
        type_: ResourceType | None,
        status: ResourceStatus | None,
        q: str | None = None,
        tag_ids: list[int] | None = None,
        category_id: int | None = None,
        exclude_collected: bool = False,
        taken_date: str | None = None,
        untimed: bool = False,
        timeline_visible: bool | None = None,
        timeline_media: bool = False,
        category_ids: list[int] | None = None,
        uncategorized: bool = False,
        exclude_category_ids: list[int] | None = None,
        map_visible: bool | None = None,
        map_only: bool = False,
        character_ids: list[int] | None = None,
        person_ids: list[int] | None = None,
    ):
        if type_ is not None:
            stmt = stmt.where(ResourceRow.type == type_.value)
        if timeline_media:
            stmt = stmt.where(
                ResourceRow.type.in_((ResourceType.IMAGE.value, ResourceType.VIDEO.value))
            )
        if status is not None:
            stmt = stmt.where(ResourceRow.status == status.value)
        if category_id is not None:
            stmt = stmt.where(
                ResourceRow.id.in_(
                    select(ResourceCategoryRow.resource_id).where(
                        ResourceCategoryRow.category_id == category_id
                    )
                )
            )
        if category_ids:
            stmt = stmt.where(
                ResourceRow.id.in_(
                    select(ResourceCategoryRow.resource_id).where(
                        ResourceCategoryRow.category_id.in_(category_ids)
                    )
                )
            )
        if exclude_category_ids:
            stmt = stmt.where(
                ResourceRow.id.not_in(
                    select(ResourceCategoryRow.resource_id).where(
                        ResourceCategoryRow.category_id.in_(exclude_category_ids)
                    )
                )
            )
        if uncategorized:
            stmt = stmt.where(
                ~exists(
                    select(ResourceCategoryRow.resource_id).where(
                        ResourceCategoryRow.resource_id == ResourceRow.id
                    )
                )
            )
        if exclude_collected:
            stmt = stmt.where(
                ResourceRow.id.not_in(select(CollectionItemRow.resource_id))
            )
        if taken_date is not None:
            stmt = stmt.where(self._taken_date_exists(taken_date))
        if untimed:
            stmt = stmt.where(~self._taken_date_exists(None))
        if timeline_visible is not None:
            stmt = stmt.where(self._timeline_visible_clause(timeline_visible))
        if map_visible is not None:
            stmt = stmt.where(self._map_visible_clause(map_visible))
        if map_only:
            stmt = stmt.where(self._map_only_clause())
        if character_ids:
            stmt = stmt.where(
                exists(
                    select(ResourceCharacterRow.resource_id).where(
                        ResourceCharacterRow.resource_id == ResourceRow.id,
                        ResourceCharacterRow.character_id.in_(character_ids),
                    )
                )
            )
        if person_ids:
            stmt = stmt.where(
                exists(
                    select(ResourcePersonRow.resource_id).where(
                        ResourcePersonRow.resource_id == ResourceRow.id,
                        ResourcePersonRow.person_id.in_(person_ids),
                    )
                )
            )
        return self._search_filter(stmt, q, tag_ids)

    async def count(
        self,
        type_: ResourceType | None = None,
        status: ResourceStatus | None = None,
        q: str | None = None,
        tag_ids: list[int] | None = None,
        category_id: int | None = None,
        exclude_collected: bool = False,
        taken_date: str | None = None,
        untimed: bool = False,
        timeline_visible: bool | None = None,
        timeline_media: bool = False,
        category_ids: list[int] | None = None,
        uncategorized: bool = False,
        map_visible: bool | None = None,
        map_only: bool = False,
        character_ids: list[int] | None = None,
        person_ids: list[int] | None = None,
    ) -> int:
        """按 list 筛选条件统计资源数量。"""
        stmt = self._filter(
            select(func.count()).select_from(ResourceRow),
            type_,
            status,
            q,
            tag_ids,
            category_id,
            exclude_collected,
            taken_date,
            untimed,
            timeline_visible,
            timeline_media,
            category_ids,
            uncategorized,
            None,
            map_visible,
            map_only,
            character_ids,
            person_ids,
        )
        total = await self._session.scalar(stmt)
        return int(total or 0)

    async def list(
        self,
        type_: ResourceType | None = None,
        status: ResourceStatus | None = None,
        limit: int = 50,
        offset: int = 0,
        order: str = "desc",
        *,
        sort: str = "createdAt",
        q: str | None = None,
        tag_ids: list[int] | None = None,
        category_id: int | None = None,
        after_key: str | None = None,
        after_created_at: str | None = None,
        after_id: int | None = None,
        exclude_collected: bool = False,
        taken_date: str | None = None,
        untimed: bool = False,
        timeline_visible: bool | None = None,
        timeline_media: bool = False,
        category_ids: list[int] | None = None,
        uncategorized: bool = False,
        map_visible: bool | None = None,
        map_only: bool = False,
        character_ids: list[int] | None = None,
        person_ids: list[int] | None = None,
    ) -> list[Resource]:
        resources, _keys = await self.list_with_sort_keys(
            type_,
            status,
            limit,
            offset,
            order,
            sort=sort,
            q=q,
            tag_ids=tag_ids,
            category_id=category_id,
            after_key=after_key,
            after_created_at=after_created_at,
            after_id=after_id,
            exclude_collected=exclude_collected,
            taken_date=taken_date,
            untimed=untimed,
            timeline_visible=timeline_visible,
            timeline_media=timeline_media,
            category_ids=category_ids,
            uncategorized=uncategorized,
            map_visible=map_visible,
            map_only=map_only,
            character_ids=character_ids,
            person_ids=person_ids,
        )
        return resources

    async def list_with_sort_keys(
        self,
        type_: ResourceType | None = None,
        status: ResourceStatus | None = None,
        limit: int = 50,
        offset: int = 0,
        order: str = "desc",
        *,
        sort: str = "createdAt",
        q: str | None = None,
        tag_ids: list[int] | None = None,
        category_id: int | None = None,
        after_key: str | None = None,
        after_created_at: str | None = None,
        after_id: int | None = None,
        exclude_collected: bool = False,
        taken_date: str | None = None,
        untimed: bool = False,
        timeline_visible: bool | None = None,
        timeline_media: bool = False,
        category_ids: list[int] | None = None,
        uncategorized: bool = False,
        map_visible: bool | None = None,
        map_only: bool = False,
        character_ids: list[int] | None = None,
        person_ids: list[int] | None = None,
    ) -> tuple[list[Resource], list[str]]:
        from app.library.application.list_query import serialize_sort_value

        sort_expr = self._sort_expr(sort)
        stmt = self._filter(
            select(ResourceRow, sort_expr.label("sort_value")),
            type_, status, q, tag_ids, category_id, exclude_collected,
            taken_date, untimed, timeline_visible, timeline_media,
            category_ids, uncategorized, None, map_visible, map_only, character_ids, person_ids,
        )
        cursor_key = after_key
        if cursor_key is None and after_created_at is not None and sort == "createdAt":
            cursor_key = after_created_at
        stmt = stmt.order_by(sort_expr.is_(None), desc(sort_expr) if order == "desc" else asc(sort_expr), desc(ResourceRow.id) if order == "desc" else asc(ResourceRow.id))
        if cursor_key is not None and after_id is not None:
            stmt = stmt.where(self._keyset_clause(sort_expr, order, cursor_key, after_id)).limit(limit)
        else:
            stmt = stmt.limit(limit).offset(offset)
        rows = (await self._session.execute(stmt)).all()
        resources = await self._attach_thumbnail_paths([_orm_to_resource(row[0]) for row in rows])
        await self.attach_categories(resources)
        await self.attach_scrape_pending(resources)
        await self.attach_primary_files(resources)
        keys = [serialize_sort_value(row[1]) for row in rows]
        return resources, keys

    async def ids_missing_thumbnail(self) -> list[int]:
        """有资源行但没有 thumbnail 文件行的 id（卫生脚本）。"""
        thumb_ids = select(FileRow.resource_id).where(FileRow.role == FILE_ROLE_THUMBNAIL)
        stmt = select(ResourceRow.id).where(ResourceRow.id.not_in(thumb_ids))
        rows = (await self._session.execute(stmt)).all()
        return [int(r[0]) for r in rows]

    async def list_resource_ids(self) -> list[int]:
        rows = (await self._session.execute(select(ResourceRow.id))).all()
        return [int(r[0]) for r in rows]

    async def create_many(self, resources: list[Resource]) -> int:
        """批量插入（演示 seed），一次提交。"""
        ts = db_now()
        rows = [
            ResourceRow(
                type=r.type.value,
                title=r.title,
                description=r.description,
                synopsis=r.synopsis,
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

    async def file_exists_by_sha256(self, sha256: str) -> bool:
        stmt = select(FileRow.id).where(FileRow.sha256 == sha256).limit(1)
        return (await self._session.scalar(stmt)) is not None

    async def resource_id_by_sha256(self, sha256: str) -> int | None:
        stmt = select(FileRow.resource_id).where(FileRow.sha256 == sha256).limit(1)
        value = await self._session.scalar(stmt)
        return int(value) if value is not None else None

    async def file_exists_by_path(self, path: str) -> bool:
        """路径去重（indexed 启动文件）。"""
        stmt = select(FileRow.id).where(FileRow.path == path).limit(1)
        return (await self._session.scalar(stmt)) is not None

    async def find_by_import_source(self, source_path: str) -> Resource | None:
        """按导入源路径找既有资源（监视番剧增量入库用：extra.importSourcePath）。"""
        stmt = (
            select(ResourceRow)
            .where(func.json_extract(ResourceRow.extra, "$.importSourcePath") == source_path)
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalars().first()
        return _orm_to_resource(row) if row else None

    async def get_season(self, resource_id: int, season_number: int) -> SeasonRow | None:
        stmt = (
            select(SeasonRow)
            .where(SeasonRow.resource_id == resource_id, SeasonRow.season_number == season_number)
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalars().first()

    async def get_episode(self, season_id: int, episode_number: int) -> EpisodeRow | None:
        stmt = (
            select(EpisodeRow)
            .where(EpisodeRow.season_id == season_id, EpisodeRow.episode_number == episode_number)
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalars().first()

    async def max_episode_number(self, season_id: int) -> int:
        stmt = select(func.max(EpisodeRow.episode_number)).where(EpisodeRow.season_id == season_id)
        value = await self._session.scalar(stmt)
        return int(value) if value is not None else 0

    async def list_extras(self, resource_id: int) -> list[ExtraRow]:
        stmt = select(ExtraRow).where(ExtraRow.resource_id == resource_id)
        return list((await self._session.execute(stmt)).scalars().all())

    async def add_file(
        self,
        resource_id: int,
        *,
        path: str,
        sha256: str | None,
        size: int | None,
        format_: str | None,
        role: str,
        duration: float | None = None,
        width: int | None = None,
        height: int | None = None,
        codec: str | None = None,
        fps: float | None = None,
        bitrate: int | None = None,
        exif_taken_at: str | None = None,
        exif_lat: float | None = None,
        exif_lng: float | None = None,
        exif_camera: str | None = None,
        exif_lens: str | None = None,
        exif_iso: int | None = None,
        exif_aperture: str | None = None,
        exif_shutter: str | None = None,
        commit: bool = True,
    ) -> FileRow:
        """写入库内文件行。"""
        ts = db_now()
        row = FileRow(
            resource_id=resource_id,
            path=path,
            sha256=sha256,
            size=size,
            format=format_,
            role=role,
            duration=duration,
            width=width,
            height=height,
            codec=codec,
            fps=fps,
            bitrate=bitrate,
            exif_taken_at=exif_taken_at,
            exif_lat=exif_lat,
            exif_lng=exif_lng,
            exif_camera=exif_camera,
            exif_lens=exif_lens,
            exif_iso=exif_iso,
            exif_aperture=exif_aperture,
            exif_shutter=exif_shutter,
            created_at=ts,
        )
        self._session.add(row)
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()
        await self._session.refresh(row)
        return row

    async def add_season(
        self,
        resource_id: int,
        season_number: int,
        *,
        title: str | None = None,
        sort_index: int = 0,
        commit: bool = True,
    ) -> SeasonRow:
        """写入一季。"""
        row = SeasonRow(
            resource_id=resource_id,
            season_number=season_number,
            title=title,
            sort_index=sort_index,
        )
        self._session.add(row)
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()
        await self._session.refresh(row)
        return row

    async def add_episode(
        self,
        season_id: int,
        file_id: int,
        episode_number: int,
        *,
        title: str | None = None,
        sort_index: int = 0,
        commit: bool = True,
    ) -> EpisodeRow:
        """写入一集。"""
        row = EpisodeRow(
            season_id=season_id,
            file_id=file_id,
            episode_number=episode_number,
            title=title,
            sort_index=sort_index,
            status="active",
        )
        self._session.add(row)
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()
        await self._session.refresh(row)
        return row

    async def add_extra(
        self,
        resource_id: int,
        file_id: int,
        *,
        title: str,
        sort_index: int = 0,
        commit: bool = True,
    ) -> ExtraRow:
        """写入特典。"""
        row = ExtraRow(
            resource_id=resource_id,
            file_id=file_id,
            title=title,
            sort_index=sort_index,
            status="active",
        )
        self._session.add(row)
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()
        await self._session.refresh(row)
        return row

    async def update_file_stat(
        self,
        file_id: int,
        *,
        path: str,
        size: int | None,
        format_: str | None,
        commit: bool = True,
    ) -> FileRow | None:
        """覆盖同角色文件时更新路径与体积，不插新行。"""
        row = await self._session.get(FileRow, file_id)
        if row is None:
            return None
        row.path = path
        row.size = size
        row.format = format_
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()
        await self._session.refresh(row)
        return row

    async def update_file_exif_taken_at(
        self,
        file_id: int,
        value: str | None,
        *,
        commit: bool = True,
    ) -> FileRow | None:
        row = await self._session.get(FileRow, file_id)
        if row is None:
            return None
        row.exif_taken_at = value
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()
        await self._session.refresh(row)
        return row

    async def update_file_exif(
        self,
        file_id: int,
        *,
        taken_at: str | None,
        lat: float | None,
        lng: float | None,
        camera: str | None = None,
        lens: str | None = None,
        iso: int | None = None,
        aperture: str | None = None,
        shutter: str | None = None,
    ) -> bool:
        """回填：更新拍摄时间、GPS 与相机 EXIF（只写库，不改原图）。"""
        row = await self._session.get(FileRow, file_id)
        if row is None:
            return False
        row.exif_taken_at = taken_at
        row.exif_lat = lat
        row.exif_lng = lng
        row.exif_camera = camera
        row.exif_lens = lens
        row.exif_iso = iso
        row.exif_aperture = aperture
        row.exif_shutter = shutter
        return True

    async def delete_file_row(self, file_id: int, *, commit: bool = True) -> None:
        row = await self._session.get(FileRow, file_id)
        if row is None:
            return
        await self._session.delete(row)
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()

    async def ensure_category(
        self, name: str, *, type_: ResourceType = ResourceType.IMAGE, commit: bool = True
    ) -> Category:
        """查找或创建同类型分类（兼容旧调用）。"""
        trimmed = name.strip()
        stmt = select(CategoryRow).where(
            CategoryRow.name == trimmed, CategoryRow.type == type_.value
        )
        row = (await self._session.execute(stmt)).scalars().first()
        if row is None:
            row = CategoryRow(name=trimmed, type=type_.value)
            self._session.add(row)
            if commit:
                await self._session.commit()
            else:
                await self._session.flush()
            await self._session.refresh(row)
        return _category_to_domain(row)

    async def set_category_id(
        self, resource_id: int, category_id: int | None, *, commit: bool = True
    ) -> None:
        row = await self._session.get(ResourceRow, resource_id)
        if row is None:
            return
        row.category_id = category_id
        row.updated_at = db_now()
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()

    async def set_categories(
        self, resource_id: int, category_ids: list[int], *, commit: bool = True
    ) -> None:
        await self._session.execute(
            delete(ResourceCategoryRow).where(ResourceCategoryRow.resource_id == resource_id)
        )
        unique_ids = list(dict.fromkeys(category_ids))
        for category_id in unique_ids:
            self._session.add(ResourceCategoryRow(
                resource_id=resource_id, category_id=category_id
            ))
        row = await self._session.get(ResourceRow, resource_id)
        if row is not None:
            row.updated_at = db_now()
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()

    async def ensure_tag(self, name: str, *, commit: bool = True) -> Tag:
        """按名查找或创建标签词条。"""
        trimmed = name.strip()
        stmt = select(TagRow).where(TagRow.name == trimmed)
        row = (await self._session.execute(stmt)).scalars().first()
        if row is None:
            row = TagRow(name=trimmed)
            self._session.add(row)
            if commit:
                await self._session.commit()
            else:
                await self._session.flush()
            await self._session.refresh(row)
        return Tag(id=row.id, name=row.name)

    async def replace_tags(
        self, resource_id: int, names: list[str], *, commit: bool = True
    ) -> None:
        """整表替换该资源的标签关联。"""
        existing = await self._session.execute(
            select(ResourceTagRow).where(ResourceTagRow.resource_id == resource_id)
        )
        for link in existing.scalars().all():
            await self._session.delete(link)
        seen: set[str] = set()
        for raw in names:
            name = raw.strip()
            if not name or name in seen:
                continue
            seen.add(name)
            tag = await self.ensure_tag(name, commit=False)
            assert tag.id is not None
            self._session.add(ResourceTagRow(resource_id=resource_id, tag_id=tag.id))
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()

    async def add_tags_union(
        self, resource_id: int, names: list[str], *, commit: bool = True
    ) -> None:
        existing_ids = set(
            (
                await self._session.execute(
                    select(ResourceTagRow.tag_id).where(ResourceTagRow.resource_id == resource_id)
                )
            )
            .scalars()
            .all()
        )
        seen: set[str] = set()
        for raw in names:
            name = raw.strip()
            if not name or name in seen:
                continue
            seen.add(name)
            tag = await self.ensure_tag(name, commit=False)
            assert tag.id is not None
            if tag.id in existing_ids:
                continue
            self._session.add(ResourceTagRow(resource_id=resource_id, tag_id=tag.id))
            existing_ids.add(tag.id)
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()

    async def scrape_pending_ids(self, resource_ids: list[int]) -> set[int]:
        if not resource_ids:
            return set()
        latest = (
            select(ScrapeJobRow.resource_id, func.max(ScrapeJobRow.id).label("jid"))
            .where(ScrapeJobRow.resource_id.in_(resource_ids))
            .group_by(ScrapeJobRow.resource_id)
            .subquery()
        )
        selected = exists(
            select(CandidateRow.id).where(
                CandidateRow.job_id == ScrapeJobRow.id, CandidateRow.selected == 1
            )
        )
        stmt = (
            select(ScrapeJobRow.resource_id)
            .join(latest, ScrapeJobRow.id == latest.c.jid)
            .where(
                ScrapeJobRow.status == "done",
                ScrapeJobRow.match_count > 0,
                ~selected,
            )
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return set(int(i) for i in rows)

    async def attach_scrape_pending(self, resources: list[Resource]) -> None:
        ids = [item.id for item in resources if item.id is not None]
        pending = await self.scrape_pending_ids(ids)
        for item in resources:
            item.scrape_pending = item.id in pending

    async def list_categories(self, type_: ResourceType | None = None) -> list[Category]:
        stmt = select(CategoryRow).order_by(CategoryRow.type, CategoryRow.name)
        if type_ is not None:
            stmt = stmt.where(CategoryRow.type == type_.value)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_category_to_domain(row) for row in rows]

    async def list_tags(self, type_: ResourceType | None = None) -> list[Tag]:
        """标签词表；给类型时只返回该类型 active 资源实际打过的标签（本类标签筛选）。"""
        stmt = select(TagRow).order_by(TagRow.name)
        if type_ is not None:
            stmt = (
                select(TagRow)
                .join(ResourceTagRow, ResourceTagRow.tag_id == TagRow.id)
                .join(ResourceRow, ResourceRow.id == ResourceTagRow.resource_id)
                .where(ResourceRow.type == type_.value, ResourceRow.status == "active")
                .distinct()
                .order_by(TagRow.name)
            )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [Tag(id=r.id, name=r.name) for r in rows]

    async def get_file_by_role(self, resource_id: int, role: str) -> FileRow | None:
        stmt = (
            select(FileRow)
            .where(FileRow.resource_id == resource_id, FileRow.role == role)
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalars().first()

    async def get_file_by_path(self, resource_id: int, path: str) -> FileRow | None:
        stmt = select(FileRow).where(FileRow.resource_id == resource_id, FileRow.path == path)
        return (await self._session.execute(stmt)).scalars().first()

    async def add_todo(self, resource_id: int, content: str, *, commit: bool = True) -> ResourceTodo:
        max_sort = await self._session.scalar(
            select(func.coalesce(func.max(ResourceTodoRow.sort), -1)).where(
                ResourceTodoRow.resource_id == resource_id
            )
        )
        row = ResourceTodoRow(
            resource_id=resource_id,
            content=content.strip(),
            done=0,
            sort=int(max_sort or -1) + 1,
            created_at=db_now(),
        )
        self._session.add(row)
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()
        await self._session.refresh(row)
        return ResourceTodo(
            id=row.id,
            resource_id=row.resource_id,
            content=row.content,
            done=bool(row.done),
            sort=row.sort,
            created_at=row.created_at,
        )

    async def patch_todo(
        self,
        resource_id: int,
        todo_id: int,
        *,
        content: str | None = None,
        done: bool | None = None,
        commit: bool = True,
    ) -> ResourceTodo | None:
        row = await self._session.get(ResourceTodoRow, todo_id)
        if row is None or row.resource_id != resource_id:
            return None
        if content is not None:
            row.content = content.strip()
        if done is not None:
            row.done = 1 if done else 0
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()
        await self._session.refresh(row)
        return ResourceTodo(
            id=row.id,
            resource_id=row.resource_id,
            content=row.content,
            done=bool(row.done),
            sort=row.sort,
            created_at=row.created_at,
        )

    async def delete_todo(self, resource_id: int, todo_id: int, *, commit: bool = True) -> bool:
        row = await self._session.get(ResourceTodoRow, todo_id)
        if row is None or row.resource_id != resource_id:
            return False
        await self._session.delete(row)
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()
        return True

    async def get_file(self, resource_id: int, file_id: int) -> FileRow | None:
        stmt = select(FileRow).where(FileRow.id == file_id, FileRow.resource_id == resource_id)
        return (await self._session.execute(stmt)).scalars().first()

    async def recent(self, limit: int = 12) -> list[Resource]:
        """获取最近添加的资源。"""
        stmt = (
            select(ResourceRow)
            .where(ResourceRow.status == ResourceStatus.ACTIVE.value)
            .order_by(ResourceRow.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        resources = await self._attach_thumbnail_paths([_orm_to_resource(r) for r in rows])
        await self.attach_categories(resources)
        await self.attach_scrape_pending(resources)
        return resources

    async def previews_by_type(self, limit: int = 3) -> dict[str, list[str]]:
        """Recent thumbnail stack per media type for the home overview."""
        previews: dict[str, list[str]] = {}
        for type_ in (ResourceType.IMAGE, ResourceType.VIDEO, ResourceType.ANIME, ResourceType.AV):
            stmt = (
                select(ResourceRow.id, FileRow.id)
                .join(FileRow, FileRow.resource_id == ResourceRow.id)
                .where(
                    ResourceRow.status == ResourceStatus.ACTIVE.value,
                    ResourceRow.type == type_.value,
                    FileRow.role == FILE_ROLE_THUMBNAIL,
                )
                .order_by(ResourceRow.created_at.desc(), ResourceRow.id.desc())
                .limit(limit)
            )
            rows = (await self._session.execute(stmt)).all()
            previews[type_.value] = [
                _file_content_url(int(resource_id), int(file_id))
                for resource_id, file_id in rows
            ]
        return previews

    async def stats(self) -> dict[str, Any]:
        """资源统计：一次 GROUP BY status+type，再 SUM 体积。

        by_type 不包含已在合集内的 active 资源（与主列表默认隐藏一致）；
        回收站/丢失计数与总体积按全库统计。
        """
        collected_ids = select(CollectionItemRow.resource_id)
        grouped = (
            await self._session.execute(
                select(ResourceRow.status, ResourceRow.type, func.count())
                .select_from(ResourceRow)
                .where(
                    or_(
                        ResourceRow.status != ResourceStatus.ACTIVE.value,
                        ResourceRow.id.not_in(collected_ids),
                    )
                )
                .group_by(ResourceRow.status, ResourceRow.type)
            )
        ).all()
        by_type: dict[str, int] = {}
        trashed_count = 0
        lost_count = 0
        for status, type_, count in grouped:
            n = int(count)
            if status == ResourceStatus.ACTIVE.value:
                by_type[type_] = n
            elif status == ResourceStatus.TRASHED.value:
                trashed_count += n
            elif status == ResourceStatus.LOST.value:
                lost_count += n
        active_ids = select(ResourceRow.id).where(ResourceRow.status == ResourceStatus.ACTIVE.value)
        total_size_bytes = await self._session.scalar(
            select(func.coalesce(func.sum(FileRow.size), 0)).where(FileRow.resource_id.in_(active_ids))
        )
        return {
            "by_type": by_type,
            "total_size_bytes": int(total_size_bytes or 0),
            "trashed_count": trashed_count,
            "lost_count": lost_count,
        }


    async def media_primary_files(self) -> list[tuple[FileRow, str]]:
        """回填用：active 图片/视频的 primary 文件行与资源类型。"""
        rows = (
            await self._session.execute(
                select(FileRow, ResourceRow.type)
                .join(ResourceRow, ResourceRow.id == FileRow.resource_id)
                .where(
                    ResourceRow.type.in_(
                        (ResourceType.IMAGE.value, ResourceType.VIDEO.value)
                    ),
                    ResourceRow.status == ResourceStatus.ACTIVE.value,
                    FileRow.role == FILE_ROLE_PRIMARY,
                )
            )
        ).all()
        return [(row[0], str(row[1])) for row in rows]

    async def timeline_photos(
        self,
        *,
        include_all: bool,
        type_: ResourceType,
        year: int | None,
        month: int | None,
        category_ids: list[int] | None,
        tag_ids: list[int] | None,
        exclude_category_ids: list[int] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        include_untimed: bool = False,
        map_visible: bool | None = None,
        map_only: bool = False,
        character_ids: list[int] | None = None,
        person_ids: list[int] | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
        """Single-type timeline tiles; unknown time optional."""
        primary = aliased(FileRow)
        thumb = aliased(FileRow)
        base = self._filter(
            select(ResourceRow.id),
            type_,
            ResourceStatus.ACTIVE,
            category_ids=category_ids,
            exclude_category_ids=exclude_category_ids,
            tag_ids=tag_ids,
            timeline_visible=None if include_all else True,
            map_visible=map_visible,
            map_only=map_only,
            character_ids=character_ids,
            person_ids=person_ids,
        )
        join = (
            select(
                ResourceRow.id,
                ResourceRow.title,
                ResourceRow.type,
                primary.id.label("file_id"),
                primary.exif_taken_at,
                primary.exif_lat,
                primary.exif_lng,
                primary.width,
                primary.height,
                primary.duration,
                thumb.id.label("thumb_id"),
            )
            .select_from(ResourceRow)
            .join(
                primary,
                and_(
                    primary.resource_id == ResourceRow.id,
                    primary.role == FILE_ROLE_PRIMARY,
                ),
            )
            .outerjoin(
                thumb,
                and_(
                    thumb.resource_id == ResourceRow.id,
                    thumb.role == FILE_ROLE_THUMBNAIL,
                ),
            )
            .where(ResourceRow.id.in_(base))
        )

        def to_tile(row) -> dict[str, Any]:
            rid, title, type_, file_id, taken_at, lat, lng, width, height, duration, thumb_id = row
            content_id = thumb_id if thumb_id is not None else file_id
            return {
                "id": int(rid),
                "title": title or "",
                "kind": "video" if type_ == ResourceType.VIDEO.value else "image",
                "width": int(width) if width is not None else None,
                "height": int(height) if height is not None else None,
                "duration": float(duration) if duration is not None else None,
                "taken_at": taken_at,
                "lat": float(lat) if lat is not None else None,
                "lng": float(lng) if lng is not None else None,
                "thumbnail_path": _file_content_url(int(rid), int(content_id)),
            }

        dated_stmt = (
            join.where(primary.exif_taken_at.is_not(None))
            .order_by(desc(primary.exif_taken_at), desc(ResourceRow.id))
        )
        if year is not None:
            dated_stmt = dated_stmt.where(
                func.substr(primary.exif_taken_at, 1, 4) == f"{year:04d}"
            )
        if month is not None:
            if year is not None:
                dated_stmt = dated_stmt.where(
                    func.substr(primary.exif_taken_at, 1, 7) == f"{year:04d}-{month:02d}"
                )
            else:
                dated_stmt = dated_stmt.where(
                    func.substr(primary.exif_taken_at, 6, 2) == f"{month:02d}"
                )
        if date_from is not None:
            dated_stmt = dated_stmt.where(func.substr(primary.exif_taken_at, 1, 10) >= date_from[:10])
        if date_to is not None:
            dated_stmt = dated_stmt.where(func.substr(primary.exif_taken_at, 1, 10) <= date_to[:10])
        dated_rows = (await self._session.execute(dated_stmt)).all()

        days_map: dict[str, list[dict[str, Any]]] = {}
        for row in dated_rows:
            date = str(row[4])[:10]
            days_map.setdefault(date, []).append(to_tile(row))
        days = [
            {"date": date, "count": len(photos), "photos": photos}
            for date, photos in sorted(days_map.items(), reverse=True)
        ]

        unknown: list[dict[str, Any]] = []
        if include_untimed:
            has_taken = self._taken_date_exists(None)
            unknown_rows = (
                await self._session.execute(
                    join.where(~has_taken).order_by(desc(ResourceRow.id))
                )
            ).all()
            unknown = [to_tile(row) for row in unknown_rows]
        total = sum(day["count"] for day in days) + len(unknown)
        return days, unknown, total

    async def list_mixed(
        self, limit: int, offset: int, exclude_collected: bool = False
    ) -> tuple[list[object], int]:
        """全库混排（无过滤时）：active 资源 + 合集按时间倒序，offset 分页。

        返回条目：Resource（领域模型）或合集卡 dict（cardType=collection）。
        exclude_collected=True 时资源部分不含已归集到合集的成员。
        """
        resource_rows = select(
            literal("resource").label("kind"),
            ResourceRow.id.label("rid"),
            ResourceRow.created_at.label("ts"),
        ).where(ResourceRow.status == ResourceStatus.ACTIVE.value)
        if exclude_collected:
            resource_rows = resource_rows.where(
                ResourceRow.id.not_in(select(CollectionItemRow.resource_id))
            )
        union = (
            resource_rows
            .union_all(
                select(
                    literal("collection").label("kind"),
                    CollectionRow.id.label("rid"),
                    CollectionRow.updated_at.label("ts"),
                )
            )
            .subquery()
        )
        total = int(await self._session.scalar(select(func.count()).select_from(union)) or 0)
        rows = (await self._session.execute(
            select(union.c.kind, union.c.rid)
            .order_by(union.c.ts.desc(), union.c.rid.desc())
            .limit(limit)
            .offset(offset)
        )).all()
        items: list[object] = []
        collection_ids: list[int] = []
        for kind, rid in rows:
            if kind == "resource":
                row = await self._session.get(ResourceRow, rid)
                if row is not None and row.status == ResourceStatus.ACTIVE.value:
                    items.append(_orm_to_resource(row))
            else:
                col_row = await self._session.get(CollectionRow, rid)
                if col_row is None:
                    continue
                collection_ids.append(int(rid))
                items.append({
                    "cardType": "collection",
                    "id": rid,
                    "title": col_row.title,
                    "memberCount": 0,
                    "updatedAt": col_row.updated_at,
                    "previewThumbnails": [],
                })
        if collection_ids:
            from app.library.infrastructure.repositories_collections import CollectionRepository

            collection_repo = CollectionRepository(self._session)
            counts = await collection_repo._active_member_counts(collection_ids)
            previews = await collection_repo._preview_thumbnails(collection_ids)
            for item in items:
                if isinstance(item, dict) and item.get("cardType") == "collection":
                    cid = int(item["id"])
                    item["memberCount"] = counts.get(cid, 0)
                    item["previewThumbnails"] = previews.get(cid, [])
        return items, total
