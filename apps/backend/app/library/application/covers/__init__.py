"""导入与手指定封面。"""

from app.library.application.covers.attach import attach_cover_image
from app.library.application.covers.cbz import extract_cbz_first_image
from app.library.application.covers.embedded import extract_audio_cover
from app.library.application.covers.epub import extract_epub_cover
from app.library.application.covers.exe_icon import extract_exe_icon
from app.library.application.covers.frame import extract_video_frame
from app.library.application.covers.ingest import apply_ingest_cover
from app.library.application.covers.lnk import resolve_lnk_target
from app.library.application.covers.origin import (
    COVER_ORIGIN_EMBEDDED,
    COVER_ORIGIN_EXE,
    COVER_ORIGIN_FOLDER,
    COVER_ORIGIN_FRAME,
    COVER_ORIGIN_PAGE,
    COVER_ORIGIN_USER,
    CoverNotAllowedError,
    is_user_locked,
    merge_cover_origin,
)
from app.library.application.covers.pdf_page import render_pdf_first_page

__all__ = [
    "COVER_ORIGIN_EMBEDDED",
    "COVER_ORIGIN_EXE",
    "COVER_ORIGIN_FOLDER",
    "COVER_ORIGIN_FRAME",
    "COVER_ORIGIN_PAGE",
    "COVER_ORIGIN_USER",
    "CoverNotAllowedError",
    "apply_ingest_cover",
    "attach_cover_image",
    "extract_audio_cover",
    "extract_cbz_first_image",
    "extract_epub_cover",
    "extract_exe_icon",
    "extract_video_frame",
    "is_user_locked",
    "merge_cover_origin",
    "render_pdf_first_page",
    "resolve_lnk_target",
]
