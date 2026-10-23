"""AI search API."""

from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.schemas import (
    AIAnalyzeRequest,
    AIFusionRequest,
    AIFusionResponse,
    AIJob,
    AISearchResponse,
    AISimilarFileRequest,
    AISimilarResponse,
    AIStatus,
    AIVLMRuntime,
    VLMPullRequest,
    VLMSelectBinaryRequest,
    VLMSelectRequest,
)
from app.ai.application.service import AIService, AIServiceError
from app.shared.db.db import get_session

router = APIRouter(tags=["ai"])


def _service(session: AsyncSession) -> AIService:
    return AIService(session)


@router.get("/status", response_model=AIStatus)
async def get_status(session: AsyncSession = Depends(get_session)) -> AIStatus:
    return await _service(session).status()


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
async def build_index(session: AsyncSession = Depends(get_session)) -> AIJob:
    try:
        return await _service(session).build_index()
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


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


@router.get("/search", response_model=AISearchResponse)
async def search(
    q: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=30, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> AISearchResponse:
    try:
        return await _service(session).search(q, limit)
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
