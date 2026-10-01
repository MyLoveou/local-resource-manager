"""刮削任务与候选仓储。"""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.scrape.application.providers.base import SearchHit
from app.scrape.domain.models import Candidate, ScrapeJob, ScrapeJobStatus
from app.shared.db.orm import CandidateRow, ScrapeJobRow
from app.shared.utils.time import db_now, db_ts


def _job(row: ScrapeJobRow) -> ScrapeJob:
    return ScrapeJob(
        id=row.id,
        resource_id=row.resource_id,
        status=ScrapeJobStatus(row.status),
        started_at=row.started_at,
        finished_at=row.finished_at,
        error=row.error,
        match_count=row.match_count,
        query=row.query,
    )


def _candidate(row: CandidateRow) -> Candidate:
    return Candidate(
        id=row.id,
        job_id=row.job_id,
        title=row.title,
        url=row.url,
        thumbnail_url=row.thumbnail_url,
        source=row.source,
        relevance=row.relevance,
        selected=bool(row.selected),
        created_at=row.created_at,
    )


class ScrapeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_job(self, resource_id: int, query: str | None = None) -> ScrapeJob:
        row = ScrapeJobRow(
            resource_id=resource_id,
            status=ScrapeJobStatus.QUEUED.value,
            match_count=0,
            query=query,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _job(row)

    async def get_job(self, job_id: int) -> ScrapeJob | None:
        row = await self._session.get(ScrapeJobRow, job_id)
        return None if row is None else _job(row)

    async def latest_job(self, resource_id: int) -> ScrapeJob | None:
        stmt = (
            select(ScrapeJobRow)
            .where(ScrapeJobRow.resource_id == resource_id)
            .order_by(ScrapeJobRow.id.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalars().first()
        return None if row is None else _job(row)

    async def incomplete_job(self, resource_id: int) -> ScrapeJob | None:
        stmt = (
            select(ScrapeJobRow)
            .where(
                ScrapeJobRow.resource_id == resource_id,
                ScrapeJobRow.status.in_((ScrapeJobStatus.QUEUED.value, ScrapeJobStatus.RUNNING.value)),
            )
            .order_by(ScrapeJobRow.id.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalars().first()
        return None if row is None else _job(row)

    async def pending_confirm_job(self, resource_id: int) -> ScrapeJob | None:
        latest = await self.latest_job(resource_id)
        if latest is None or latest.id is None:
            return None
        if latest.status != ScrapeJobStatus.DONE or latest.match_count <= 0:
            return None
        selected = await self._session.scalar(
            select(func.count())
            .select_from(CandidateRow)
            .where(CandidateRow.job_id == latest.id, CandidateRow.selected == 1)
        )
        if int(selected or 0) > 0:
            return None
        return latest

    async def list_unfinished_ids(self) -> list[int]:
        stmt = select(ScrapeJobRow.id).where(
            ScrapeJobRow.status.in_((ScrapeJobStatus.QUEUED.value, ScrapeJobStatus.RUNNING.value))
        )
        return [int(i) for i in (await self._session.execute(stmt)).scalars().all()]

    async def save_job(self, job: ScrapeJob) -> None:
        assert job.id is not None
        row = await self._session.get(ScrapeJobRow, job.id)
        if row is None:
            return
        row.status = job.status.value
        row.started_at = db_ts(job.started_at)
        row.finished_at = db_ts(job.finished_at)
        row.error = job.error
        row.match_count = job.match_count
        row.query = job.query
        await self._session.commit()

    async def replace_candidates(self, job_id: int, hits: list[SearchHit]) -> None:
        await self._session.execute(delete(CandidateRow).where(CandidateRow.job_id == job_id))
        for hit in hits:
            self._session.add(
                CandidateRow(
                    job_id=job_id,
                    title=hit.title,
                    url=hit.key,
                    thumbnail_url=hit.thumbnail_url,
                    source=hit.source,
                    relevance=hit.relevance,
                    selected=0,
                    created_at=db_now(),
                )
            )
        await self._session.commit()

    async def list_candidates(self, job_id: int) -> list[Candidate]:
        stmt = select(CandidateRow).where(CandidateRow.job_id == job_id).order_by(CandidateRow.id)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_candidate(r) for r in rows]

    async def get_candidate(self, candidate_id: int) -> Candidate | None:
        row = await self._session.get(CandidateRow, candidate_id)
        return None if row is None else _candidate(row)

    async def mark_selected(self, candidate_id: int) -> None:
        row = await self._session.get(CandidateRow, candidate_id)
        if row is None:
            return
        row.selected = 1
        await self._session.commit()
