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
from app.library.domain.media_types import (
    FILE_ROLE_PREVIEW,
    FILE_ROLE_PRIMARY,
    FILE_ROLE_THUMBNAIL,
)
from app.library.domain.models import CategoryRule, ResourceStatus, ResourceType
from app.library.infrastructure.repositories import CategoryRepository, ResourceRepository
from app.shared.config import settings
from app.shared.fs.file_ops import FileOps
from app.shared.log import logger


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
        character_ids: list[int] | None = None,
        person_ids: list[int] | None = None,
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
                character_ids=character_ids,
                person_ids=person_ids,
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

    async def rebuild_thumbnail(self, resource_id: int) -> ThumbnailBackfillResult:
        """Rebuild one resource's grid thumbnail and HEIC preview."""
        resource = await self._resources.get(resource_id)
        if resource is None or resource.id is None:
            return ThumbnailBackfillResult(scanned=1, failed=1)
        primary = next(
            (file for file in resource.files if file.role == FILE_ROLE_PRIMARY),
            None,
        )
        if primary is None or not primary.path:
            return ThumbnailBackfillResult(scanned=1, failed=1)
        source = Path(primary.path)
        if not source.is_file():
            return ThumbnailBackfillResult(scanned=1, failed=1)
        layout = layout_for(resource.type)
        if layout is None:
            return ThumbnailBackfillResult(scanned=1, skipped=1)
        thumb_source = source_for_grid_thumbnail(
            resource.type, {FILE_ROLE_PRIMARY: source}
        )
        if thumb_source is None:
            return ThumbnailBackfillResult(scanned=1, skipped=1)
        package = ResourcePackage(
            self._store_root,
            resource.type,
            resource.id,
            self._ops,
            cover_falls_back_to_primary=layout.cover_falls_back_to_primary,
        )
        try:
            thumb_dest = await asyncio.to_thread(package.put_thumbnail, thumb_source)
            if thumb_dest is None:
                return ThumbnailBackfillResult(scanned=1, failed=1)
            preview_dest = None
            if source.suffix.lower() in {".heic", ".heif"}:
                preview_dest = await asyncio.to_thread(package.put_preview, source)
            for role in (FILE_ROLE_THUMBNAIL, FILE_ROLE_PREVIEW):
                old = await self._resources.get_file_by_role(resource.id, role)
                if old is not None and old.id is not None:
                    await self._resources.delete_file_row(old.id, commit=False)
            thumb_size = (await asyncio.to_thread(thumb_dest.stat)).st_size
            await self._resources.add_file(
                resource.id,
                path=str(thumb_dest),
                sha256=None,
                size=thumb_size,
                format_="webp",
                role=FILE_ROLE_THUMBNAIL,
                commit=False,
            )
            if preview_dest is not None and preview_dest.is_file():
                preview_size = (await asyncio.to_thread(preview_dest.stat)).st_size
                await self._resources.add_file(
                    resource.id,
                    path=str(preview_dest),
                    sha256=None,
                    size=preview_size,
                    format_="jpg",
                    role=FILE_ROLE_PREVIEW,
                    commit=False,
                )
            await self._resources.commit()
            return ThumbnailBackfillResult(scanned=1, repaired=1)
        except Exception:
            await self._resources.rollback()
            logger.exception("thumbnail rebuild failed resource=%s", resource_id)
            return ThumbnailBackfillResult(scanned=1, failed=1)

    async def backfill_thumbnails(self, force: bool = False) -> ThumbnailBackfillResult:
        """Recreate missing grid thumbnails without touching primary files.

        ``force`` also rebuilds thumbnails that already exist, which is useful
        after an EXIF/orientation or thumbnail-rendering fix.
        """
        rows = await self._resources.media_primary_files()
        scanned = len(rows)
        repaired = 0
        skipped = 0
        failed = 0
        for primary_row, type_value in rows:
            type_ = ResourceType(type_value)
            resource = await self._resources.get(primary_row.resource_id)
            if resource is None or resource.id is None:
                failed += 1
                continue
            thumb = next(
                (file for file in resource.files if file.role == FILE_ROLE_THUMBNAIL),
                None,
            )
            if thumb is not None and thumb.path and Path(thumb.path).is_file() and not force:
                skipped += 1
                continue
            source = Path(primary_row.path)
            if not source.is_file():
                failed += 1
                continue
            role_paths = {FILE_ROLE_PRIMARY: source}
            thumb_source = source_for_grid_thumbnail(type_, role_paths)
            layout = layout_for(type_)
            if thumb_source is None or layout is None:
                skipped += 1
                continue
            try:
                if thumb is not None and thumb.id is not None:
                    await self._resources.delete_file_row(thumb.id, commit=False)
                package = ResourcePackage(
                    self._store_root,
                    type_,
                    resource.id,
                    self._ops,
                    cover_falls_back_to_primary=layout.cover_falls_back_to_primary,
                )
                dest = await asyncio.to_thread(package.put_thumbnail, thumb_source)
                if dest is None:
                    await self._resources.rollback()
                    failed += 1
                    continue
                size = await asyncio.to_thread(dest.stat)
                await self._resources.add_file(
                    resource.id,
                    path=str(dest),
                    sha256=None,
                    size=size.st_size,
                    format_="webp",
                    role=FILE_ROLE_THUMBNAIL,
                    commit=False,
                )
                if source.suffix.lower() in {".heic", ".heif"}:
                    preview_dest = await asyncio.to_thread(package.put_preview, source)
                    if preview_dest is not None:
                        old_preview = await self._resources.get_file_by_role(
                            resource.id, FILE_ROLE_PREVIEW
                        )
                        if old_preview is not None and old_preview.id is not None:
                            await self._resources.delete_file_row(
                                old_preview.id, commit=False
                            )
                        preview_size = (await asyncio.to_thread(preview_dest.stat)).st_size
                        await self._resources.add_file(
                            resource.id,
                            path=str(preview_dest),
                            sha256=None,
                            size=preview_size,
                            format_="jpg",
                            role=FILE_ROLE_PREVIEW,
                            commit=False,
                        )
                await self._resources.commit()
                repaired += 1
            except Exception:
                await self._resources.rollback()
                logger.exception("thumbnail backfill failed resource=%s", resource.id)
                failed += 1
        return ThumbnailBackfillResult(
            scanned=scanned,
            repaired=repaired,
            skipped=skipped,
            failed=failed,
        )
