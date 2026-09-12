"""复制入库用例。"""

from __future__ import annotations

import asyncio
import hashlib
import os
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.library.application.thumbnails import source_for_grid_thumbnail
from app.library.application.importers import importer_for
from app.library.application.packages import ResourcePackage, layout_for
from app.library.application.packages.layouts import PackageLayout
from app.library.application.packages.resource_package import default_library_store
from app.library.application.media_probe import ProbeFields, probe_media
from app.library.infrastructure.import_job_store import ImportJobState
from app.library.infrastructure.repositories import ResourceRepository
from app.shared.config import settings
from app.shared.fs.file_ops import FileOps
from app.shared.log import logger
from app.shared.media_types import FILE_ROLE_PRIMARY, FILE_ROLE_THUMBNAIL
from app.shared.models import Resource, ResourceStatus, ResourceType


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
    ) -> None:
        importer = importer_for(type_)
        layout = layout_for(type_)
        if importer is None or layout is None:
            job.skipped_error += 1
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
