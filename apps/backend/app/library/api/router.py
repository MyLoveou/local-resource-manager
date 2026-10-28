"""Library 路由聚合（由根应用 include，prefix=/library）。"""
from fastapi import APIRouter

from app.library.api import (
    categories,
    characters,
    collections,
    health,
    home,
    imports,
    overview,
    persons,
    photos,
    progress,
    resources,
    saved_views,
    series_assets,
    suggestions,
    tags,
    timeline_notes,
    todos,
    watch,
    workbench,
)

router = APIRouter()
router.include_router(health.router)
router.include_router(overview.router)
router.include_router(imports.router)
router.include_router(resources.router)
router.include_router(progress.resource_router)
router.include_router(progress.router)
router.include_router(suggestions.router)
router.include_router(photos.router)
router.include_router(collections.router)
router.include_router(collections.resource_collections_router)
router.include_router(watch.router)
router.include_router(workbench.router)
router.include_router(todos.router)
router.include_router(categories.router)
router.include_router(saved_views.router)
router.include_router(home.router)
router.include_router(tags.router)
router.include_router(timeline_notes.router)
router.include_router(characters.router)
router.include_router(persons.router)
router.include_router(series_assets.router)
