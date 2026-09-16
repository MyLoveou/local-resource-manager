"""按资源类型的包布局（本轮视频仅 primary）。"""

from dataclasses import dataclass
from pathlib import Path

from app.library.application.packages.resource_package import ResourcePackage
from app.shared.media_types import FILE_ROLE_PRIMARY
from app.shared.models import ResourceType


@dataclass(frozen=True)
class PackageLayout:
    """类型如何往包里放文件。"""

    type: ResourceType
    cover_falls_back_to_primary: bool

    def place_primary(self, package: ResourcePackage, source: Path) -> dict[str, Path]:
        """本轮各类型都只放 primary；后续视频可在此扩展字幕/封面。"""
        dest = package.put_primary(source)
        return {FILE_ROLE_PRIMARY: dest}


IMAGE_LAYOUT = PackageLayout(ResourceType.IMAGE, cover_falls_back_to_primary=True)
VIDEO_LAYOUT = PackageLayout(ResourceType.VIDEO, cover_falls_back_to_primary=False)
SERIES_LAYOUT = PackageLayout(ResourceType.ANIME, cover_falls_back_to_primary=True)

_LAYOUTS = {
    ResourceType.IMAGE: IMAGE_LAYOUT,
    ResourceType.VIDEO: VIDEO_LAYOUT,
    ResourceType.ANIME: SERIES_LAYOUT,
    ResourceType.AV: PackageLayout(ResourceType.AV, cover_falls_back_to_primary=True),
}


def layout_for(type_: ResourceType) -> PackageLayout | None:
    """已启用类型的布局；未登记则 None。"""
    return _LAYOUTS.get(type_)
