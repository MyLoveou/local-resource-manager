"""抓取模块路由。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.scrape.application.images import fetch_poster_bytes
from app.scrape.application.jobs import (
    ScrapeError,
    create_or_reuse_job,
    preview_candidate,
    select_candidate,
)
from app.scrape.application.queue import enqueue_job
from app.scrape.application.schemas import ScrapeJobCreate, ScrapeSelect
from app.scrape.domain.models import ScrapeJobStatus
from app.scrape.infrastructure.repo import ScrapeRepository
from app.shared.db.db import get_session

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "app": "scrape", "version": "0.1.0"}


def _err(exc: ScrapeError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/jobs")
async def create_job(
    body: ScrapeJobCreate,
    force: bool = Query(False),
    session: AsyncSession = Depends(get_session),
):
    try:
        repo = ScrapeRepository(session)
        before = await repo.incomplete_job(body.resource_id)
        job = await create_or_reuse_job(
            session,
            body.resource_id,
            force=force,
            query=body.query,
        )
    except ScrapeError as exc:
        raise _err(exc) from exc
    if (
        job.id is not None
        and job.status == ScrapeJobStatus.QUEUED
        and (before is None or before.id != job.id)
    ):
        await enqueue_job(job.id)
    return job


@router.get("/jobs/{job_id}")
async def get_job(job_id: int, session: AsyncSession = Depends(get_session)):
    job = await ScrapeRepository(session).get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job


@router.get("/jobs/{job_id}/candidates")
async def list_candidates(job_id: int, session: AsyncSession = Depends(get_session)):
    repo = ScrapeRepository(session)
    if await repo.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return await repo.list_candidates(job_id)


@router.post("/jobs/{job_id}/select")
async def select_job_candidate(
    job_id: int,
    body: ScrapeSelect,
    session: AsyncSession = Depends(get_session),
):
    try:
        return await select_candidate(
            session,
            job_id,
            body.candidate_id,
            cover_url=body.cover_url,
            apply_title=body.apply_title,
            apply_synopsis=body.apply_synopsis,
            apply_author=body.apply_author,
            apply_tags=body.apply_tags,
            apply_catalog=body.apply_catalog,
            apply_cover=body.apply_cover,
            replace_user_cover=body.replace_user_cover,
        )
    except ScrapeError as exc:
        raise _err(exc) from exc


@router.get("/jobs/{job_id}/candidates/{candidate_id}/preview")
async def preview_job_candidate(
    job_id: int,
    candidate_id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        return await preview_candidate(session, job_id, candidate_id)
    except ScrapeError as exc:
        raise _err(exc) from exc


@router.get("/proxy-image")
async def proxy_image(url: str = Query(...)):
    try:
        body, mime = await fetch_poster_bytes(url)
    except HTTPException:
        raise
    except Exception as exc:
        text = str(exc) or "封面无法加载"
        code = 400 if any(token in text for token in ("不允许", "不是图片", "过大")) else 502
        raise HTTPException(status_code=code, detail=text) from exc
    return Response(content=body, media_type=mime)


@router.get("/resources/{resource_id}/latest-job")
async def latest_job(resource_id: int, session: AsyncSession = Depends(get_session)):
    job = await ScrapeRepository(session).latest_job(resource_id)
    if job is None:
        raise HTTPException(status_code=404, detail="尚无刮削任务")
    return job
