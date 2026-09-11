"""下载模块路由。"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "app": "download", "version": "0.0.0"}
