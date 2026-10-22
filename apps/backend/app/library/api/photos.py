"""照片时间线与旧图回填路由。"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.library.api.deps import get_repos
from app.library.application.photos import PhotoTimelineService
from app.library.application.schemas import PhotoBackfillResult, PhotoTimeline
from app.library.domain.models import CategoryRule, ResourceType
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository

router = APIRouter(prefix="/photos", tags=["library-photos"])


def _service(
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> PhotoTimelineService:
    resources, _tasks = repos
    return PhotoTimelineService(resources)


@router.get("/timeline", response_model=PhotoTimeline)
async def photo_timeline(
    scope: str = Query(default="image"),
    type_: ResourceType | None = Query(default=None, alias="type"),
    include_all: bool = Query(default=False, alias="includeAll"),
    year: int | None = Query(default=None, ge=1, le=9999),
    month: int | None = Query(default=None, ge=1, le=12),
    category_id: int | None = Query(default=None, alias="categoryId"),
    category_ids: list[int] | None = Query(default=None, alias="categoryIds"),
    image_category_ids: list[int] | None = Query(default=None, alias="imageCategoryIds"),
    video_category_ids: list[int] | None = Query(default=None, alias="videoCategoryIds"),
    image_exclude_category_ids: list[int] | None = Query(default=None, alias="imageExcludeCategoryIds"),
    video_exclude_category_ids: list[int] | None = Query(default=None, alias="videoExcludeCategoryIds"),
    tag_ids: list[int] | None = Query(default=None, alias="tagIds"),
    date_from: str | None = Query(default=None, alias="dateFrom"),
    date_to: str | None = Query(default=None, alias="dateTo"),
    include_untimed: bool = Query(default=False, alias="includeUntimed"),
    map_visible: bool | None = Query(default=None, alias="mapVisible"),
    map_only: bool = Query(default=False, alias="mapOnly"),
    character_ids: list[int] | None = Query(default=None, alias="characterIds"),
    person_ids: list[int] | None = Query(default=None, alias="personIds"),
    service: PhotoTimelineService = Depends(_service),
) -> PhotoTimeline:
    """Timeline by scope (image/video/media); per-type include/exclude rules."""
    if scope not in ("image", "video", "media"):
        raise HTTPException(status_code=422, detail="invalid scope")
    if type_ is not None:
        scope = type_.value
    legacy_categories = list(category_ids or [])
    if category_id is not None:
        legacy_categories.append(category_id)
    image_include = list(image_category_ids or [])
    video_include = list(video_category_ids or [])
    if scope == "image":
        image_include.extend(legacy_categories)
    elif scope == "video":
        video_include.extend(legacy_categories)
    return await service.timeline(
        include_all=include_all,
        scope=scope,
        year=year,
        month=month,
        image_rule=CategoryRule(
            include=image_include, exclude=list(image_exclude_category_ids or [])
        ),
        video_rule=CategoryRule(
            include=video_include, exclude=list(video_exclude_category_ids or [])
        ),
        tag_ids=tag_ids,
        date_from=date_from,
        date_to=date_to,
        include_untimed=include_untimed,
        map_visible=map_visible,
        map_only=map_only,
        character_ids=character_ids,
        person_ids=person_ids,
    )


@router.post("/backfill", response_model=PhotoBackfillResult)
async def photo_backfill(
    service: PhotoTimelineService = Depends(_service),
) -> PhotoBackfillResult:
    """旧图回填：重读 primary 文件 EXIF，写回拍摄时间与 GPS。"""
    return await service.backfill()
