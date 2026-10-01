"""资源库仓储实现（SQLAlchemy 2.0 async）。

ORM 行 ↔ Pydantic 领域模型；API camelCase 由 ApiModel 负责。
"""
import json
from collections.abc import Callable
from typing import Any

from sqlalchemy import and_, asc, desc, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.db.orm import (
    CandidateRow,
    CategoryRow,
    DownloadTaskRow,
    EpisodeRow,
    ExtraRow,
    FileRow,
    ResourceRow,
    ResourceTagRow,
    ResourceTodoRow,
    ScrapeJobRow,
    SeasonRow,
    TagRow,
)
from app.library.domain.media_types import (
    FILE_ROLE_PAGE,
    FILE_ROLE_THUMBNAIL,
    is_series_type,
)
from app.shared.utils.time import db_now, db_ts
from app.library.domain.models import (
    Category,
    Resource,
    WorkCatalog,
    ResourceFile,
    ResourceStatus,
    ResourceTodo,
    ResourceType,
    SeriesEpisode,
    SeriesExtra,
    SeriesSeason,
    StorageKind,
    Tag,
)


def _file_content_url(resource_id: int, file_id: int) -> str:
    """已有文件流路由，网格缩略图也走它。"""
    return f"/library/resources/{resource_id}/files/{file_id}/content"


def _parse_extra(raw: str | None) -> dict[str, Any]:
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _catalog_from_extra(extra: dict[str, Any]) -> WorkCatalog | None:
    raw = extra.get("catalog")
    if not isinstance(raw, dict) or not raw:
        return None
    try:
        return WorkCatalog.model_validate(raw)
    except Exception:
        return None


def _dump_extra(resource: Resource) -> str:
    extra = dict(resource.extra or {})
    if resource.catalog is None:
        extra.pop("catalog", None)
    else:
        extra["catalog"] = resource.catalog.model_dump(mode="json", by_alias=True)
    return json.dumps(extra, ensure_ascii=False)


def _orm_to_resource(row: ResourceRow) -> Resource:
    """ORM 行 → 领域模型。"""
    extra = _parse_extra(row.extra)
    catalog = _catalog_from_extra(extra)
    rest = {k: v for k, v in extra.items() if k != "catalog"}
    return Resource(
        id=row.id,
        type=ResourceType(row.type),
        storage_kind=StorageKind(row.storage_kind or StorageKind.OWNED.value),
        title=row.title,
        description=row.description,
        synopsis=row.synopsis,
        catalog=catalog,
        author=row.author,
        rating=row.rating,
        cover_path=row.cover_path,
        status=ResourceStatus(row.status),
        deleted_at=row.deleted_at,
        last_scraped_at=row.last_scraped_at,
        scraped_source=row.scraped_source,
        extra=rest,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def orm_to_resource(row: ResourceRow) -> Resource:
    return _orm_to_resource(row)


class ResourceRepository:
    """资源仓储：创建/查询/统计。"""

    def __init__(self, session: AsyncSession):
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def attach_listed(self, resources: list[Resource]) -> list[Resource]:
        return await self._attach_thumbnail_paths(resources)

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
            cover_path=resource.cover_path,
            status=resource.status.value,
            extra=_dump_extra(resource),
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
        row.cover_path = resource.cover_path
        row.status = resource.status.value
        row.deleted_at = db_ts(resource.deleted_at)
        row.last_scraped_at = db_ts(resource.last_scraped_at)
        row.scraped_source = resource.scraped_source
        row.extra = _dump_extra(resource)
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
        cat = (
            await self._session.get(CategoryRow, row.category_id)
            if row.category_id is not None
            else None
        )
        tags = (await self._session.execute(tag_stmt)).scalars().all()
        files = (await self._session.execute(file_stmt)).scalars().all()
        todos = (await self._session.execute(todo_stmt)).scalars().all()
        if cat is not None:
            resource.category = Category(id=cat.id, name=cat.name)
        resource.tags = [Tag(id=t.id, name=t.name) for t in tags]
        resource.files = [
            ResourceFile(
                id=f.id,
                resource_id=f.resource_id,
                path=f.path,
                sha256=f.sha256,
                size=f.size,
                format=f.format,
                role=f.role,
                duration=f.duration,
                width=f.width,
                height=f.height,
                codec=f.codec,
                fps=f.fps,
                bitrate=f.bitrate,
                exif_taken_at=f.exif_taken_at,
                created_at=f.created_at,
            )
            for f in files
        ]
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
        files_by_id = {f.id: f for f in resource.files if f.id is not None}
        season_rows = (
            await self._session.execute(
                select(SeasonRow)
                .where(SeasonRow.resource_id == resource.id)
                .order_by(SeasonRow.sort_index, SeasonRow.season_number, SeasonRow.id)
            )
        ).scalars().all()
        seasons: list[SeriesSeason] = []
        for season in season_rows:
            ep_rows = (
                await self._session.execute(
                    select(EpisodeRow)
                    .where(EpisodeRow.season_id == season.id, EpisodeRow.status == "active")
                    .order_by(EpisodeRow.sort_index, EpisodeRow.episode_number, EpisodeRow.id)
                )
            ).scalars().all()
            episodes: list[SeriesEpisode] = []
            for episode in ep_rows:
                media = files_by_id.get(episode.file_id)
                episodes.append(
                    SeriesEpisode(
                        id=episode.id,
                        file_id=episode.file_id,
                        episode_number=episode.episode_number,
                        title=episode.title,
                        duration=media.duration if media else None,
                        width=media.width if media else None,
                        height=media.height if media else None,
                    )
                )
            seasons.append(
                SeriesSeason(
                    id=season.id,
                    season_number=season.season_number,
                    title=season.title,
                    episodes=episodes,
                )
            )
        extra_rows = (
            await self._session.execute(
                select(ExtraRow)
                .where(ExtraRow.resource_id == resource.id, ExtraRow.status == "active")
                .order_by(ExtraRow.sort_index, ExtraRow.id)
            )
        ).scalars().all()
        extras: list[SeriesExtra] = []
        for extra in extra_rows:
            media = files_by_id.get(extra.file_id)
            extras.append(
                SeriesExtra(
                    id=extra.id,
                    file_id=extra.file_id,
                    title=extra.title,
                    duration=media.duration if media else None,
                )
            )
        resource.seasons = seasons
        resource.extras = extras

    def _apply_thumbnail_path(self, resource: Resource) -> None:
        """从已加载 files 填 thumbnail_path，不改 cover_path。"""
        if resource.id is None:
            return
        thumb = next((f for f in resource.files if f.role == FILE_ROLE_THUMBNAIL and f.id is not None), None)
        if thumb is None:
            resource.thumbnail_path = None
            return
        resource.thumbnail_path = _file_content_url(resource.id, thumb.id)

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
                select(CategoryRow.id).where(
                    CategoryRow.id == ResourceRow.category_id,
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

    def _filter(
        self,
        stmt,
        type_: ResourceType | None,
        status: ResourceStatus | None,
        q: str | None = None,
        tag_ids: list[int] | None = None,
    ):
        if type_ is not None:
            stmt = stmt.where(ResourceRow.type == type_.value)
        if status is not None:
            stmt = stmt.where(ResourceRow.status == status.value)
        return self._search_filter(stmt, q, tag_ids)

    async def count(
        self,
        type_: ResourceType | None = None,
        status: ResourceStatus | None = None,
        q: str | None = None,
        tag_ids: list[int] | None = None,
    ) -> int:
        """与 list 相同过滤条件下的总数。"""
        stmt = self._filter(select(func.count()).select_from(ResourceRow), type_, status, q, tag_ids)
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
        after_key: str | None = None,
        after_created_at: str | None = None,
        after_id: int | None = None,
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
            after_key=after_key,
            after_created_at=after_created_at,
            after_id=after_id,
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
        after_key: str | None = None,
        after_created_at: str | None = None,
        after_id: int | None = None,
    ) -> tuple[list[Resource], list[str]]:
        from app.library.application.list_query import serialize_sort_value

        sort_expr = self._sort_expr(sort)
        stmt = self._filter(select(ResourceRow, sort_expr.label("sort_value")), type_, status, q, tag_ids)
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
        await self.attach_scrape_pending(resources)
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

    async def delete_file_row(self, file_id: int, *, commit: bool = True) -> None:
        row = await self._session.get(FileRow, file_id)
        if row is None:
            return
        await self._session.delete(row)
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()

    async def ensure_category(self, name: str, *, commit: bool = True) -> Category:
        """按名查找或创建分类词条。"""
        trimmed = name.strip()
        stmt = select(CategoryRow).where(CategoryRow.name == trimmed)
        row = (await self._session.execute(stmt)).scalars().first()
        if row is None:
            row = CategoryRow(name=trimmed)
            self._session.add(row)
            if commit:
                await self._session.commit()
            else:
                await self._session.flush()
            await self._session.refresh(row)
        return Category(id=row.id, name=row.name)

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

    async def list_categories(self) -> list[Category]:
        rows = (
            await self._session.execute(select(CategoryRow).order_by(CategoryRow.name))
        ).scalars().all()
        return [Category(id=r.id, name=r.name) for r in rows]

    async def list_tags(self) -> list[Tag]:
        rows = (await self._session.execute(select(TagRow).order_by(TagRow.name))).scalars().all()
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
        """最近入库的活跃资源。"""
        stmt = (
            select(ResourceRow)
            .where(ResourceRow.status == ResourceStatus.ACTIVE.value)
            .order_by(ResourceRow.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        resources = await self._attach_thumbnail_paths([_orm_to_resource(r) for r in rows])
        await self.attach_scrape_pending(resources)
        return resources

    async def stats(self) -> dict[str, Any]:
        """资源统计：一次 GROUP BY status+type，再 SUM 体积。"""
        grouped = (
            await self._session.execute(
                select(ResourceRow.status, ResourceRow.type, func.count())
                .select_from(ResourceRow)
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
