"""Runtime paths that can be selected by persisted settings at startup."""

from __future__ import annotations

from pathlib import Path

_library_root: Path | None = None


def set_library_root(path: Path | None) -> None:
    global _library_root
    _library_root = path.resolve() if path else None


def library_root(db_path: Path) -> Path:
    if _library_root is not None:
        return _library_root
    return db_path.parent / "library"
