"""领域常量（单一事实源）。

跨子应用共享的枚举/路由表。避免在业务代码中散落裸字符串。
"""
from enum import Enum


class Protocol(str, Enum):
    """下载协议。"""

    HTTP = "http"
    FTP = "ftp"
    MAGNET = "magnet"
    TORRENT = "torrent"


class DownloadEngine(str, Enum):
    """下载引擎。"""

    ARIA2 = "aria2"
    RQBIT = "rqbit"
    YTDLP = "yt-dlp"
    HTTPX = "httpx"


class AdapterKey(str, Enum):
    """元数据站点适配器标识（SearXNG 检索 + 站点详情适配器）。"""

    OG = "og"
    TMDB = "tmdb"
    BANGUMI = "bangumi"
    MIKAN = "mikan"
    PIXIV = "pixiv"
    DOUBAN = "douban"


class SourceKind(str, Enum):
    """导入来源：文件或多文件 / 一次选目录。"""

    FILE = "file"
    DIRECTORY = "directory"


HIDDEN_NAME_PREFIX = "."

API_CODE_OK = 0
API_STATUS_SUCCESS = "success"
API_STATUS_ERROR = "error"
API_MESSAGE_OK = "ok"

ENVELOPE_SKIP_PATHS = ("/docs", "/redoc", "/openapi.json")


def is_hidden_fs_name(name: str) -> bool:
    """点开头的文件或目录不参与导入收集。"""
    return name.startswith(HIDDEN_NAME_PREFIX)


# 协议 → 默认引擎 路由表（aria2 兼 BT 兜底；rqbit 负责现代 BT/流式）
PROTOCOL_TO_ENGINE: dict[Protocol, DownloadEngine] = {
    Protocol.HTTP: DownloadEngine.ARIA2,
    Protocol.FTP: DownloadEngine.ARIA2,
    Protocol.MAGNET: DownloadEngine.RQBIT,
    Protocol.TORRENT: DownloadEngine.RQBIT,
}
