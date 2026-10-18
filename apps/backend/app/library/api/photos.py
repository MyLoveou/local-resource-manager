"""照片时间线与旧图回填路由。"""

from fastapi import APIRouter, Depends, Query

from app.library.api.deps import get_repos
from app.library.application.photos import PhotoTimelineService
from app.library.application.schemas import PhotoBackfillResult, PhotoTimeline
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository

router = APIRouter(prefix="/photos", tags=["library-photos"])


def _service(
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> PhotoTimelineService:
    resources, _tasks = repos
    return PhotoTimelineService(resources)


@router.get("/timeline", response_model=PhotoTimeline)
async def photo_timeline(
    include_all: bool = Query(default=False, alias="includeAll"),
    year: int | None = Query(default=None, ge=1, le=9999),
    month: int | None = Query(default=None, ge=1, le=12),
    category_id: int | None = Query(default=None, alias="categoryId"),
    tag_ids: list[int] | None = Query(default=None, alias="tagIds"),
    service: PhotoTimelineService = Depends(_service),
) -> PhotoTimeline:
    """按拍摄日聚合图片；默认只含有效可见的照片（含合集成员）。"""
    return await service.timeline(
        include_all=include_all,
        year=year,
        month=month,
        category_id=category_id,
        tag_ids=tag_ids,
    )


@router.post("/backfill", response_model=PhotoBackfillResult)
async def photo_backfill(
    service: PhotoTimelineService = Depends(_service),
) -> PhotoBackfillResult:
    """旧图回填：重读 primary 文件 EXIF，写回拍摄时间与 GPS。"""
    return await service.backfill()
