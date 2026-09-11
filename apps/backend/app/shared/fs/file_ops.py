"""通用文件操作（复制/移动/重命名）。入库写盘只走此类。"""

from pathlib import Path
import shutil


class FileOps:
    """磁盘写操作入口。"""

    def copy(self, src: Path, dest: Path) -> Path:
        """复制文件到目标（自动建父目录）。"""
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return dest

    def move(self, src: Path, dest: Path) -> Path:
        """移动文件到目标（自动建父目录）。"""
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        return dest

    def remove_tree(self, path: Path) -> None:
        """删除目录树（失败入库回滚时用）。"""
        if path.exists():
            shutil.rmtree(path)

    def rename(self, src: Path, dest: Path) -> Path:
        """同盘重命名。"""
        dest.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dest)
        return dest
