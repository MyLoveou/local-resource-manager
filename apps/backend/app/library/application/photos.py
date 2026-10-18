"""照片时间线与旧图回填用例。"""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.library.application.media_probe import ProbeFields, probe_media
from app.library.application.schemas import (
    PhotoBackfillResult,
    PhotoTile,
    PhotoTimeline,
    PhotoTimelineDay,
)
from app.library.domain.models import ResourceType
from app.library.infrastructure.repositories import ResourceRepository


class PhotoTimelineService:
    def __init__(self, resources: ResourceRepository):
        self._resources = resources

    async def timeline(
        self,
        *,
        include_all: bool,
        year: int | None,
        month: int | None,
        category_id: int | None,
        tag_ids: list[int] | None,
    ) -> PhotoTimeline:
        days, unknown, total = await self._resources.timeline_photos(
            include_all=include_all,
            year=year,
            month=month,
            category_id=category_id,
            tag_ids=tag_ids,
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
            if taken is None and lat is None and lng is None:
                skipped += 1
                continue
            if taken != row.exif_taken_at:
                taken_updated += 1
            if lat != row.exif_lat or lng != row.exif_lng:
                gps_updated += 1
            if taken != row.exif_taken_at or lat != row.exif_lat or lng != row.exif_lng:
                await self._resources.update_file_exif(
                    file_id, taken_at=taken, lat=lat, lng=lng
                )
        await self._resources.commit()
        return PhotoBackfillResult(
            scanned=scanned,
            taken_at_updated=taken_updated,
            gps_updated=gps_updated,
            skipped=skipped,
            failed=failed,
        )
