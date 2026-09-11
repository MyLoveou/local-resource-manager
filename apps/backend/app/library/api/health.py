"""Library 健康检查。"""
from fastapi import APIRouter

router = APIRouter(tags=["library-health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "app": "library", "version": "0.0.0"}
