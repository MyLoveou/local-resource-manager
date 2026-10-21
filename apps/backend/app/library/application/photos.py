"""照片时间线与旧图回填用例。"""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.library.application.media_probe import ProbeFields, probe_media
from app.library.application.packages import ResourcePackage, layout_for
from app.library.application.packages.resource_package import default_library_store
from app.library.application.schemas import (
    PhotoBackfillResult,
    PhotoTile,
    PhotoTimeline,
    PhotoTimelineDay,
    ThumbnailBackfillResult,
)
from app.library.application.thumbnails import source_for_grid_thumbnail
from app.library.domain.media_types import FILE_ROLE_THUMBNAIL
from app.library.domain.models import CategoryRule, ResourceStatus, ResourceType
from app.library.infrastructure.repositories import CategoryRepository, ResourceRepository
from app.shared.config import settings
from app.shared.fs.file_ops import FileOps


class PhotoTimelineService:
    def __init__(
        self,
        resources: ResourceRepository,
        categories: CategoryRepository | None = None,
        *,
        store_root: Path | None = None,
        file_ops: FileOps | None = None,
    ):
        self._resources = resources
        self._categories = categories or CategoryRepository(resources.session)
        self._store_root = store_root or default_library_store(settings.db_path)
        self._ops = file_ops or FileOps()

    async def timeline(
        self,
        *,
        include_all: bool,
        scope: str | None = None,
        year: int | None,
        month: int | None,
        image_rule: CategoryRule | None = None,
        video_rule: CategoryRule | None = None,
        tag_ids: list[int] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        include_untimed: bool = False,
        type_: ResourceType | None = None,
        category_ids: list[int] | None = None,
        map_visible: bool | None = None,
        map_only: bool = False,
    ) -> PhotoTimeline:
        if scope is None:
            scope = (type_ or ResourceType.IMAGE).value
        if category_ids:
            if scope == "image" and image_rule is None:
                image_rule = CategoryRule(include=category_ids)
            elif scope == "video" and video_rule is None:
                video_rule = CategoryRule(include=category_ids)
        image_rule = image_rule or CategoryRule()
        video_rule = video_rule or CategoryRule()
        result: list[tuple[list[dict], list[dict], int]] = []
        for type_, rule in ((ResourceType.IMAGE, image_rule), (ResourceType.VIDEO, video_rule)):
            if scope != "media" and scope != type_.value:
                continue
            include_ids = await self._categories.descendant_ids(rule.include)
            exclude_ids = await self._categories.descendant_ids(rule.exclude)
            result.append(await self._resources.timeline_photos(
                include_all=include_all,
                type_=type_,
                year=year,
                month=month,
                category_ids=include_ids,
                exclude_category_ids=exclude_ids,
                tag_ids=tag_ids,
                date_from=date_from,
                date_to=date_to,
                include_untimed=include_untimed,
                map_visible=map_visible,
                map_only=map_only,
            ))

        days_by_date: dict[str, list[dict]] = {}
        unknown: list[dict] = []
        total = 0
        for days, unknown_rows, part_total in result:
            total += part_total
            for day in days:
                days_by_date.setdefault(day["date"], []).extend(day["photos"])
            unknown.extend(unknown_rows)
        days = [
            {
                "date": date,
                "count": len(photos),
                "photos": sorted(
                    photos,
                    key=lambda photo: (photo.get("taken_at") or "", photo["id"]),
                    reverse=True,
                ),
            }
            for date, photos in sorted(days_by_date.items(), reverse=True)
        ]
        unknown = sorted(
            unknown,
            key=lambda photo: (photo.get("taken_at") or "", photo["id"]),
            reverse=True,
        )
        return PhotoTimeline(
            days=[
                PhotoTimelineDay(
                    date=day["date"],
                    count=day["count"],
                    photos=[PhotoTile(**photo) for photo in day["photos"]],
                )
                for day in days
            ],
            unknown_count=len(unknown),
            unknown_photos=[PhotoTile(**photo) for photo in unknown],
            total=total,
        )

    async def backfill(self) -> PhotoBackfillResult:
        """重读旧图片/视频的拍摄元数据：只更新拍摄时间/GPS，不清空已有值，不覆盖手动可见性。"""
        rows = await self._resources.media_primary_files()

        def probe_all() -> list[tuple[int, ProbeFields | None, str | None]]:
            results: list[tuple[int, ProbeFields | None, str | None]] = []
            for row, type_value in rows:
                path = Path(row.path)
                if not path.is_file():
                    results.append((row.id, None, "missing"))
                    continue
                try:
                    results.append(
                        (row.id, probe_media(ResourceType(type_value), path), None)
                    )
                except Exception:
                    results.append((row.id, None, "failed"))
            return results

        probed = await asyncio.to_thread(probe_all)
        current = {row.id: row for row, _type in rows}
        scanned = len(probed)
        taken_updated = 0
        gps_updated = 0
        skipped = 0
        failed = 0
        for file_id, result, error in probed:
            if error == "missing":
                skipped += 1
                continue
            if error is not None or result is None:
                failed += 1
                continue
            row = current.get(file_id)
            if row is None:
                failed += 1
                continue
            taken = result.exif_taken_at if result.exif_taken_at is not None else row.exif_taken_at
            lat = result.exif_lat if result.exif_lat is not None else row.exif_lat
            lng = result.exif_lng if result.exif_lng is not None else row.exif_lng
            camera = result.exif_camera if result.exif_camera is not None else row.exif_camera
            lens = result.exif_lens if result.exif_lens is not None else row.exif_lens
            iso = result.exif_iso if result.exif_iso is not None else row.exif_iso
            aperture = result.exif_aperture if result.exif_aperture is not None else row.exif_aperture
            shutter = result.exif_shutter if result.exif_shutter is not None else row.exif_shutter
            camera_changed = (
                camera != row.exif_camera
                or lens != row.exif_lens
                or iso != row.exif_iso
                or aperture != row.exif_aperture
                or shutter != row.exif_shutter
            )
            if (
                taken is None
                and lat is None
                and lng is None
                and camera is None
                and lens is None
                and iso is None
                and aperture is None
                and shutter is None
            ):
                skipped += 1
                continue
            if taken != row.exif_taken_at:
                taken_updated += 1
            if lat != row.exif_lat or lng != row.exif_lng:
                gps_updated += 1
            if taken != row.exif_taken_at or lat != row.exif_lat or lng != row.exif_lng or camera_changed:
                await self._resources.update_file_exif(
                    file_id,
                    taken_at=taken,
                    lat=lat,
                    lng=lng,
                    camera=camera,
                    lens=lens,
                    iso=iso,
                    aperture=aperture,
                    shutter=shutter,
                )
        await self._resources.commit()
        return PhotoBackfillResult(
            scanned=scanned,
            taken_at_updated=taken_updated,
            gps_updated=gps_updated,
            skipped=skipped,
            failed=failed,
        )
