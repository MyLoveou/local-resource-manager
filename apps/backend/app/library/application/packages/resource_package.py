"""通用资源包：{store}/{type}/{id}/ 与角色文件。"""

from pathlib import Path

from app.shared.fs.file_ops import FileOps
from app.shared.media_types import FILE_ROLE_SUBTITLE
from app.shared.models import ResourceType


def default_library_store(db_path: Path) -> Path:
    """实现默认：与 db 同级的 library/。产品设置项本轮不做。"""
    return db_path.parent / "library"


class ResourcePackage:
    """一个资源在库内的目录。路径只在此类内拼接。"""

    def __init__(
        self,
        store_root: Path,
        type_: ResourceType,
        resource_id: int,
        file_ops: FileOps,
        *,
        cover_falls_back_to_primary: bool,
    ) -> None:
        self._store_root = store_root
        self._type = type_
        self._resource_id = resource_id
        self._ops = file_ops
        self.cover_falls_back_to_primary = cover_falls_back_to_primary

    @property
    def root(self) -> Path:
        return self._store_root / self._type.value / str(self._resource_id)

    def ensure_dir(self) -> Path:
        """创建资源包目录。"""
        self.root.mkdir(parents=True, exist_ok=True)
        return self.root

    def put_role(self, role: str, src: Path, dest_name: str | None = None) -> Path:
        """按角色复制进包内。字幕可用 dest_name 覆盖源文件名。"""
        self.ensure_dir()
        if role == FILE_ROLE_SUBTITLE:
            name = Path(dest_name or src.name).name
            dest = (self.root / "subtitles" / name).resolve()
        else:
            dest = (self.root / f"{role}{src.suffix.lower()}").resolve()
        try:
            dest.relative_to(self.root.resolve())
        except ValueError as exc:
            raise ValueError("destination outside package") from exc
        return self._ops.copy(src, dest)

    def put_subtitle(self, src: Path, dest_name: str) -> Path:
        """复制字幕并使用给定文件名。"""
        return self.put_role("subtitle", src, dest_name)

    def put_primary(self, src: Path) -> Path:
        return self.put_role("primary", src)

    def put_cover(self, src: Path) -> Path:
        return self.put_role("cover", src)

    def resolve_cover(self, role_paths: dict[str, Path]) -> Path | None:
        """有 cover 角色用它；否则按类型是否回退到 primary。"""
        cover = role_paths.get("cover")
        if cover is not None:
            return cover
        if self.cover_falls_back_to_primary:
            return role_paths.get("primary")
        return None
