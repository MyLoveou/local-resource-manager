"""导入任务 API。"""

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.library.application.importers import importer_for
from app.library.application.import_service import ImportService
from app.library.application.packages.layouts import layout_for
from app.library.application.schemas import ImportCreate, ImportJob, ImportJobCreated, SourceKind
from app.library.infrastructure.import_job_store import ImportJobState, job_store
from app.shared.db.db import get_session_factory
from app.library.domain.type_profile import COMIC_ARCHIVE_EXTENSIONS, profile_for

router = APIRouter(prefix="/imports", tags=["library-imports"])
_import_tasks: set[asyncio.Task[None]] = set()


def validate_import(body: ImportCreate) -> str | None:
    """返回错误文案；合法则 None。"""
    profile = profile_for(body.type)
    if importer_for(body.type) is None or layout_for(body.type) is None or profile is None:
        return "unsupported type"
    storage = body.storage_kind or profile.default_storage
    if storage not in profile.allowed_storage:
        return "unsupported storageKind"
    if profile.ingest_kind == "series" and body.source_kind != SourceKind.DIRECTORY:
        return "series import requires a directory"
    if (
        profile.ingest_kind == "package"
        and body.source_kind != SourceKind.DIRECTORY
        and not (
            profile.allows_file_source
            and body.source_kind == SourceKind.FILE
            and all(Path(p).suffix.lower() in COMIC_ARCHIVE_EXTENSIONS for p in body.paths)
        )
    ):
        return "package import requires a directory"
    if body.source_kind == SourceKind.DIRECTORY:
        if len(body.paths) != 1:
            return "directory import requires exactly one path"
        if not Path(body.paths[0]).is_dir():
            return "path is not a directory"
        return None
    for raw in body.paths:
        if not Path(raw).is_file():
            return "path is not a file"
    return None


def _to_dto(job: ImportJobState) -> ImportJob:
    return ImportJob(
        job_id=job.id,
        status=job.status,
        phase=job.phase,
        total=job.total,
        done=job.done,
        imported=job.imported,
        skipped_duplicate=job.skipped_duplicate,
        skipped_error=job.skipped_error,
        error=job.error,
    )


async def _execute(job: ImportJobState, body: ImportCreate) -> None:
    job_store.mark_running(job)
    factory = get_session_factory()
    try:
        service = ImportService(session_factory=factory)
        await service.run(
            job, body.type, body.source_kind.value, body.paths,
            storage_kind=body.storage_kind.value if body.storage_kind else None,
        )
        await job_store.finish(job)
    except asyncio.CancelledError:
        await job_store.finish(job, failed="cancelled")
        raise
    except Exception as exc:  # noqa: BLE001 — 任务失败要落状态
        await job_store.finish(job, failed=str(exc))


@router.post("", response_model=ImportJobCreated, status_code=202)
async def create_import(body: ImportCreate) -> ImportJobCreated:
    """创建导入任务（异步复制入库）。"""
    error = validate_import(body)
    if error:
        raise HTTPException(status_code=400, detail=error)
    job = await job_store.create_if_idle()
    if job is None:
        raise HTTPException(status_code=409, detail="import already running")
    task = asyncio.create_task(_execute(job, body))
    _import_tasks.add(task)
    task.add_done_callback(_import_tasks.discard)
    return ImportJobCreated(job_id=job.id)


@router.get("/{job_id}", response_model=ImportJob)
async def get_import_job(job_id: str) -> ImportJob:
    """导入进度。"""
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return _to_dto(job)
