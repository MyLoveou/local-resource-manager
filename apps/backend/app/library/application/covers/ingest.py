"""导入时解析封面源并写入。"""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import Callable
from pathlib import Path

from app.library.application.covers.attach import attach_cover_image
from app.library.application.covers.cbz import extract_cbz_first_image
from app.library.application.covers.embedded import extract_audio_cover
from app.library.application.covers.epub import extract_epub_cover
from app.library.application.covers.exe_icon import extract_exe_icon
from app.library.application.covers.frame import extract_video_frame
from app.library.application.covers.lnk import resolve_lnk_target
from app.library.application.covers.origin import (
    COVER_ORIGIN_EMBEDDED,
    COVER_ORIGIN_EXE,
    COVER_ORIGIN_FOLDER,
    COVER_ORIGIN_FRAME,
    COVER_ORIGIN_PAGE,
    is_user_locked,
)
from app.library.application.covers.pdf_page import render_pdf_first_page
from app.library.application.ingest.placement import find_folder_cover, find_sidecar_cover
from app.library.application.packages.resource_package import ResourcePackage
from app.library.domain.type_profile import IMAGE_EXTENSIONS
from app.library.infrastructure.repositories import ResourceRepository
from app.shared.log import logger
from app.library.domain.media_types import FILE_ROLE_PRIMARY
from app.library.domain.models import (
    Resource,
    ResourceType,
)


async def apply_ingest_cover(
    resources: ResourceRepository,
    resource: Resource,
    package: ResourcePackage,
    type_: ResourceType,
    *,
    role_paths: dict[str, Path],
    source_root: Path | None = None,
    source_file: Path | None = None,
    launch_path: Path | None = None,
    video_path: Path | None = None,
    video_duration: float | None = None,
    audio_path: Path | None = None,
    episode_path: Path | None = None,
    episode_duration: float | None = None,
) -> None:
    """新导入自动封面。已锁定用户封面则跳过。失败静默。"""
    try:
        await _apply_ingest_cover_inner(
            resources,
            resource,
            package,
            type_,
            role_paths=role_paths,
            source_root=source_root,
            source_file=source_file,
            launch_path=launch_path,
            video_path=video_path,
            video_duration=video_duration,
            audio_path=audio_path,
            episode_path=episode_path,
            episode_duration=episode_duration,
        )
    except Exception as exc:
        logger.warning("自动封面跳过 resource=%s: %s", resource.id, exc)


async def _apply_ingest_cover_inner(
    resources: ResourceRepository,
    resource: Resource,
    package: ResourcePackage,
    type_: ResourceType,
    *,
    role_paths: dict[str, Path],
    source_root: Path | None = None,
    source_file: Path | None = None,
    launch_path: Path | None = None,
    video_path: Path | None = None,
    video_duration: float | None = None,
    audio_path: Path | None = None,
    episode_path: Path | None = None,
    episode_duration: float | None = None,
) -> None:
    if is_user_locked(resource):
        return
    if type_ == ResourceType.IMAGE:
        return
    sidecar = None
    if source_root is not None:
        sidecar = await asyncio.to_thread(find_folder_cover, source_root)
    elif source_file is not None:
        sidecar = await asyncio.to_thread(find_sidecar_cover, source_file)
    if sidecar is not None:
        await attach_cover_image(
            resources, resource, package, sidecar, COVER_ORIGIN_FOLDER, role_paths=role_paths
        )
        return
    if type_ in {ResourceType.VIDEO} and video_path is not None:
        await _attach_frame(resources, resource, package, role_paths, video_path, video_duration)
        return
    if type_ in {ResourceType.ANIME, ResourceType.AV} and episode_path is not None:
        await _attach_frame(resources, resource, package, role_paths, episode_path, episode_duration)
        return
    if type_ == ResourceType.AUDIO and audio_path is not None:
        await _attach_extracted(
            resources, resource, package, role_paths, audio_path, extract_audio_cover, COVER_ORIGIN_EMBEDDED
        )
        return
    if type_ == ResourceType.NOVEL:
        await _attach_novel(resources, resource, package, role_paths, source_file, role_paths.get(FILE_ROLE_PRIMARY))
        return
    if type_ == ResourceType.COMIC:
        await _attach_comic(resources, resource, package, role_paths, source_file, role_paths.get(FILE_ROLE_PRIMARY))
        return
    if type_ == ResourceType.GAME:
        await _attach_game_icon(resources, resource, package, role_paths, launch_path)


async def _attach_extracted(
    resources: ResourceRepository,
    resource: Resource,
    package: ResourcePackage,
    role_paths: dict[str, Path],
    src: Path,
    extractor: Callable[[Path, Path], bool],
    origin: str,
    dest_name: str = "extracted.jpg",
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / dest_name
        ok = await asyncio.to_thread(extractor, src, dest)
        if not ok:
            return
        await attach_cover_image(resources, resource, package, dest, origin, role_paths=role_paths)


async def _attach_frame(
    resources: ResourceRepository,
    resource: Resource,
    package: ResourcePackage,
    role_paths: dict[str, Path],
    video: Path,
    duration: float | None,
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "frame.jpg"
        ok = await asyncio.to_thread(extract_video_frame, video, dest, duration=duration)
        if not ok:
            return
        await attach_cover_image(
            resources, resource, package, dest, COVER_ORIGIN_FRAME, role_paths=role_paths
        )


async def _attach_novel(
    resources: ResourceRepository,
    resource: Resource,
    package: ResourcePackage,
    role_paths: dict[str, Path],
    source_file: Path | None,
    primary: Path | None,
) -> None:
    src = primary if primary is not None else source_file
    if src is None:
        return
    suffix = src.suffix.lower()
    if suffix == ".epub":
        await _attach_extracted(
            resources, resource, package, role_paths, src, extract_epub_cover, COVER_ORIGIN_EMBEDDED
        )
        return
    if suffix == ".pdf":
        await _attach_extracted(
            resources, resource, package, role_paths, src, render_pdf_first_page, COVER_ORIGIN_PAGE
        )


async def _attach_comic(
    resources: ResourceRepository,
    resource: Resource,
    package: ResourcePackage,
    role_paths: dict[str, Path],
    source_file: Path | None,
    primary: Path | None,
) -> None:
    probe = primary if primary is not None else source_file
    suffix = probe.suffix.lower() if probe is not None else ""
    if suffix == ".cbr":
        return
    if suffix == ".cbz":
        archive = primary if primary is not None else source_file
        if archive is None:
            return
        await _attach_extracted(
            resources, resource, package, role_paths, archive, extract_cbz_first_image, COVER_ORIGIN_PAGE
        )
        return
    page = primary
    if page is not None and page.suffix.lower() in IMAGE_EXTENSIONS:
        await attach_cover_image(
            resources, resource, package, page, COVER_ORIGIN_PAGE, role_paths=role_paths
        )


async def _attach_game_icon(
    resources: ResourceRepository,
    resource: Resource,
    package: ResourcePackage,
    role_paths: dict[str, Path],
    launch_path: Path | None,
) -> None:
    if launch_path is None:
        return
    exe = launch_path
    suffix = launch_path.suffix.lower()
    if suffix == ".lnk":
        resolved = await asyncio.to_thread(resolve_lnk_target, launch_path)
        if resolved is None or resolved.suffix.lower() != ".exe":
            return
        exe = resolved
    elif suffix != ".exe":
        return
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "icon.png"
        ok = await asyncio.to_thread(extract_exe_icon, exe, dest)
        if not ok:
            return
        await attach_cover_image(
            resources, resource, package, dest, COVER_ORIGIN_EXE, role_paths=role_paths
        )
