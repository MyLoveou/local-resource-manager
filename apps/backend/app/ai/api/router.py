"""AI search API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.schemas import AIJob, AISearchResponse, AISimilarResponse, AIStatus
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


@router.post("/index", response_model=AIJob)
async def build_index(session: AsyncSession = Depends(get_session)) -> AIJob:
    try:
        return await _service(session).build_index()
    except AIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


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
