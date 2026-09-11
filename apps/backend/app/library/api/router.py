"""Library 路由聚合（由根应用 include，prefix=/library）。"""
from fastapi import APIRouter

from app.library.api import categories, health, imports, overview, resources, tags, todos

router = APIRouter()
router.include_router(health.router)
router.include_router(overview.router)
router.include_router(imports.router)
router.include_router(resources.router)
router.include_router(todos.router)
router.include_router(categories.router)
router.include_router(tags.router)
