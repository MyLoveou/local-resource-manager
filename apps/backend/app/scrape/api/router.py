"""抓取模块路由。"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "app": "scrape", "version": "0.0.0"}
