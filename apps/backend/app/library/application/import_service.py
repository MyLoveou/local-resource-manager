"""复制入库用例。"""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from app.library.application.importers import importer_for
from app.library.application.packages import ResourcePackage, layout_for
from app.library.application.packages.layouts import PackageLayout
from app.library.application.packages.resource_package import default_library_store
from app.library.infrastructure.import_job_store import ImportJobState
from app.library.infrastructure.repositories import ResourceRepository
from app.shared.config import settings
from app.shared.fs.file_ops import FileOps
from app.shared.log import logger
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


class ImportService:
    """列举 → 去重 → 建资源 → Layout 复制 → 写 files。"""

    def __init__(
        self,
        resources: ResourceRepository,
        *,
        store_root: Path | None = None,
        file_ops: FileOps | None = None,
    ) -> None:
        self._resources = resources
        self._store_root = store_root or default_library_store(settings.db_path)
        self._ops = file_ops or FileOps()

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
        for candidate in candidates:
            await self._ingest_one(job, type_, layout, candidate)
            job.done += 1

    async def _ingest_one(
        self,
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
        if await self._resources.file_exists_by_sha256(digest):
            job.skipped_duplicate += 1
            return
        extra = {"importSourcePath": str(source)}
        package: ResourcePackage | None = None
        try:
            resource = await self._resources.create(
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
                await self._resources.add_file(
                    resource.id,
                    path=str(dest),
                    sha256=digest if role == "primary" else None,
                    size=size if role == "primary" else dest.stat().st_size,
                    format_=dest.suffix.lower().lstrip("."),
                    role=role,
                    commit=False,
                )
            cover = package.resolve_cover(role_paths)
            if cover is not None:
                resource.cover_path = f"/library/resources/{resource.id}/content"
                await self._resources.update(resource.id, resource, commit=False)
            await self._resources.commit()
            job.imported += 1
        except IntegrityError:
            await self._resources.rollback()
            if package is not None:
                self._ops.remove_tree(package.root)
            job.skipped_duplicate += 1
        except OSError as exc:
            await self._resources.rollback()
            if package is not None:
                self._ops.remove_tree(package.root)
            logger.warning("导入跳过 %s: %s", source, exc)
            job.skipped_error += 1
