"""Signed URLs for files inside a resource package."""

from __future__ import annotations

from app.shared.media_auth import sign_media_path


def file_content_url(resource_id: int, file_id: int) -> str:
    path = f"/library/resources/{resource_id}/files/{file_id}/content"
    return sign_media_path(path) or path


def media_path(path: str | None) -> str | None:
    return sign_media_path(path)


def resource_thumb_url(resource_id: int, file_id: int | None) -> str:
    """AI 等跨模块场景用的缩略图 URL；有缩略图文件走文件流，否则回退主文件。

    媒体元素发不出 Authorization 头，所以必须签名，否则启用 token 后一律 401。
    """
    if file_id is not None:
        return file_content_url(resource_id, file_id)
    raw = f"/library/resources/{resource_id}/content"
    return sign_media_path(raw) or raw
