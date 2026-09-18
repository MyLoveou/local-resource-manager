"""复制入库用例。"""

from __future__ import annotations

import asyncio
import hashlib
import os
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.library.application.importers import importer_for
from app.library.application.ingest.placement import (
    comic_pages,
    copy_tree_filtered,
    find_folder_cover,
    find_launch,
    normalize_path,
)
from app.library.domain.type_profile import ingest_kind, profile_for
from app.library.application.thumbnails import source_for_grid_thumbnail
from app.library.application.packages import ResourcePackage, layout_for
from app.library.application.packages.layouts import PackageLayout
from app.library.application.packages.resource_package import default_library_store
from app.library.application.media_probe import ProbeFields, probe_media
from app.library.application.series_plan import PlannedItem, plan_series_videos
from app.library.infrastructure.import_job_store import ImportJobState
from app.library.infrastructure.repositories import ResourceRepository
from app.shared.config import settings
from app.shared.fs.file_ops import FileOps
from app.shared.log import logger
from app.shared.media_types import (
    FILE_ROLE_COVER,
    FILE_ROLE_EPISODE,
    FILE_ROLE_EXTRA,
    FILE_ROLE_LAUNCH,
    FILE_ROLE_PAGE,
    FILE_ROLE_PRIMARY,
    FILE_ROLE_THUMBNAIL,
)
from app.shared.models import Resource, ResourceStatus, ResourceType, StorageKind


def hash_file(path: Path) -> tuple[str, int]:
    """sha256 与字节大小。"""
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def import_cpu_workers() -> int:
    """CPU 工人上限：min(4, CPU-1)，至少 1。"""
    n = os.cpu_count() or 2
    return max(1, min(4, n - 1))


class ImportService:
    """列举 → 去重 → 建资源 → Layout 复制 → 写 files。"""

    def __init__(
        self,
        resources: ResourceRepository | None = None,
        *,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        store_root: Path | None = None,
        file_ops: FileOps | None = None,
        probe: Callable[[ResourceType, Path], ProbeFields] | None = None,
        workers: int | None = None,
    ) -> None:
        self._resources = resources
        self._session_factory = session_factory
        self._store_root = store_root or default_library_store(settings.db_path)
        self._ops = file_ops or FileOps()
        self._probe = probe or probe_media
        self._workers = workers if workers is not None else import_cpu_workers()

    async def run(
        self,
        job: ImportJobState,
        type_: ResourceType,
        source_kind: str,
        paths: list[str],
        storage_kind: str | None = None,
    ) -> None:
        importer = importer_for(type_)
        layout = layout_for(type_)
        profile = profile_for(type_)
        if importer is None or layout is None or profile is None:
            job.skipped_error += 1
            return
        storage = StorageKind(storage_kind) if storage_kind else profile.default_storage
        if storage not in profile.allowed_storage:
            job.skipped_error += 1
            return
        kind = ingest_kind(type_)
        if kind == "series":
            await self._run_series(job, type_, layout, importer, source_kind, paths)
            return
        if kind == "package" and source_kind != "file":
            await self._run_package(job, type_, layout, paths, storage)
            return
        candidates = await asyncio.to_thread(importer.collect, source_kind, [Path(p) for p in paths])
        job.total = len(candidates)
        job.phase = "hash"
        if self._session_factory is not None:
            await self._run_pooled(job, type_, layout, candidates)
            return
        if self._resources is None:
            raise RuntimeError("ImportService needs resources or session_factory")
        for candidate in candidates:
            await self._ingest_one(self._resources, job, type_, layout, candidate)
            job.done += 1
            await asyncio.sleep(0)

    async def _run_pooled(
        self,
        job: ImportJobState,
        type_: ResourceType,
        layout: PackageLayout,
        candidates: list[Path],
    ) -> None:
        factory = self._session_factory
        assert factory is not None
        sem = asyncio.Semaphore(self._workers)

        async def one(source: Path) -> None:
            async with sem:
                last_error: Exception | None = None
                for attempt in range(4):
                    try:
                        async with factory() as session:
                            repo = ResourceRepository(session)
                            await self._ingest_one(repo, job, type_, layout, source)
                        last_error = None
                        break
                    except OperationalError as exc:
                        last_error = exc
                        await asyncio.sleep(0.05 * (attempt + 1))
                if last_error is not None:
                    logger.warning("导入写库重试耗尽 %s: %s", source, last_error)
                    job.skipped_error += 1
                job.done += 1
                await asyncio.sleep(0)

        await asyncio.gather(*(one(path) for path in candidates))

    async def _run_series(
        self,
        job: ImportJobState,
        type_: ResourceType,
        layout: PackageLayout,
        importer,
        source_kind: str,
        paths: list[str],
    ) -> None:
        """一目录一部作品。"""
        root = Path(paths[0])
        videos = await asyncio.to_thread(importer.collect, source_kind, [root])
        job.total = 1
        job.phase = "hash"
        if self._session_factory is not None:
            last_error: Exception | None = None
            for attempt in range(4):
                try:
                    async with self._session_factory() as session:
                        repo = ResourceRepository(session)
                        await self._ingest_series(repo, job, type_, layout, root, videos)
                    last_error = None
                    break
                except OperationalError as exc:
                    last_error = exc
                    await asyncio.sleep(0.05 * (attempt + 1))
            if last_error is not None:
                logger.warning("系列导入写库重试耗尽 %s: %s", root, last_error)
                job.skipped_error += 1
            job.done = 1
            return
        if self._resources is None:
            raise RuntimeError("ImportService needs resources or session_factory")
        await self._ingest_series(self._resources, job, type_, layout, root, videos)
        job.done = 1

    async def _try_register_thumbnail(
        self,
        resources: ResourceRepository,
        resource_id: int,
        package: ResourcePackage,
        type_: ResourceType,
        role_paths: dict[str, Path],
    ) -> None:
        """缩略图失败只记日志，不回滚已复制的资源。"""
        thumb_src = source_for_grid_thumbnail(type_, role_paths)
        if thumb_src is None:
            return
        try:
            thumb_dest = await asyncio.to_thread(package.put_thumbnail, thumb_src)
            if thumb_dest is None:
                return
            thumb_size = (await asyncio.to_thread(thumb_dest.stat)).st_size
            await resources.add_file(
                resource_id,
                path=str(thumb_dest),
                sha256=None,
                size=thumb_size,
                format_=thumb_dest.suffix.lower().lstrip("."),
                role=FILE_ROLE_THUMBNAIL,
                commit=True,
            )
        except Exception as exc:
            logger.warning("缩略图登记失败 resource=%s: %s", resource_id, exc)
            await resources.rollback()

    async def _ingest_one(
        self,
        resources: ResourceRepository,
        job: ImportJobState,
        type_: ResourceType,
        layout: PackageLayout,
        source: Path,
    ) -> None:
        try:
            digest, size = await asyncio.to_thread(hash_file, source)
        except OSError as exc:
            logger.warning("导入跳过 %s: %s", source, exc)
            job.skipped_error += 1
            return
        if await resources.file_exists_by_sha256(digest):
            job.skipped_duplicate += 1
            return
        extra = {"importSourcePath": str(source)}
        package: ResourcePackage | None = None
        try:
            resource = await resources.create(
                Resource(
                    type=type_,
                    title=source.stem,
                    status=ResourceStatus.ACTIVE,
                    storage_kind=StorageKind.OWNED,
                    extra=extra,
                ),
                commit=False,
            )
            assert resource.id is not None
            package = ResourcePackage(
                self._store_root,
                type_,
                resource.id,
                self._ops,
                cover_falls_back_to_primary=layout.cover_falls_back_to_primary,
            )
            job.phase = "copy"
            role_paths = await asyncio.to_thread(layout.place_primary, package, source)
            job.phase = "probe"
            for role, dest in role_paths.items():
                probed = ProbeFields()
                if role == FILE_ROLE_PRIMARY:
                    probed = await asyncio.to_thread(self._probe, type_, dest)
                file_size = size
                if role != FILE_ROLE_PRIMARY:
                    file_size = (await asyncio.to_thread(dest.stat)).st_size
                await resources.add_file(
                    resource.id,
                    path=str(dest),
                    sha256=digest if role == FILE_ROLE_PRIMARY else None,
                    size=file_size,
                    format_=dest.suffix.lower().lstrip("."),
                    role=role,
                    duration=probed.duration,
                    width=probed.width,
                    height=probed.height,
                    codec=probed.codec,
                    fps=probed.fps,
                    bitrate=probed.bitrate,
                    commit=False,
                )
            cover = package.resolve_cover(role_paths)
            if cover is not None:
                resource.cover_path = f"/library/resources/{resource.id}/content"
                await resources.update(resource.id, resource, commit=False)
            await resources.commit()
            job.imported += 1
            job.phase = "thumb"
            await self._try_register_thumbnail(resources, resource.id, package, type_, role_paths)
        except IntegrityError:
            await resources.rollback()
            if package is not None:
                self._ops.remove_tree(package.root)
            job.skipped_duplicate += 1
        except OSError as exc:
            await resources.rollback()
            if package is not None:
                self._ops.remove_tree(package.root)
            logger.warning("导入跳过 %s: %s", source, exc)
            job.skipped_error += 1

    async def _ingest_series(
        self,
        resources: ResourceRepository,
        job: ImportJobState,
        type_: ResourceType,
        layout: PackageLayout,
        root: Path,
        videos: list[Path],
    ) -> None:
        """整夹进一部作品；集不是独立 Resource。"""
        plan = plan_series_videos(root, videos)
        if plan is None:
            logger.warning("系列目录无法自动识别 %s", root)
            job.skipped_error += 1
            return
        hashes: list[tuple[PlannedItem, str, int]] = []
        for item in plan:
            try:
                digest, size = await asyncio.to_thread(hash_file, item.src)
            except OSError as exc:
                logger.warning("系列跳过文件 %s: %s", item.src, exc)
                job.skipped_error += 1
                return
            if await resources.file_exists_by_sha256(digest):
                job.skipped_duplicate += 1
                return
            hashes.append((item, digest, size))

        package: ResourcePackage | None = None
        try:
            resource = await resources.create(
                Resource(
                    type=type_,
                    title=root.name,
                    status=ResourceStatus.ACTIVE,
                    storage_kind=StorageKind.OWNED,
                    extra={"importSourcePath": str(root)},
                ),
                commit=False,
            )
            assert resource.id is not None
            package = ResourcePackage(
                self._store_root,
                type_,
                resource.id,
                self._ops,
                cover_falls_back_to_primary=layout.cover_falls_back_to_primary,
            )
            job.phase = "copy"
            season_ids: dict[int, int] = {}
            role_paths: dict[str, Path] = {}
            first_dest: Path | None = None
            for index, (item, digest, size) in enumerate(hashes):
                dest = await asyncio.to_thread(package.put_relative, item.src, item.dest_rel)
                job.phase = "probe"
                probed = await asyncio.to_thread(self._probe, type_, dest)
                if index == 0:
                    role = FILE_ROLE_PRIMARY
                    first_dest = dest
                    role_paths[FILE_ROLE_PRIMARY] = dest
                elif item.kind == "extra":
                    role = FILE_ROLE_EXTRA
                else:
                    role = FILE_ROLE_EPISODE
                file_row = await resources.add_file(
                    resource.id,
                    path=str(dest),
                    sha256=digest,
                    size=size,
                    format_=dest.suffix.lower().lstrip("."),
                    role=role,
                    duration=probed.duration,
                    width=probed.width,
                    height=probed.height,
                    codec=probed.codec,
                    fps=probed.fps,
                    bitrate=probed.bitrate,
                    commit=False,
                )
                if item.kind == "episode":
                    assert item.episode is not None
                    season_id = season_ids.get(item.season)
                    if season_id is None:
                        season_row = await resources.add_season(
                            resource.id,
                            item.season,
                            sort_index=item.season,
                            commit=False,
                        )
                        season_id = season_row.id
                        season_ids[item.season] = season_id
                    await resources.add_episode(
                        season_id,
                        file_row.id,
                        item.episode,
                        sort_index=item.episode,
                        commit=False,
                    )
                else:
                    await resources.add_extra(
                        resource.id,
                        file_row.id,
                        title=item.title or item.src.stem,
                        sort_index=index,
                        commit=False,
                    )
            if first_dest is not None:
                resource.cover_path = f"/library/resources/{resource.id}/content"
                await resources.update(resource.id, resource, commit=False)
            await resources.commit()
            job.imported += 1
            job.phase = "thumb"
            await self._try_register_thumbnail(resources, resource.id, package, type_, role_paths)
        except IntegrityError:
            await resources.rollback()
            if package is not None:
                self._ops.remove_tree(package.root)
            job.skipped_duplicate += 1
        except OSError as exc:
            await resources.rollback()
            if package is not None:
                self._ops.remove_tree(package.root)
            logger.warning("系列导入跳过 %s: %s", root, exc)
            job.skipped_error += 1

    async def _run_package(
        self,
        job: ImportJobState,
        type_: ResourceType,
        layout: PackageLayout,
        paths: list[str],
        storage: StorageKind,
    ) -> None:
        """一目录一部作品。"""
        root = Path(paths[0])
        job.total = 1
        job.phase = "hash"
        if self._session_factory is not None:
            last_error: Exception | None = None
            for attempt in range(4):
                try:
                    async with self._session_factory() as session:
                        repo = ResourceRepository(session)
                        await self._ingest_package(repo, job, type_, layout, root, storage)
                    last_error = None
                    break
                except OperationalError as exc:
                    last_error = exc
                    await asyncio.sleep(0.05 * (attempt + 1))
            if last_error is not None:
                logger.warning("包导入写库重试耗尽 %s: %s", root, last_error)
                job.skipped_error += 1
            job.done = 1
            return
        if self._resources is None:
            raise RuntimeError("ImportService needs resources or session_factory")
        await self._ingest_package(self._resources, job, type_, layout, root, storage)
        job.done = 1

    async def _ingest_package(
        self,
        resources: ResourceRepository,
        job: ImportJobState,
        type_: ResourceType,
        layout: PackageLayout,
        root: Path,
        storage: StorageKind,
    ) -> None:
        profile = profile_for(type_)
        if profile is None or profile.package_contents is None:
            job.skipped_error += 1
            return
        if profile.package_contents == "image_pages":
            await self._ingest_comic(resources, job, type_, layout, root)
            return
        await self._ingest_game(resources, job, type_, layout, root, storage)

    async def _ingest_comic(
        self,
        resources: ResourceRepository,
        job: ImportJobState,
        type_: ResourceType,
        layout: PackageLayout,
        root: Path,
    ) -> None:
        pages = comic_pages(root)
        if not pages:
            job.skipped_error += 1
            return
        try:
            digest, size = await asyncio.to_thread(hash_file, pages[0])
        except OSError as exc:
            logger.warning("漫画导入跳过 %s: %s", root, exc)
            job.skipped_error += 1
            return
        if await resources.file_exists_by_sha256(digest):
            job.skipped_duplicate += 1
            return
        package: ResourcePackage | None = None
        try:
            resource = await resources.create(
                Resource(
                    type=type_,
                    title=root.name,
                    status=ResourceStatus.ACTIVE,
                    storage_kind=StorageKind.OWNED,
                    extra={"importSourcePath": str(root)},
                ),
                commit=False,
            )
            assert resource.id is not None
            package = ResourcePackage(
                self._store_root,
                type_,
                resource.id,
                self._ops,
                cover_falls_back_to_primary=layout.cover_falls_back_to_primary,
            )
            job.phase = "copy"
            role_paths: dict[str, Path] = {}
            for index, src in enumerate(pages):
                rel = f"pages/{index + 1:03d}{src.suffix.lower()}"
                dest = await asyncio.to_thread(package.put_relative, src, rel)
                role = FILE_ROLE_PRIMARY if index == 0 else FILE_ROLE_PAGE
                if index == 0:
                    role_paths[FILE_ROLE_PRIMARY] = dest
                page_digest, page_size = (digest, size) if index == 0 else (None, None)
                if index != 0:
                    page_size = (await asyncio.to_thread(dest.stat)).st_size
                await resources.add_file(
                    resource.id,
                    path=str(dest),
                    sha256=page_digest,
                    size=page_size if page_size is not None else size,
                    format_=dest.suffix.lower().lstrip("."),
                    role=role,
                    commit=False,
                )
            resource.cover_path = f"/library/resources/{resource.id}/content"
            await resources.update(resource.id, resource, commit=False)
            await resources.commit()
            job.imported += 1
            job.phase = "thumb"
            await self._try_register_thumbnail(resources, resource.id, package, type_, role_paths)
        except IntegrityError:
            await resources.rollback()
            if package is not None:
                self._ops.remove_tree(package.root)
            job.skipped_duplicate += 1
        except OSError as exc:
            await resources.rollback()
            if package is not None:
                self._ops.remove_tree(package.root)
            logger.warning("漫画导入跳过 %s: %s", root, exc)
            job.skipped_error += 1

    async def _ingest_game(
        self,
        resources: ResourceRepository,
        job: ImportJobState,
        type_: ResourceType,
        layout: PackageLayout,
        root: Path,
        storage: StorageKind,
    ) -> None:
        launch_src = find_launch(root)
        package: ResourcePackage | None = None
        try:
            digest: str | None = None
            size: int | None = None
            launch_store: Path | None = None
            if launch_src is not None:
                digest, size = await asyncio.to_thread(hash_file, launch_src)
                indexed_path = normalize_path(launch_src)
                if storage == StorageKind.INDEXED and await resources.file_exists_by_path(indexed_path):
                    job.skipped_duplicate += 1
                    return
                if digest and await resources.file_exists_by_sha256(digest):
                    job.skipped_duplicate += 1
                    return
            resource = await resources.create(
                Resource(
                    type=type_,
                    title=root.name,
                    status=ResourceStatus.ACTIVE,
                    storage_kind=storage,
                    extra={"importSourcePath": str(root.resolve())},
                ),
                commit=False,
            )
            assert resource.id is not None
            package = ResourcePackage(
                self._store_root,
                type_,
                resource.id,
                self._ops,
                cover_falls_back_to_primary=layout.cover_falls_back_to_primary,
            )
            job.phase = "copy"
            role_paths: dict[str, Path] = {}
            if storage == StorageKind.OWNED:
                await asyncio.to_thread(copy_tree_filtered, self._ops, root, package.root)
                if launch_src is not None:
                    launch_store = package.root / launch_src.relative_to(root)
            else:
                cover_src = find_folder_cover(root)
                if cover_src is not None:
                    dest = await asyncio.to_thread(package.put_cover, cover_src)
                    role_paths[FILE_ROLE_COVER] = dest
                    cover_size = (await asyncio.to_thread(dest.stat)).st_size
                    await resources.add_file(
                        resource.id,
                        path=str(dest),
                        sha256=None,
                        size=cover_size,
                        format_=dest.suffix.lower().lstrip("."),
                        role=FILE_ROLE_COVER,
                        commit=False,
                    )
                if launch_src is not None:
                    launch_store = launch_src
            if launch_store is not None:
                path_value = (
                    normalize_path(launch_store)
                    if storage == StorageKind.INDEXED
                    else str(launch_store)
                )
                await resources.add_file(
                    resource.id,
                    path=path_value,
                    sha256=digest,
                    size=size,
                    format_=launch_store.suffix.lower().lstrip("."),
                    role=FILE_ROLE_LAUNCH,
                    commit=False,
                )
                role_paths[FILE_ROLE_PRIMARY] = launch_store
            await resources.commit()
            job.imported += 1
            job.phase = "thumb"
            await self._try_register_thumbnail(resources, resource.id, package, type_, role_paths)
        except IntegrityError:
            await resources.rollback()
            if package is not None and storage == StorageKind.OWNED:
                self._ops.remove_tree(package.root)
            elif package is not None and storage == StorageKind.INDEXED:
                self._ops.remove_tree(package.root)
            job.skipped_duplicate += 1
        except OSError as exc:
            await resources.rollback()
            if package is not None:
                self._ops.remove_tree(package.root)
            logger.warning("游戏导入跳过 %s: %s", root, exc)
            job.skipped_error += 1

