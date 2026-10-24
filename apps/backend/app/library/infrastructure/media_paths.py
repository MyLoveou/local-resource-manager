"""Signed URLs for files inside a resource package."""

from __future__ import annotations

from app.shared.media_auth import sign_media_path


def file_content_url(resource_id: int, file_id: int) -> str:
    path = f"/library/resources/{resource_id}/files/{file_id}/content"
    return sign_media_path(path) or path


def media_path(path: str | None) -> str | None:
    return sign_media_path(path)
