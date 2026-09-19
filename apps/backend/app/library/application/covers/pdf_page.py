"""PDF 第一页渲成 JPEG。"""

from __future__ import annotations

from pathlib import Path

from app.shared.log import logger
from app.shared.media_types import THUMB_MAX_EDGE_PX


def render_pdf_first_page(pdf: Path, dest_jpg: Path) -> bool:
    """pypdfium2 渲第 1 页；失败返回 False。"""
    try:
        import pypdfium2 as pdfium
    except ImportError:
        logger.warning("未安装 pypdfium2，跳过 PDF 封面")
        return False
    document = None
    page = None
    bitmap = None
    try:
        document = pdfium.PdfDocument(str(pdf))
        if len(document) < 1:
            return False
        page = document[0]
        width, height = page.get_size()
        longest = max(float(width), float(height), 1.0)
        max_edge = float(THUMB_MAX_EDGE_PX * 4)
        scale = min(max_edge / longest, 2.0)
        bitmap = page.render(scale=scale)
        image = bitmap.to_pil()
        dest_jpg.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest_jpg.with_name(f"{dest_jpg.stem}.part.jpg")
        image.convert("RGB").save(tmp, format="JPEG", quality=90)
        tmp.replace(dest_jpg)
        return dest_jpg.is_file() and dest_jpg.stat().st_size > 0
    except (OSError, ValueError, MemoryError, pdfium.PdfiumError) as exc:
        logger.warning("PDF 封面渲染失败 %s: %s", pdf, exc)
        return False
    finally:
        if bitmap is not None:
            close = getattr(bitmap, "close", None)
            if close is not None:
                close()
        if page is not None:
            close = getattr(page, "close", None)
            if close is not None:
                close()
        if document is not None:
            document.close()
