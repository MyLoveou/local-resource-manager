"""资源库应用用例（编排仓储 → DTO）。"""
import asyncio
from pathlib import Path

from app.library.application.packages.layouts import layout_for
from app.library.application.packages.resource_package import ResourcePackage, default_library_store
from app.library.application.schemas import (
    CoverReplace,
    Overview,
    ResourcePage,
    ResourcePatch,
    ResourceSortField,
    ResourceStats,
    TaskSummary,
)
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository
from app.shared.config import settings
from app.shared.fs.file_ops import FileOps
from app.shared.models import Resource, ResourceStatus, ResourceType

_COVER_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic", ".avif"}


class LibraryQueryService:
    """资源库用例：概览、列表、部分更新、软删、换封面。"""

    def __init__(
        self,
        resources: ResourceRepository,
        tasks: TaskSummaryRepository,
        *,
        file_ops: FileOps | None = None,
        store_root: Path | None = None,
    ):
        self._resources = resources
        self._tasks = tasks
        self._ops = file_ops or FileOps()
        self._store = store_root or default_library_store(settings.db_path)

    async def overview(self) -> Overview:
        """首页概览：统计 + 最近添加 + 任务计数。"""
        return Overview(
            stats=ResourceStats(**await self._resources.stats()),
            recent=await self._resources.recent(limit=12),
            tasks=TaskSummary(**await self._tasks.summary()),
        )

    async def list_page(
        self,
        type_: ResourceType | None,
        status: ResourceStatus | None,
        limit: int,
        offset: int,
        sort: ResourceSortField,
        order: str,
    ) -> ResourcePage:
        """分页列表。sort 预留；MVP 仅 createdAt。"""
        _ = sort
        total = await self._resources.count(type_, status)
        items = await self._resources.list(type_, status, limit, offset, order)
        return ResourcePage(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(items) < total,
        )

    async def patch(self, resource_id: int, body: ResourcePatch) -> Resource | None:
        """部分更新标题/描述/评分；可选按名绑定分类、整表替换标签。"""
        existing = await self._resources.get(resource_id)
        if existing is None:
            return None
        data = body.model_dump(exclude_unset=True)
        data.pop("tag_names", None)
        data.pop("category_name", None)
        for key, value in data.items():
            setattr(existing, key, value)
        existing._touch()
        updated = await self._resources.update(resource_id, existing, commit=False)
        if updated is None:
            return None
        if "category_name" in body.model_fields_set:
            raw = body.category_name
            if raw is None or not raw.strip():
                await self._resources.set_category_id(resource_id, None, commit=False)
            else:
                cat = await self._resources.ensure_category(raw, commit=False)
                await self._resources.set_category_id(resource_id, cat.id, commit=False)
        if "tag_names" in body.model_fields_set:
            await self._resources.replace_tags(resource_id, body.tag_names or [], commit=False)
        await self._resources.commit()
        return await self._resources.get(resource_id)

    async def replace_cover(self, resource_id: int, body: CoverReplace) -> Resource | None:
        """复制本机图片为 cover 角色，不改 primary。"""
        src = Path(body.path)
        if not src.is_file() or src.suffix.lower() not in _COVER_EXTS:
            raise ValueError("invalid cover path")
        existing = await self._resources.get(resource_id)
        if existing is None or existing.id is None:
            return None
        layout = layout_for(existing.type)
        if layout is None:
            raise ValueError("unsupported type")
        package = ResourcePackage(
            self._store,
            existing.type,
            existing.id,
            self._ops,
            cover_falls_back_to_primary=layout.cover_falls_back_to_primary,
        )
        old = await self._resources.get_file_by_role(existing.id, "cover")
        dest = await asyncio.to_thread(package.put_cover, src)
        if old is not None:
            old_path = Path(old.path)
            if old_path.resolve() != dest.resolve() and old_path.is_file():
                await asyncio.to_thread(old_path.unlink)
            await self._resources.delete_file_row(old.id, commit=False)
        size = dest.stat().st_size
        cover_row = await self._resources.add_file(
            existing.id,
            path=str(dest),
            sha256=None,
            size=size,
            format_=dest.suffix.lower().lstrip("."),
            role="cover",
            commit=False,
        )
        existing.cover_path = f"/library/resources/{existing.id}/files/{cover_row.id}/content"
        existing._touch()
        await self._resources.update(existing.id, existing, commit=False)
        await self._resources.commit()
        return await self._resources.get(existing.id)

    async def trash(self, resource_id: int) -> Resource | None:
        """软删入回收站（已 trashed 则原样写回）。"""
        return await self._resources.trash(resource_id)
