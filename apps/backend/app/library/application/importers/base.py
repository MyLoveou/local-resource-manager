"""按扩展名收集待导入路径。"""

import os
from collections.abc import Callable
from pathlib import Path

from app.shared.constants import SourceKind, is_hidden_fs_name
from app.shared.media_types import IMPORT_EXTENSIONS, import_extensions
from app.shared.models import ResourceType


class Importer:
    """类型策略：只负责找出候选文件，不拼库内路径。"""

    def __init__(self, type_: ResourceType) -> None:
        self.type = type_
        exts = import_extensions(type_)
        if exts is None:
            raise ValueError(f"unsupported import type: {type_}")
        self.extensions = exts

    def matches(self, path: Path) -> bool:
        return (
            path.is_file()
            and path.suffix.lower() in self.extensions
            and not is_hidden_fs_name(path.name)
        )

    def _collect_files(self, paths: list[Path]) -> list[Path]:
        found: list[Path] = []
        for raw in paths:
            path = raw.resolve()
            if self.matches(path):
                found.append(path)
        return found

    def _collect_directory(self, paths: list[Path]) -> list[Path]:
        found: list[Path] = []
        root = paths[0].resolve()
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not is_hidden_fs_name(d)]
            for name in filenames:
                if is_hidden_fs_name(name):
                    continue
                candidate = Path(dirpath) / name
                if self.matches(candidate):
                    found.append(candidate)
        return found

    def collect(self, source_kind: str, paths: list[Path]) -> list[Path]:
        """按来源种类查表收集，不在此处写死 file/directory 字符串。"""
        collectors: dict[str, Callable[[list[Path]], list[Path]]] = {
            SourceKind.FILE.value: self._collect_files,
            SourceKind.DIRECTORY.value: self._collect_directory,
        }
        collector = collectors.get(source_kind)
        if collector is None:
            return []
        return collector(paths)


_IMPORTERS = {type_: Importer(type_) for type_ in IMPORT_EXTENSIONS}


def importer_for(type_: ResourceType) -> Importer | None:
    return _IMPORTERS.get(type_)
