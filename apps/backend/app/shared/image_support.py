"""Optional image decoder registration shared by library and AI code."""

from __future__ import annotations

from app.shared.log import logger

_registered = False


def register_optional_image_decoders() -> None:
    """Register HEIF/HEIC support when pillow-heif is installed."""
    global _registered
    if _registered:
        return
    _registered = True
    try:
        import pillow_heif
    except ImportError:
        logger.info("pillow-heif 未安装，HEIC 仅能外部打开")
        return
    try:
        pillow_heif.register_heif_opener()
        logger.info("HEIC 解码已启用")
    except Exception as exc:  # noqa: BLE001 - optional decoder must not block startup
        logger.warning("注册 HEIC 解码失败: %s", exc)
