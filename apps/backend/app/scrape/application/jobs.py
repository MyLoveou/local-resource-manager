"""刮削任务：search 不写 Resource；select 才 apply。"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.library.application.covers.origin import is_user_locked
from app.library.infrastructure.repositories import ResourceRepository
from app.scrape.application.apply import apply_scrape_detail, catalog_summary, up_from_catalog
from app.scrape.application.providers import is_scrapeable, provider_for_key, providers_for
from app.scrape.application.providers.base import MetadataProvider, SearchHit
from app.scrape.application.providers.bilibili import BilibiliProvider, extract_ids, resolve_query_ids
from app.scrape.application.providers.og import page_url_or_error
from app.scrape.application.providers.tmdb import TmdbProvider
from app.scrape.application.schemas import ScrapeCurrent, ScrapePreview
from app.scrape.domain.models import ScrapeJob, ScrapeJobStatus
from app.scrape.infrastructure.repo import ScrapeRepository
from app.shared.log import logger
from app.library.domain.models import (
    Resource,
    ResourceType,
)


class ScrapeError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


async def create_or_reuse_job(
    session: AsyncSession,
    resource_id: int,
    *,
    force: bool = False,
    query: str | None = None,
) -> ScrapeJob:
    resources = ResourceRepository(session)
    resource = await resources.get(resource_id)
    if resource is None:
        raise ScrapeError("资源不存在", 404)
    if not is_scrapeable(resource.type):
        raise ScrapeError("仅视频、番剧与图片支持获取元数据", 400)
    hint = (query or "").strip() or None
    if resource.type == ResourceType.IMAGE:
        if not hint:
            raise ScrapeError("请填写页面链接", 400)
        try:
            hint = page_url_or_error(hint)
        except RuntimeError as exc:
            raise ScrapeError(str(exc), 400) from exc
        force = True
    elif hint:
        ids = extract_ids(hint)
        if not ids:
            ids = await resolve_query_ids(hint)
        force = True
        if ids:
            hint = " ".join(value if kind == "bvid" else f"av{value}" for kind, value in ids)
    repo = ScrapeRepository(session)
    if not force:
        running = await repo.incomplete_job(resource_id)
        if running is not None:
            return running
        pending = await repo.pending_confirm_job(resource_id)
        if pending is not None:
            return pending
    return await repo.create_job(resource_id, query=hint)


def _file_stems(resource: Resource) -> list[str]:
    names: list[str] = []
    for row in resource.files or []:
        if not row.path:
            continue
        names.append(Path(row.path.replace("\\", "/")).stem)
    return names


def _bili_blob(resource: Resource, job_query: str | None) -> str:
    parts = [job_query or "", resource.title or "", *_file_stems(resource)]
    return " ".join(part for part in parts if part.strip())


async def run_search(session: AsyncSession, job_id: int) -> ScrapeJob:
    repo = ScrapeRepository(session)
    job = await repo.get_job(job_id)
    if job is None or job.id is None:
        raise ScrapeError("任务不存在", 404)
    resources = ResourceRepository(session)
    resource = await resources.get(job.resource_id)
    if resource is None:
        job.fail("资源不存在")
        await repo.save_job(job)
        return job
    if job.status == ScrapeJobStatus.RUNNING:
        job.status = ScrapeJobStatus.QUEUED
    job.start()
    await repo.save_job(job)
    try:
        hits = await _search_channels(resource, job.query)
        await repo.replace_candidates(job.id, hits)
        job.finish(len(hits))
        await repo.save_job(job)
    except Exception as exc:
        job.fail(str(exc) or "搜索失败")
        await repo.save_job(job)
    result = await repo.get_job(job_id)
    assert result is not None
    return result


async def select_candidate(
    session: AsyncSession,
    job_id: int,
    candidate_id: int,
    *,
    cover_url: str | None = None,
    apply_title: bool = True,
    apply_synopsis: bool = True,
    apply_author: bool = True,
    apply_tags: bool = True,
    apply_catalog: bool = True,
    apply_cover: bool = True,
    replace_user_cover: bool = False,
) -> ScrapeJob:
    repo = ScrapeRepository(session)
    job = await repo.get_job(job_id)
    if job is None:
        raise ScrapeError("任务不存在", 404)
    if job.status != ScrapeJobStatus.DONE:
        raise ScrapeError("任务尚未完成搜索", 409)
    candidate = await repo.get_candidate(candidate_id)
    if candidate is None or candidate.job_id != job_id:
        raise ScrapeError("候选无效", 400)
    resources = ResourceRepository(session)
    resource = await resources.get(job.resource_id)
    if resource is None:
        raise ScrapeError("资源不存在", 404)
    try:
        provider = provider_for_key(candidate.url)
        detail = await provider.detail(candidate.url)
        await apply_scrape_detail(
            resources,
            resource,
            detail,
            cover_url=cover_url,
            apply_title=apply_title,
            apply_synopsis=apply_synopsis,
            apply_author=apply_author,
            apply_tags=apply_tags,
            apply_catalog=apply_catalog,
            apply_cover=apply_cover,
            replace_user_cover=replace_user_cover,
        )
        await repo.mark_selected(candidate_id)
    except ScrapeError:
        raise
    except Exception as exc:
        raise ScrapeError(str(exc) or "回填失败", 502) from exc
    result = await repo.get_job(job_id)
    assert result is not None
    return result


async def _search_channels(resource: Resource, job_query: str | None) -> list[SearchHit]:
    if resource.type == ResourceType.IMAGE:
        page = (job_query or "").strip()
        if not page:
            raise RuntimeError("请填写页面链接")
        return await _collect_hits(providers_for(ResourceType.IMAGE), page, page)
    name = (job_query or "").strip()
    by_name = bool(name) and not extract_ids(name)
    if by_name:
        title_q = name
        bili_blob = name
    else:
        title_q = resource.title or ""
        bili_blob = _bili_blob(resource, job_query)
    providers = providers_for(resource.type)
    if resource.type == ResourceType.VIDEO:
        has_id = bool(extract_ids(bili_blob))
        bili = [p for p in providers if isinstance(p, BilibiliProvider)]
        others = [p for p in providers if not isinstance(p, BilibiliProvider)]
        ordered = [*bili, *others] if has_id else [*others, *bili]
        return await _collect_hits(ordered, title_q, bili_blob)
    return await _collect_hits(providers, title_q, title_q)


# 每个渠道单独配额：否则前一个渠道结果一多，后面的会被总上限直接挤掉
_PER_PROVIDER_CAP = 10
_OVERALL_CAP = 20


async def _collect_hits(
    providers: list[MetadataProvider],
    title: str,
    bili_blob: str,
) -> list[SearchHit]:
    uniq: list[SearchHit] = []
    seen: set[str] = set()
    errors: list[str] = []
    for provider in providers:
        query = bili_blob if isinstance(provider, BilibiliProvider) else title
        if isinstance(provider, TmdbProvider):
            query = title
        try:
            found = await provider.search(query)
        except Exception as exc:
            name = type(provider).__name__
            # 只带 str(exc) 常常是空的，补上类型名才能定位
            detail = f"{type(exc).__name__}: {exc}".strip()
            errors.append(f"{name}: {detail}")
            logger.warning("刮削渠道失败 %s: %s", name, detail)
            continue
        added = 0
        for hit in found:
            if hit.key in seen:
                continue
            seen.add(hit.key)
            uniq.append(hit)
            added += 1
            if added >= _PER_PROVIDER_CAP or len(uniq) >= _OVERALL_CAP:
                break
        if len(uniq) >= _OVERALL_CAP:
            break
    if not uniq and errors:
        hint = ""
        if all(("ConnectError" in item or "Timeout" in item) for item in errors):
            hint = "（网络不可达：请检查系统代理或节点）"
        raise RuntimeError("；".join(errors) + hint)
    return uniq


async def preview_candidate(session: AsyncSession, job_id: int, candidate_id: int) -> ScrapePreview:
    repo = ScrapeRepository(session)
    job = await repo.get_job(job_id)
    if job is None:
        raise ScrapeError("任务不存在", 404)
    candidate = await repo.get_candidate(candidate_id)
    if candidate is None or candidate.job_id != job_id:
        raise ScrapeError("候选无效", 400)
    resource = await ResourceRepository(session).get(job.resource_id)
    if resource is None:
        raise ScrapeError("资源不存在", 404)
    try:
        detail = await provider_for_key(candidate.url).detail(candidate.url)
    except Exception as exc:
        raise ScrapeError(str(exc) or "预览失败", 502) from exc
    covers = list(detail.cover_urls)
    if detail.poster_url and detail.poster_url not in covers:
        covers.insert(0, detail.poster_url)
    return ScrapePreview(
        title=detail.title,
        synopsis=detail.synopsis,
        author=up_from_catalog(detail.catalog),
        tags=detail.tags,
        cover_urls=covers,
        catalog=detail.catalog,
        catalog_summary=catalog_summary(detail.catalog),
        source_ref=detail.source_ref,
        user_cover_locked=is_user_locked(resource),
        current=ScrapeCurrent(
            title=resource.title or "",
            synopsis=resource.synopsis,
            author=resource.author,
            tags=[t.name for t in (resource.tags or []) if t.name],
            catalog_summary=catalog_summary(resource.catalog),
        ),
    )
