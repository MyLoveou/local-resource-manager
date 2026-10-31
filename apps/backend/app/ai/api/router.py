"""AI search API."""

from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.schemas import (
    AIAnalyzeRequest,
    AIEntitySuggestion,
    AITagCandidate,
    AIFusionRequest,
    AIFusionResponse,
    AIJob,
    AIFeedbackRequest,
    AIIndexRequest,
    AIPerformance,
    AIPerformancePatch,
    AISearchResponse,
    AISimilarFileRequest,
    AISuggestionItem,
    AISimilarResponse,
    AIStatus,
    AIVLMRuntime,
    VLMPullRequest,
    VLMSelectBinaryRequest,
    VLMSelectRequest,
)
from app.ai.application.category_hint import suggest_categories
from app.ai.application.tag_hint import new_tag_candidates
from app.ai.application.service import AIService, AIServiceError
from app.shared.db.db import get_session

router = APIRouter(tags=["ai"])


def _service(session: AsyncSession) -> AIService:
    return AIService(session)


@router.get("/status", response_model=AIStatus)
async def get_status(session: AsyncSession = Depends(get_session)) -> AIStatus:
    return await _service(session).status()


@router.get("/performance", response_model=AIPerformance)
async def get_performance(session: AsyncSession = Depends(get_session)) -> AIPerformance:
    return await _service(session).performance()


@router.patch("/performance", response_model=AIPerformance)
async def update_performance(
    body: AIPerformancePatch,
    session: AsyncSession = Depends(get_session),
) -> AIPerformance:
    try:
        return await _service(session).update_performance(body)
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/models/install", response_model=AIJob)
async def install_model(session: AsyncSession = Depends(get_session)) -> AIJob:
    try:
        return await _service(session).install_model()
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/vlm/runtime", response_model=AIVLMRuntime)
async def vlm_runtime(session: AsyncSession = Depends(get_session)) -> AIVLMRuntime:
    return await _service(session).vlm_runtime_status()


@router.post("/vlm/runtime/select", response_model=AIVLMRuntime)
async def select_ollama_binary(
    body: VLMSelectBinaryRequest,
    session: AsyncSession = Depends(get_session),
) -> AIVLMRuntime:
    try:
        return await _service(session).select_ollama_binary(body.path)
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/vlm/runtime/start", response_model=AIVLMRuntime)
async def start_ollama_runtime(
    session: AsyncSession = Depends(get_session),
) -> AIVLMRuntime:
    try:
        return await _service(session).start_ollama_runtime()
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/anime/install", response_model=AIJob)
async def install_anime_tagger(session: AsyncSession = Depends(get_session)) -> AIJob:
    try:
        return await _service(session).install_anime_tagger()
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/vlm/pull", response_model=AIJob)
async def pull_vlm(
    body: VLMPullRequest,
    session: AsyncSession = Depends(get_session),
) -> AIJob:
    try:
        return await _service(session).pull_vlm(body.model)
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/vlm/select", response_model=AIStatus)
async def select_vlm(
    body: VLMSelectRequest,
    session: AsyncSession = Depends(get_session),
) -> AIStatus:
    try:
        return await _service(session).select_vlm(body.model)
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/analyze", response_model=AIJob)
async def analyze(
    body: AIAnalyzeRequest,
    session: AsyncSession = Depends(get_session),
) -> AIJob:
    try:
        return await _service(session).analyze_images(
            body.resource_ids, body.only_pending
        )
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/index", response_model=AIJob)
async def build_index(
    body: AIIndexRequest | None = None,
    session: AsyncSession = Depends(get_session),
) -> AIJob:
    try:
        return await _service(session).build_index(bool(body.full) if body else False)
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/suggestions", response_model=list[AISuggestionItem])
async def suggestions(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[AISuggestionItem]:
    items = await _service(session).suggestions(limit, offset)
    # 分类建议在应用层补齐：service.py 已顶到文件规模基线，不往里加行
    resource_ids = [item.resource_id for item in items]
    hints = await suggest_categories(session, resource_ids)
    new_tags = await new_tag_candidates(session, resource_ids)
    for item in items:
        item.categories = [
            AIEntitySuggestion(id=hit["id"], name=hit["name"], confidence=hit["confidence"])
            for hit in hints.get(item.resource_id, [])
        ]
        item.new_tags = [
            AITagCandidate(name=hit["name"], similar_to=hit["similar_to"], similarity=hit["similarity"])
            for hit in new_tags.get(item.resource_id, [])
        ]
    return items


@router.get("/jobs", response_model=list[AIJob])
async def list_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> list[AIJob]:
    return await _service(session).list_jobs(limit)


@router.delete("/jobs")
async def clear_jobs(session: AsyncSession = Depends(get_session)) -> dict:
    try:
        await _service(session).clear_jobs()
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"cleared": True}


@router.get("/jobs/{job_id}", response_model=AIJob)
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)) -> AIJob:
    try:
        return await _service(session).get_job(job_id)
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/similar", response_model=AISimilarResponse)
async def similar(
    resource_id: int = Query(alias="resourceId"),
    mode: str = Query(default="auto"),
    limit: int = Query(default=30, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> AISimilarResponse:
    try:
        return await _service(session).similar(resource_id, mode, limit)
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/search/fusion", response_model=AIFusionResponse)
async def fusion(
    body: AIFusionRequest,
    session: AsyncSession = Depends(get_session),
) -> AIFusionResponse:
    try:
        return await _service(session).fusion(
            body.resource_id,
            body.query,
            min(max(body.limit, 1), 100),
            body.strict,
            body.image_weight,
            body.text_weight,
        )
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/similar/file", response_model=AISimilarResponse)
async def similar_file(
    body: AISimilarFileRequest,
    session: AsyncSession = Depends(get_session),
) -> AISimilarResponse:
    try:
        data = base64.b64decode(body.data_base64, validate=True)
        return await _service(session).similar_file(
            data,
            body.filename,
            body.mode,
            min(max(body.limit, 1), 100),
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="图片数据无效") from exc
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/feedback", response_model=dict)
async def feedback(
    body: AIFeedbackRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        await _service(session).add_feedback(
            body.query,
            body.resource_id,
            body.action,
            body.source,
            body.score,
            body.position,
            body.features,
        )
        return {"ok": True}
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.delete("/feedback", response_model=dict)
async def remove_feedback(
    query: str = Query(min_length=1, max_length=100),
    resource_id: int = Query(alias="resourceId"),
    source: str = Query(default="search"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        await _service(session).remove_feedback(query, resource_id, source)
        return {"ok": True}
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/search", response_model=AISearchResponse)
async def search(
    q: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=30, ge=1, le=100),
    min_score: float = Query(default=0.0, ge=0.0, le=1.0, alias="minScore"),
    session: AsyncSession = Depends(get_session),
) -> AISearchResponse:
    try:
        return await _service(session).search(q, limit, min_score)
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
