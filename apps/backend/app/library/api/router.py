"""Library 路由聚合（由根应用 include，prefix=/library）。"""
from fastapi import APIRouter

from app.library.api import categories, collections, health, imports, overview, resources, tags, todos, watch, workbench

router = APIRouter()
router.include_router(health.router)
router.include_router(overview.router)
router.include_router(imports.router)
router.include_router(resources.router)
router.include_router(collections.router)
router.include_router(collections.resource_collections_router)
router.include_router(watch.router)
router.include_router(workbench.router)
router.include_router(todos.router)
router.include_router(categories.router)
router.include_router(tags.router)
