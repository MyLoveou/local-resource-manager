"""导出命名纯函数（算法切片）：合集导出文件按顺序编号 + 清理非法字符。"""

import re

_INVALID = re.compile(r'[\\/:*?"<>|\r\n]')


def safe_title(title: str, max_len: int = 80) -> str:
    """清理文件系统非法字符；空标题兜底 untitled。"""
    text = _INVALID.sub("_", title or "").strip()
    text = text[:max_len].rstrip(" .")
    return text or "untitled"


def export_name(index: int, title: str, ext: str) -> str:
    """导出文件名：`{index:03d}_{安全标题}{后缀}`。"""
    suffix = ext if ext.startswith(".") else f".{ext}"
    return f"{index:03d}_{safe_title(title)}{suffix}"
