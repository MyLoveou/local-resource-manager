"""资源库应用用例（编排仓储 → DTO）。"""
import asyncio
from datetime import datetime
from pathlib import Path

from app.library.application.packages.layouts import layout_for
from app.library.application.packages.resource_package import ResourcePackage, default_library_store
from app.library.application.schemas import (
    CoverReplace,
    Overview,
    ResourceBatchFailedItem,
    ResourceBatchResult,
    ResourcePage,
    ResourcePatch,
    ResourceSortField,
    ResourceStats,
    SubtitleAdd,
    TaskSummary,
    TodoCreate,
    TodoPatch,
)
from app.library.application.subtitle_naming import original_stem_from_extra, subtitle_dest_name
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository
from app.shared.config import settings
from app.shared.errors import InvalidStateError
from app.shared.fs.file_ops import FileOps
from app.shared.log import logger
from app.shared.media_types import COVER_EXTENSIONS, FILE_ROLE_THUMBNAIL, SUBTITLE_EXTENSIONS
from app.shared.models import Resource, ResourceStatus, ResourceType


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
        *,
        after_created_at: str | None = None,
        after_id: int | None = None,
    ) -> ResourcePage:
        """分页列表。sort 预留；MVP 仅 createdAt。keyset 优先于 offset。"""
        _ = sort
        fetch = limit + 1
        use_keyset = after_created_at is not None and after_id is not None
        items = await self._resources.list(
            type_,
            status,
            fetch,
            0 if use_keyset else offset,
            order,
            after_created_at=after_created_at if use_keyset else None,
            after_id=after_id if use_keyset else None,
        )
        has_more = len(items) > limit
        items = items[:limit]
        total = await self._resources.count(type_, status)
        last = items[-1] if items else None
        cursor_ts = None
        if last is not None and last.created_at is not None:
            if isinstance(last.created_at, datetime):
                cursor_ts = last.created_at.strftime("%Y-%m-%d %H:%M:%S")
            else:
                cursor_ts = str(last.created_at)
        return ResourcePage(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more,
            next_created_at=cursor_ts if has_more else None,
            next_id=last.id if has_more and last is not None else None,
        )

    async def patch(self, resource_id: int, body: ResourcePatch) -> Resource | None:
        """部分更新标题/描述/评分；可选按名绑定分类、整表替换标签。"""
        existing = await self._resources.get(resource_id)
        if existing is None:
            return None
        data = body.model_dump(exclude_unset=True)
        data.pop("tag_names", None)
        data.pop("category_name", None)
        if "author" in data:
            raw_author = data["author"]
            data["author"] = raw_author.strip() if isinstance(raw_author, str) and raw_author.strip() else None
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
        if not src.is_file() or src.suffix.lower() not in COVER_EXTENSIONS:
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
        await self._try_refresh_thumbnail(existing.id, package, dest)
        return await self._resources.get(existing.id)

    async def _try_refresh_thumbnail(self, resource_id: int, package: ResourcePackage, source_image: Path) -> None:
        """换封面后覆盖网格缩略图；失败不影响封面提交。"""
        try:
            thumb_dest = await asyncio.to_thread(package.put_thumbnail, source_image)
            if thumb_dest is None:
                return
            thumb_size = (await asyncio.to_thread(thumb_dest.stat)).st_size
            old_thumb = await self._resources.get_file_by_role(resource_id, FILE_ROLE_THUMBNAIL)
            if old_thumb is not None:
                await self._resources.update_file_stat(
                    old_thumb.id,
                    path=str(thumb_dest),
                    size=thumb_size,
                    format_=thumb_dest.suffix.lower().lstrip("."),
                    commit=True,
                )
                return
            await self._resources.add_file(
                resource_id,
                path=str(thumb_dest),
                sha256=None,
                size=thumb_size,
                format_=thumb_dest.suffix.lower().lstrip("."),
                role=FILE_ROLE_THUMBNAIL,
                commit=True,
            )
        except Exception as exc:
            logger.warning("换封面后缩略图失败 resource=%s: %s", resource_id, exc)
            await self._resources.rollback()

    async def add_subtitle(self, resource_id: int, body: SubtitleAdd) -> Resource | None:
        """复制字幕进包内并按原始视频名改名。"""
        src = Path(body.path)
        if not src.is_file() or src.suffix.lower() not in SUBTITLE_EXTENSIONS:
            raise ValueError("invalid subtitle path")
        existing = await self._resources.get(resource_id)
        if existing is None or existing.id is None:
            return None
        if existing.type != ResourceType.VIDEO:
            raise ValueError("subtitles only for video")
        dest_name = subtitle_dest_name(original_stem_from_extra(existing.extra, existing.title), src.name)
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
        dest = await asyncio.to_thread(package.put_subtitle, src, dest_name)
        size = await asyncio.to_thread(lambda: dest.stat().st_size)
        old = await self._resources.get_file_by_path(existing.id, str(dest))
        if old is not None:
            await self._resources.delete_file_row(old.id, commit=False)
        await self._resources.add_file(
            existing.id,
            path=str(dest),
            sha256=None,
            size=size,
            format_=dest.suffix.lower().lstrip("."),
            role="subtitle",
            commit=False,
        )
        existing._touch()
        await self._resources.update(existing.id, existing, commit=False)
        await self._resources.commit()
        return await self._resources.get(existing.id)

    async def add_todo(self, resource_id: int, body: TodoCreate) -> Resource | None:
        existing = await self._resources.get(resource_id)
        if existing is None:
            return None
        content = body.content.strip()
        if not content:
            raise ValueError("todo content required")
        await self._resources.add_todo(resource_id, content)
        return await self._resources.get(resource_id)

    async def patch_todo(self, resource_id: int, todo_id: int, body: TodoPatch) -> Resource | None:
        existing = await self._resources.get(resource_id)
        if existing is None:
            return None
        content = body.content.strip() if body.content is not None else None
        if content is not None and not content:
            raise ValueError("todo content required")
        updated = await self._resources.patch_todo(
            resource_id,
            todo_id,
            content=content,
            done=body.done,
        )
        if updated is None:
            return None
        return await self._resources.get(resource_id)

    async def delete_todo(self, resource_id: int, todo_id: int) -> Resource | None:
        existing = await self._resources.get(resource_id)
        if existing is None:
            return None
        ok = await self._resources.delete_todo(resource_id, todo_id)
        if not ok:
            return None
        return await self._resources.get(resource_id)

    async def trash(self, resource_id: int) -> Resource | None:
        """软删入回收站（已 trashed 则原样写回）。"""
        return await self._resources.trash(resource_id)

    async def restore(self, resource_id: int) -> Resource | None:
        """仅 trashed → active。非 trashed 抛 InvalidStateError。"""
        return await self._resources.restore(resource_id)

    def _package_for(self, resource: Resource) -> ResourcePackage:
        layout = layout_for(resource.type)
        return ResourcePackage(
            self._store,
            resource.type,
            resource.id or 0,
            self._ops,
            cover_falls_back_to_primary=bool(layout and layout.cover_falls_back_to_primary),
        )

    async def purge(self, resource_id: int) -> bool:
        """先删库内包（已不存在则跳过），再 DROP 行。删盘失败不 DROP。"""
        existing = await self._resources.get(resource_id)
        if existing is None or existing.id is None:
            return False
        package = self._package_for(existing)
        try:
            await asyncio.to_thread(self._ops.remove_tree, package.root)
        except OSError as exc:
            logger.warning("删包失败 resource=%s: %s", resource_id, exc)
            raise RuntimeError("failed to delete package") from exc
        if existing.storage_kind.value == "owned" and package.root.exists():
            logger.warning("删包后目录仍在 resource=%s path=%s", resource_id, package.root)
            raise RuntimeError("failed to delete package")
        return await self._resources.delete_row(existing.id)

    async def batch(self, action: str, ids: list[int]) -> ResourceBatchResult:
        """逐条独立提交；部分失败不影响已成功项。"""
        unique: list[int] = []
        seen: set[int] = set()
        for rid in ids:
            if rid in seen:
                continue
            seen.add(rid)
            unique.append(rid)
        ok: list[int] = []
        failed: list[ResourceBatchFailedItem] = []
        for rid in unique:
            try:
                if action == "trash":
                    row = await self.trash(rid)
                    if row is None:
                        failed.append(ResourceBatchFailedItem(id=rid, message="resource not found"))
                    else:
                        ok.append(rid)
                elif action == "restore":
                    row = await self.restore(rid)
                    if row is None:
                        failed.append(ResourceBatchFailedItem(id=rid, message="resource not found"))
                    else:
                        ok.append(rid)
                elif action == "purge":
                    dropped = await self.purge(rid)
                    if dropped:
                        ok.append(rid)
                    else:
                        failed.append(ResourceBatchFailedItem(id=rid, message="resource not found"))
                else:
                    failed.append(ResourceBatchFailedItem(id=rid, message="invalid action"))
            except InvalidStateError:
                failed.append(ResourceBatchFailedItem(id=rid, message="resource is not trashed"))
            except Exception:
                await self._resources.rollback()
                logger.exception("批量操作失败 id=%s action=%s", rid, action)
                failed.append(ResourceBatchFailedItem(id=rid, message="operation failed"))
        return ResourceBatchResult(ok=ok, failed=failed)
