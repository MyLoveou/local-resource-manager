"""按扩展名收集待导入路径。"""

import os
from pathlib import Path

from app.library.application.importers.image import EXTENSIONS as IMAGE_EXTENSIONS
from app.library.application.importers.video import EXTENSIONS as VIDEO_EXTENSIONS
from app.shared.models import ResourceType

_EXT = {
    ResourceType.IMAGE: IMAGE_EXTENSIONS,
    ResourceType.VIDEO: VIDEO_EXTENSIONS,
}


class Importer:
    """类型策略：只负责找出候选文件，不拼库内路径。"""

    def __init__(self, type_: ResourceType) -> None:
        self.type = type_
        self.extensions = _EXT[type_]

    def matches(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lower() in self.extensions and not path.name.startswith(".")

    def collect(self, source_kind: str, paths: list[Path]) -> list[Path]:
        """file：过滤已给路径；directory：递归该类型扩展名。"""
        found: list[Path] = []
        if source_kind == "file":
            for raw in paths:
                path = raw.resolve()
                if self.matches(path):
                    found.append(path)
            return found
        if source_kind == "directory":
            root = paths[0].resolve()
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if not d.startswith(".")]
                for name in filenames:
                    if name.startswith("."):
                        continue
                    candidate = Path(dirpath) / name
                    if self.matches(candidate):
                        found.append(candidate)
            return found
        return []


_IMPORTERS = {
    ResourceType.IMAGE: Importer(ResourceType.IMAGE),
    ResourceType.VIDEO: Importer(ResourceType.VIDEO),
}


def importer_for(type_: ResourceType) -> Importer | None:
    return _IMPORTERS.get(type_)
