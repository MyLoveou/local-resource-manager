"""包入库：过滤名、启动文件、漫画页序、过滤复制。"""

from __future__ import annotations

import os
import re
from pathlib import Path

from app.library.domain.type_profile import GAME_LAUNCH_EXTENSIONS, IMAGE_EXTENSIONS
from app.library.domain.models import is_hidden_fs_name
from app.shared.fs.file_ops import FileOps

_SKIP_FILES = frozenset({"thumbs.db", "desktop.ini"})
_COVER_STEMS = frozenset({"cover", "folder", "poster"})


def skip_entry(name: str) -> bool:
    """隐藏名与系统垃圾文件。"""
    return is_hidden_fs_name(name) or name.lower() in _SKIP_FILES


def normalize_path(path: Path) -> str:
    """Win 大小写不敏感比较用。"""
    return os.path.normcase(str(path.resolve()))


_SIDECAR_STEM_EXTENSIONS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".webp"})


def natural_key(path: Path) -> list[int | str]:
    """文件名自然序（数字按数值）。"""
    parts = re.split(r"(\d+)", path.name.lower())
    return [int(p) if p.isdigit() else p for p in parts]


def _natural_key(path: Path) -> list[int | str]:
    return natural_key(path)


def iter_files(root: Path) -> list[Path]:
    """深度遍历，跳过 skip_entry。"""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not skip_entry(d)]
        for name in filenames:
            if skip_entry(name):
                continue
            found.append(Path(dirpath) / name)
    return found


def find_launch(root: Path) -> Path | None:
    """启动文件优先级：同名 exe → launch.exe → game.exe → 任意 exe → bat/cmd/lnk。"""
    named = root / f"{root.name}.exe"
    if named.is_file() and not skip_entry(named.name):
        return named
    for candidate in ("launch.exe", "game.exe"):
        path = root / candidate
        if path.is_file() and not skip_entry(path.name):
            return path
    first_exe: Path | None = None
    first_script: Path | None = None
    for path in iter_files(root):
        suffix = path.suffix.lower()
        if suffix == ".exe" and first_exe is None:
            first_exe = path
        elif suffix in {".bat", ".cmd", ".lnk"} and first_script is None:
            first_script = path
        if first_exe is not None and first_script is not None:
            break
    return first_exe or first_script


def comic_pages(root: Path) -> list[Path]:
    """一层或递归收集图片，自然序。"""
    pages = [p for p in iter_files(root) if p.suffix.lower() in IMAGE_EXTENSIONS]
    pages.sort(key=_natural_key)
    return pages


def find_folder_cover(root: Path) -> Path | None:
    """游戏目录可选封面（小文件，可复制进库）。"""
    try:
        if not root.is_dir():
            return None
        for path in root.iterdir():
            if not path.is_file() or skip_entry(path.name):
                continue
            if path.stem.lower() in _COVER_STEMS and path.suffix.lower() in IMAGE_EXTENSIONS:
                return path
    except OSError:
        return None
    return None


def find_sidecar_cover(source: Path) -> Path | None:
    """单文件旁海报（cover/folder/poster）或同主文件名的 jpg/png/webp。"""
    try:
        if not source.is_file():
            return None
        parent = source.parent
        poster = find_folder_cover(parent)
        if poster is not None:
            return poster
        source_key = source.resolve()
        stem = source.stem.lower()
        for path in sorted(parent.iterdir(), key=lambda item: item.name.lower()):
            if not path.is_file() or skip_entry(path.name):
                continue
            if path.suffix.lower() not in _SIDECAR_STEM_EXTENSIONS:
                continue
            if path.stem.lower() != stem:
                continue
            try:
                if path.resolve() == source_key:
                    continue
            except OSError:
                if path == source:
                    continue
            return path
    except OSError:
        return None
    return None


def copy_tree_filtered(ops: FileOps, src: Path, dest: Path) -> None:
    """复制整树，跳过隐藏与系统垃圾。"""
    dest.mkdir(parents=True, exist_ok=True)
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if not skip_entry(d)]
        rel = Path(dirpath).relative_to(src)
        target_dir = dest / rel
        target_dir.mkdir(parents=True, exist_ok=True)
        for name in filenames:
            if skip_entry(name):
                continue
            ops.copy(Path(dirpath) / name, target_dir / name)


# 启动扩展名给调用方查表，避免 if game
LAUNCH_EXTENSIONS = GAME_LAUNCH_EXTENSIONS
