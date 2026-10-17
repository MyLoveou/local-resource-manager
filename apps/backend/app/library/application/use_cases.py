"""资源库应用用例（编排仓储 → DTO）。"""
import asyncio
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

import shutil

from app.library.application.covers import CoverNotAllowedError, attach_cover_image
from app.library.application.export_naming import export_name
from app.library.application.list_query import allowed_sorts, normalize_q
from app.library.application.media_probe import normalize_taken_at
from app.library.application.packages.layouts import layout_for
from app.library.application.packages.resource_package import ResourcePackage, default_library_store
from app.library.application.schemas import (
    CollectionExportResult,
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
from app.library.application.workbench import active_work, recent_consumption
from app.library.application.subtitle_naming import original_stem_from_extra, subtitle_dest_name
from app.library.domain.type_profile import allows_user_cover
from app.library.infrastructure.repositories import (
    CollectionRepository,
    ResourceRepository,
    TaskSummaryRepository,
)
from app.shared.config import settings
from app.shared.log import logger
from app.shared.errors import InvalidStateError
from app.shared.fs.file_ops import FileOps
from app.library.domain.media_types import (
    COVER_EXTENSIONS,
    FILE_ROLE_PRIMARY,
    SUBTITLE_EXTENSIONS,
)
from app.library.domain.models import (
    Collection,
    Resource,
    ResourceStatus,
    ResourceType,
)


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
            active_work=await active_work(self._resources.session),
            recent_consumption=await recent_consumption(self._resources.session),
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
        q: str | None = None,
        tag_ids: list[int] | None = None,
        category_id: int | None = None,
        after_key: str | None = None,
    ) -> ResourcePage:
        """分页列表。q/tagIds/categoryId/sort 服务端过滤；非法 sort 422。"""
        query = normalize_q(q)
        tags = tag_ids or []
        if sort.value not in allowed_sorts(type_):
            raise HTTPException(status_code=422, detail="sort not allowed")
        # 全库混排：type 为空、无任何过滤、默认排序时，资源与合集按时间混排（offset 分页）
        mixed_ok = (
            type_ is None
            and (status is None or status == ResourceStatus.ACTIVE)
            and not query
            and not tags
            and category_id is None
            and sort.value == "createdAt"
            and order == "desc"
            and after_key is None
        )
        if mixed_ok:
            items, total = await self._resources.list_mixed(limit, offset)
            return ResourcePage(
                items=items,
                total=total,
                limit=limit,
                offset=offset,
                has_more=(offset + limit) < total,
            )
        fetch = limit + 1
        cursor_key = after_key
        if cursor_key is None and after_created_at is not None and sort.value == "createdAt":
            cursor_key = after_created_at
        use_keyset = cursor_key is not None and after_id is not None
        items, keys = await self._resources.list_with_sort_keys(
            type_,
            status,
            fetch,
            0 if use_keyset else offset,
            order,
            sort=sort.value,
            q=query,
            tag_ids=tags,
            category_id=category_id,
            after_key=cursor_key if use_keyset else None,
            after_id=after_id if use_keyset else None,
        )
        has_more = len(items) > limit
        items = items[:limit]
        keys = keys[:limit]
        total = await self._resources.count(
            type_, status, q=query, tag_ids=tags, category_id=category_id
        )
        last = items[-1] if items else None
        next_key = keys[-1] if has_more and keys else None
        next_created = next_key if has_more and sort.value == "createdAt" else None
        return ResourcePage(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more,
            next_created_at=next_created,
            next_id=last.id if has_more and last is not None else None,
            next_key=next_key,
        )

    async def patch(self, resource_id: int, body: ResourcePatch) -> Resource | None:
        """部分更新标题/描述/评分；可选按名绑定分类、整表替换标签。"""
        existing = await self._resources.get(resource_id)
        if existing is None:
            return None
        data = body.model_dump(exclude_unset=True)
        data.pop("tag_names", None)
        data.pop("category_name", None)
        data.pop("exif_taken_at", None)
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
        if "exif_taken_at" in body.model_fields_set:
            if existing.type != ResourceType.IMAGE:
                raise ValueError("exif taken at only for image")
            raw_taken = body.exif_taken_at
            if raw_taken is None or (isinstance(raw_taken, str) and not raw_taken.strip()):
                normalized = None
            else:
                normalized = normalize_taken_at(raw_taken)
                if normalized is None:
                    raise ValueError("invalid taken at")
            primary = await self._resources.get_file_by_role(resource_id, FILE_ROLE_PRIMARY)
            if primary is None:
                raise ValueError("primary file missing")
            await self._resources.update_file_exif_taken_at(primary.id, normalized, commit=False)
        await self._resources.commit()
        return await self._resources.get(resource_id)

    async def replace_cover(self, resource_id: int, body: CoverReplace) -> Resource | None:
        """复制本机图片为 cover 角色，不改 primary。图片禁止。"""
        src = Path(body.path)
        if not src.is_file() or src.suffix.lower() not in COVER_EXTENSIONS:
            raise ValueError("invalid cover path")
        existing = await self._resources.get(resource_id)
        if existing is None or existing.id is None:
            return None
        if not allows_user_cover(existing.type):
            raise CoverNotAllowedError()
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
        from app.library.application.covers.origin import COVER_ORIGIN_USER

        ok = await attach_cover_image(
            self._resources,
            existing,
            package,
            src,
            COVER_ORIGIN_USER,
            honor_user_lock=False,
        )
        if not ok:
            raise ValueError("cover write failed")
        return await self._resources.get(resource_id)

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

    async def batch(
        self, action: str, ids: list[int], tag_names: list[str] | None = None
    ) -> ResourceBatchResult:
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
        names = [name.strip() for name in (tag_names or []) if name.strip()]
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
                elif action == "add_tags":
                    if not names:
                        failed.append(ResourceBatchFailedItem(id=rid, message="empty tags"))
                    else:
                        await self._resources.add_tags_union(rid, names)
                        ok.append(rid)
                else:
                    failed.append(ResourceBatchFailedItem(id=rid, message="invalid action"))
            except InvalidStateError:
                failed.append(ResourceBatchFailedItem(id=rid, message="resource is not trashed"))
            except Exception:
                await self._resources.rollback()
                logger.exception("批量操作失败 id=%s action=%s", rid, action)
                failed.append(ResourceBatchFailedItem(id=rid, message="operation failed"))
        return ResourceBatchResult(ok=ok, failed=failed)


"""合集用例：CRUD + 成员增删排序。标题空白 422；合集不存在 404；资源不存在 422。"""


class CollectionService:
    def __init__(self, collections: CollectionRepository, resources: ResourceRepository):
        self._collections = collections
        self._resources = resources

    async def list(self) -> list[Collection]:
        return await self._collections.list()

    async def create(self, title: str, description: str | None) -> Collection:
        if not (title or "").strip():
            raise HTTPException(status_code=422, detail="title required")
        return await self._collections.create(title, description)

    async def get(self, collection_id: int) -> Collection:
        collection = await self._collections.get(collection_id)
        if collection is None:
            raise HTTPException(status_code=404, detail="collection not found")
        return collection

    async def patch(self, collection_id: int, title: str | None, description: str | None) -> Collection:
        existing = await self._collections.get(collection_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="collection not found")
        next_title = title if title is not None else existing.title
        if not next_title.strip():
            raise HTTPException(status_code=422, detail="title required")
        next_desc = description if description is not None else existing.description
        updated = await self._collections.rename(collection_id, next_title, next_desc)
        assert updated is not None
        return updated

    async def delete(self, collection_id: int) -> None:
        if not await self._collections.delete(collection_id):
            raise HTTPException(status_code=404, detail="collection not found")

    async def members(self, collection_id: int) -> list[Resource]:
        await self.get(collection_id)
        return await self._collections.members(collection_id)

    async def add_item(self, collection_id: int, resource_id: int) -> None:
        await self.get(collection_id)
        if await self._resources.get(resource_id) is None:
            raise HTTPException(status_code=422, detail="resource not found")
        await self._collections.add_item(collection_id, resource_id)

    async def remove_item(self, collection_id: int, resource_id: int) -> None:
        await self.get(collection_id)
        await self._collections.remove_item(collection_id, resource_id)

    async def move_item(self, collection_id: int, resource_id: int, direction: str) -> None:
        await self.get(collection_id)
        await self._collections.move_item(collection_id, resource_id, direction)

    async def collections_of(self, resource_id: int) -> list[Collection]:
        return await self._collections.collections_of(resource_id)

    async def export(self, collection_id: int, target_dir: str) -> CollectionExportResult:
        """导出合集成员主文件到目标目录（按合集顺序编号命名；缺失文件跳过）。"""
        await self.get(collection_id)
        members = await self._collections.members(collection_id)
        if not members:
            raise HTTPException(status_code=422, detail="collection has no members")
        target = Path(target_dir).resolve()
        if not target.is_dir():
            raise HTTPException(status_code=400, detail="target directory not found")
        exported = 0
        skipped = 0
        for index, resource in enumerate(members, start=1):
            file_row = await self._resources.get_file_by_role(
                resource.id, FILE_ROLE_PRIMARY
            ) if resource.id is not None else None
            if file_row is None or not file_row.path:
                skipped += 1
                continue
            source = Path(file_row.path)
            if not source.is_file():
                skipped += 1
                continue
            name = export_name(index, resource.title, source.suffix)
            try:
                shutil.copy2(source, target / name)
                exported += 1
            except OSError:
                skipped += 1
        return CollectionExportResult(
            exported=exported, skipped=skipped, target_dir=str(target)
        )

