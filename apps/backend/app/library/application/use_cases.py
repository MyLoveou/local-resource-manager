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
    CategoryNode,
    CollectionExportResult,
    CoverReplace,
    HomeSummary,
    Overview,
    ResourceBatchFailedItem,
    ResourceBatchResult,
    ResourcePage,
    ResourcePatch,
    ResourceSortField,
    ResourceStats,
    SavedViewCreate,
    SavedViewPatch,
    SubtitleAdd,
    TaskSummary,
    TodoCreate,
    TodoPatch,
)
from app.library.application.workbench import active_work, recent_consumption
from app.library.application.subtitle_naming import original_stem_from_extra, subtitle_dest_name
from app.library.domain.type_profile import allows_user_cover
from app.library.infrastructure.repositories import (
    CategoryRepository,
    CollectionRepository,
    ResourceRepository,
    SavedViewRepository,
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
    Category,
    Collection,
    Resource,
    ResourceStatus,
    ResourceType,
    SavedView,
    SavedViewFilters,
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
        categories: CategoryRepository | None = None,
        collections: CollectionRepository | None = None,
        saved_views: SavedViewRepository | None = None,
    ):
        self._resources = resources
        self._tasks = tasks
        self._ops = file_ops or FileOps()
        self._store = store_root or default_library_store(settings.db_path)
        self._categories = categories or CategoryRepository(resources.session)
        self._collections = collections or CollectionRepository(resources.session)
        self._saved_views = saved_views or SavedViewRepository(resources.session)

    async def overview(self) -> Overview:
        """首页概览：统计 + 预览图 + 最近添加 + 合集 + 已保存时间线。"""
        stats = await self._resources.stats()
        stats["previews_by_type"] = await self._resources.previews_by_type()
        return Overview(
            stats=ResourceStats(**stats),
            recent=await self._resources.recent(limit=12),
            tasks=TaskSummary(**await self._tasks.summary()),
            active_work=await active_work(self._resources.session),
            recent_consumption=await recent_consumption(self._resources.session),
        )

    async def home(self) -> HomeSummary:
        """资源工作台聚合：在 overview 上补合集与保存时间线。"""
        overview = await self.overview()
        collections = await self._collections.list()
        saved_views = await self._saved_views.list("timeline")
        collection_cards = [
            {
                "cardType": "collection",
                "id": item.id,
                "title": item.title,
                "memberCount": item.member_count,
                "updatedAt": item.updated_at,
                "previewThumbnails": item.preview_thumbnails,
            }
            for item in collections
            if item.id is not None
        ]
        return HomeSummary(
            stats=overview.stats,
            recent=overview.recent,
            tasks=overview.tasks,
            active_work=overview.active_work,
            recent_consumption=overview.recent_consumption,
            collections=collection_cards,
            saved_timelines=saved_views,
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
        category_ids: list[int] | None = None,
        uncategorized: bool = False,
        after_key: str | None = None,
        include_collected: bool = False,
        taken_date: str | None = None,
        untimed: bool = False,
        timeline_visible: bool | None = None,
        timeline_media: bool = False,
        map_visible: bool | None = None,
        map_only: bool = False,
        character_ids: list[int] | None = None,
        person_ids: list[int] | None = None,
    ) -> ResourcePage:
        """分页列表。q/tagIds/categoryId/sort 服务端过滤；非法 sort 422。

        默认不显示已归集到合集的资源（include_collected=True 或有关键词时显示）。
        """
        query = normalize_q(q)
        tags = tag_ids or []
        category_filter = list(dict.fromkeys(category_ids or ([] if category_id is None else [category_id])))
        expanded_category_ids = await self._categories.descendant_ids(category_filter)
        if sort.value not in allowed_sorts(type_):
            raise HTTPException(status_code=422, detail="sort not allowed")
        exclude_collected = (
            not include_collected
            and not query
            and (status is None or status == ResourceStatus.ACTIVE)
        )
        # 全库混排：type 为空、无任何过滤、默认排序时，资源与合集按时间混排（offset 分页）
        mixed_ok = (
            type_ is None
            and (status is None or status == ResourceStatus.ACTIVE)
            and not query
            and not tags
            and category_id is None
            and not category_ids
            and not uncategorized
            and sort.value == "createdAt"
            and order == "desc"
            and after_key is None
            and taken_date is None
            and not untimed
            and timeline_visible is None
            and not timeline_media
            and map_visible is None
            and not map_only
            and not character_ids
            and not person_ids
        )
        if mixed_ok:
            items, total = await self._resources.list_mixed(
                limit, offset, exclude_collected=exclude_collected
            )
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
            category_id=None,
            category_ids=expanded_category_ids,
            uncategorized=uncategorized,
            after_key=cursor_key if use_keyset else None,
            after_id=after_id if use_keyset else None,
            exclude_collected=exclude_collected,
            taken_date=taken_date,
            untimed=untimed,
            timeline_visible=timeline_visible,
            timeline_media=timeline_media,
            map_visible=map_visible,
            map_only=map_only,
            character_ids=character_ids,
            person_ids=person_ids,
        )
        has_more = len(items) > limit
        items = items[:limit]
        keys = keys[:limit]
        total = await self._resources.count(
            type_,
            status,
            q=query,
            tag_ids=tags,
            category_id=None,
            category_ids=expanded_category_ids,
            uncategorized=uncategorized,
            exclude_collected=exclude_collected,
            taken_date=taken_date,
            untimed=untimed,
            timeline_visible=timeline_visible,
            timeline_media=timeline_media,
            map_visible=map_visible,
            map_only=map_only,
            character_ids=character_ids,
            person_ids=person_ids,
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
        data.pop("category_ids", None)
        data.pop("exif_taken_at", None)
        data.pop("character_ids", None)
        data.pop("person_ids", None)
        if "author" in data:
            raw_author = data["author"]
            data["author"] = raw_author.strip() if isinstance(raw_author, str) and raw_author.strip() else None
        for key, value in data.items():
            setattr(existing, key, value)
        existing._touch()
        updated = await self._resources.update(resource_id, existing, commit=False)
        if updated is None:
            return None
        if "category_ids" in body.model_fields_set:
            ids = list(dict.fromkeys(body.category_ids or []))
            categories = [await self._categories.get(category_id) for category_id in ids]
            if any(category is None for category in categories):
                raise HTTPException(status_code=422, detail="category not found")
            if any(category.type != existing.type for category in categories if category is not None):
                raise HTTPException(status_code=422, detail="category type mismatch")
            await self._resources.set_categories(resource_id, ids, commit=False)
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
        if "character_ids" in body.model_fields_set:
            ids = list(dict.fromkeys(body.character_ids or []))
            from app.library.infrastructure.repositories import CharacterRepository
            character_repo = CharacterRepository(self._resources.session)
            selected = [await character_repo.get(character_id) for character_id in ids]
            if any(character is None for character in selected):
                raise HTTPException(status_code=422, detail="character not found")
            await character_repo.set_resources(resource_id, ids, commit=False)
        if "person_ids" in body.model_fields_set:
            ids = list(dict.fromkeys(body.person_ids or []))
            from app.library.infrastructure.repositories import PersonRepository
            person_repo = PersonRepository(self._resources.session)
            selected = [await person_repo.get(person_id) for person_id in ids]
            if any(person is None for person in selected):
                raise HTTPException(status_code=422, detail="person not found")
            await person_repo.set_resources(resource_id, ids, commit=False)
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
        self,
        action: str,
        ids: list[int],
        tag_names: list[str] | None = None,
        category_ids: list[int] | None = None,
        character_ids: list[int] | None = None,
        person_ids: list[int] | None = None,
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
        category_ids = list(dict.fromkeys(category_ids or []))
        character_ids = list(dict.fromkeys(character_ids or []))
        person_ids = list(dict.fromkeys(person_ids or []))
        from app.library.infrastructure.repositories import CharacterRepository, PersonRepository
        character_repo = CharacterRepository(self._resources.session)
        person_repo = PersonRepository(self._resources.session)
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
                elif action in ("add_categories", "remove_categories"):
                    if not category_ids:
                        failed.append(ResourceBatchFailedItem(id=rid, message="empty categories"))
                        continue
                    resource = await self._resources.get(rid)
                    if resource is None:
                        failed.append(ResourceBatchFailedItem(id=rid, message="resource not found"))
                        continue
                    selected = [await self._categories.get(cid) for cid in category_ids]
                    if any(item is None or item.type != resource.type for item in selected):
                        failed.append(ResourceBatchFailedItem(id=rid, message="category type mismatch"))
                        continue
                    current = {
                        category.id for category in (resource.categories or []) if category.id is not None
                    }
                    if action == "add_categories":
                        current.update(int(cid) for cid in category_ids)
                    else:
                        current.difference_update(int(cid) for cid in category_ids)
                    await self._resources.set_categories(rid, sorted(current))
                    ok.append(rid)
                elif action in ("add_characters", "remove_characters"):
                    if not character_ids:
                        failed.append(ResourceBatchFailedItem(id=rid, message="empty characters"))
                        continue
                    selected = [await character_repo.get(cid) for cid in character_ids]
                    if any(item is None for item in selected):
                        failed.append(ResourceBatchFailedItem(id=rid, message="character not found"))
                        continue
                    if action == "add_characters":
                        await character_repo.add_resources([rid], character_ids)
                    else:
                        await character_repo.remove_resources([rid], character_ids)
                    ok.append(rid)
                elif action in ("add_persons", "remove_persons"):
                    if not person_ids:
                        failed.append(ResourceBatchFailedItem(id=rid, message="empty persons"))
                        continue
                    selected = [await person_repo.get(pid) for pid in person_ids]
                    if any(item is None for item in selected):
                        failed.append(ResourceBatchFailedItem(id=rid, message="person not found"))
                        continue
                    if action == "add_persons":
                        await person_repo.add_resources([rid], person_ids)
                    else:
                        await person_repo.remove_resources([rid], person_ids)
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


class CategoryService:
    """每类型分类树：树查询、管理、资源分类校验。"""

    def __init__(self, categories: CategoryRepository, saved_views: SavedViewRepository):
        self._categories = categories
        self._saved_views = saved_views

    async def tree(self, type_: ResourceType) -> list[CategoryNode]:
        rows = await self._categories.list_rows(type_)
        counts = await self._categories.counts(type_)
        nodes: dict[int, CategoryNode] = {}
        for row in rows:
            nodes[row.id] = CategoryNode(
                id=row.id,
                type=type_,
                parent_id=row.parent_id,
                name=row.name,
                sort=row.sort,
                is_system=bool(row.is_system),
                count=counts.get(row.id, 0),
            )
        roots: list[CategoryNode] = []
        for node in nodes.values():
            parent = nodes.get(node.parent_id) if node.parent_id is not None else None
            if parent is None:
                roots.append(node)
            else:
                parent.children.append(node)
        visible = [
            node for node in roots
            if not (node.is_system and not node.children and node.count == 0)
        ]
        return sorted(visible, key=lambda item: (item.sort, item.name.lower()))

    async def create(
        self, type_: ResourceType, parent_id: int | None, name: str, sort: int
    ) -> Category:
        cleaned = (name or "").strip()
        if not cleaned:
            raise HTTPException(status_code=422, detail="name required")
        parent = await self._categories.get(parent_id) if parent_id is not None else None
        if parent_id is not None and parent is None:
            raise HTTPException(status_code=422, detail="parent not found")
        if parent is not None and parent.type != type_:
            raise HTTPException(status_code=422, detail="parent type mismatch")
        if await self._categories.depth(parent_id) + 1 > 4:
            raise HTTPException(status_code=422, detail="category depth exceeded")
        if await self._categories.name_exists(type_, parent_id, cleaned):
            raise HTTPException(status_code=409, detail="category name exists")
        return await self._categories.create(type_, parent_id, cleaned, sort)

    async def patch(
        self,
        category_id: int,
        *,
        name: str | None,
        parent_id: int | None,
        update_parent: bool,
        sort: int | None,
    ) -> Category:
        existing = await self._categories.get(category_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="category not found")
        if existing.is_system and (update_parent or (name is not None and name.strip() != existing.name)):
            raise HTTPException(status_code=409, detail="system category")
        next_name = existing.name if name is None else name.strip()
        if not next_name:
            raise HTTPException(status_code=422, detail="name required")
        next_parent = parent_id if update_parent else existing.parent_id
        if next_parent is not None:
            parent = await self._categories.get(next_parent)
            if parent is None or parent.type != existing.type:
                raise HTTPException(status_code=422, detail="parent type mismatch")
            descendants = await self._categories.descendant_ids([category_id])
            if next_parent in descendants:
                raise HTTPException(status_code=409, detail="category cycle")
            height = await self._categories.subtree_height(category_id)
            if await self._categories.depth(next_parent) + height > 4:
                raise HTTPException(status_code=422, detail="category depth exceeded")
        if await self._categories.name_exists(
            existing.type, next_parent, next_name, exclude_id=category_id
        ):
            raise HTTPException(status_code=409, detail="category name exists")
        updated = await self._categories.update(
            category_id,
            name=next_name,
            parent_id=next_parent,
            sort=sort,
            update_parent=update_parent,
        )
        assert updated is not None
        return updated

    async def delete(self, category_id: int) -> None:
        existing = await self._categories.get(category_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="category not found")
        if existing.is_system:
            raise HTTPException(status_code=409, detail="system category")
        if await self._categories.has_children(category_id):
            raise HTTPException(status_code=409, detail="category has children")
        if await self._categories.has_resources(category_id):
            raise HTTPException(status_code=409, detail="category has resources")
        await self._categories.delete(category_id)
        await self._saved_views.remove_category(category_id)

    async def validate_ids(self, type_: ResourceType, ids: list[int]) -> list[int]:
        unique = list(dict.fromkeys(ids))
        categories = [await self._categories.get(category_id) for category_id in unique]
        if any(category is None for category in categories):
            raise HTTPException(status_code=422, detail="category not found")
        if any(category.type != type_ for category in categories if category is not None):
            raise HTTPException(status_code=422, detail="category type mismatch")
        return unique

    async def expand_ids(self, ids: list[int]) -> list[int]:
        return await self._categories.descendant_ids(ids)


class SavedViewService:
    """保存的时间线筛选器。"""

    def __init__(self, saved_views: SavedViewRepository, categories: CategoryRepository):
        self._saved_views = saved_views
        self._categories = categories

    async def list(self, scope: str | None = None, kind: str = "timeline") -> list[SavedView]:
        return await self._saved_views.list(kind, scope)

    async def get(self, view_id: int) -> SavedView:
        view = await self._saved_views.get(view_id)
        if view is None:
            raise HTTPException(status_code=404, detail="saved view not found")
        return view

    async def _validate_filters(self, filters: SavedViewFilters) -> None:
        for type_, rule in (
            (ResourceType.IMAGE, filters.image),
            (ResourceType.VIDEO, filters.video),
        ):
            ids = list(dict.fromkeys([*rule.include, *rule.exclude]))
            categories = [await self._categories.get(category_id) for category_id in ids]
            if any(category is None for category in categories):
                raise HTTPException(status_code=422, detail="category not found")
            if any(category.type != type_ for category in categories if category is not None):
                raise HTTPException(status_code=422, detail="category type mismatch")

    async def create(self, body: SavedViewCreate) -> SavedView:
        cleaned = body.name.strip()
        if not cleaned:
            raise HTTPException(status_code=422, detail="name required")
        scope = body.scope
        if "scope" not in body.model_fields_set and body.type is not None:
            scope = body.type.value
        await self._validate_filters(body.filters)
        if await self._saved_views.name_exists(body.kind, scope, cleaned):
            raise HTTPException(status_code=409, detail="saved view name exists")
        return await self._saved_views.create(
            kind=body.kind,
            scope=scope,
            name=cleaned,
            filters=body.filters,
            sort=body.sort,
        )

    async def patch(self, view_id: int, body: SavedViewPatch) -> SavedView:
        existing = await self.get(view_id)
        next_name = existing.name if body.name is None else body.name.strip()
        next_scope = body.scope or existing.scope
        if not next_name:
            raise HTTPException(status_code=422, detail="name required")
        next_filters = body.filters if body.filters is not None else existing.filters
        await self._validate_filters(next_filters)
        if await self._saved_views.name_exists(
            existing.kind, next_scope, next_name, exclude_id=view_id
        ):
            raise HTTPException(status_code=409, detail="saved view name exists")
        updated = await self._saved_views.update(
            view_id,
            scope=next_scope,
            name=next_name,
            filters=body.filters,
            sort=body.sort,
        )
        assert updated is not None
        return updated

    async def delete(self, view_id: int) -> None:
        await self.get(view_id)
        await self._saved_views.delete(view_id)


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

    async def add_items(self, collection_id: int, resource_ids: list[int]) -> tuple[int, int, int]:
        """批量加入；返回 (added, skipped, missing)。"""
        await self.get(collection_id)
        return await self._collections.add_items(collection_id, resource_ids)

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
                await asyncio.to_thread(shutil.copy2, source, target / name)
                exported += 1
            except OSError:
                skipped += 1
        return CollectionExportResult(
            exported=exported, skipped=skipped, target_dir=str(target)
        )

