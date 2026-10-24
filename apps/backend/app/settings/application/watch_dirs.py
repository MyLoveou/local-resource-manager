"""监视目录 · 归一化与校验（纯函数，算法切片）。"""
from pathlib import Path

from app.settings.application.errors import SettingsError
from app.shared.utils.file_watcher import File_Extension_Map

# 可监视类型 = 有扩展名映射的类型（与 File_Extension_Map 一致；
# anime/av/game/work_directory 是目录型/无单文件扩展名，不在此列）
WATCHABLE_TYPES = frozenset(t.value for t in File_Extension_Map)


def normalize_watch_dirs(raw: dict | None) -> dict[str, list[str]]:
    """过滤非法类型键；目录去空、去重、去尾分隔符，保留顺序。"""
    result: dict[str, list[str]] = {}
    for key, dirs in (raw or {}).items():
        if key not in WATCHABLE_TYPES:
            continue
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in dirs or []:
            if item is None:
                continue
            text = str(item).strip()
            if not text:
                continue
            normalized = text.rstrip("\\/")
            if not normalized:
                continue
            if normalized not in seen:
                seen.add(normalized)
                cleaned.append(normalized)
        if cleaned:
            result[key] = cleaned
    return result


def validate_watch_dirs(dirs: dict[str, list[str]]) -> None:
    """保存前校验：目录必须存在且是目录；失败抛 400。"""
    for type_value, paths in dirs.items():
        for path in paths:
            if not Path(path).is_dir():
                raise SettingsError(f"[{type_value}] 目录不存在: {path}", 400)
