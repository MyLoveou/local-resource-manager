"""Library 路由聚合（由根应用 include，prefix=/library）。"""
from fastapi import APIRouter

from app.library.api import health, imports, overview, resources

router = APIRouter()
router.include_router(health.router)
router.include_router(overview.router)
router.include_router(imports.router)
router.include_router(resources.router)
