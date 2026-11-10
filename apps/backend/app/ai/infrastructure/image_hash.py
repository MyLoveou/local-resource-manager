"""Perceptual dHash for cheap near-duplicate detection."""

from __future__ import annotations

from pathlib import Path


def dhash(path: Path) -> str | None:
    """Return a 64-bit difference hash as 16 hex chars, or None."""
    try:
        from PIL import Image, ImageOps

        with Image.open(path) as opened:
            image = ImageOps.exif_transpose(opened).convert("L")
            image = image.resize((9, 8), Image.Resampling.BILINEAR)
            pixels = list(image.getdata())
        bits = 0
        for row in range(8):
            offset = row * 9
            for column in range(8):
                bits = (bits << 1) | int(pixels[offset + column] > pixels[offset + column + 1])
        return f"{bits:016x}"
    except Exception:
        return None


def hamming(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def dhash_many(paths: list[Path]) -> list[str | None]:
    return [dhash(path) for path in paths]
