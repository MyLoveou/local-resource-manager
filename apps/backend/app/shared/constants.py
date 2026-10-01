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

# 鉴权豁免：健康检查（/health 与各子应用 /xxx/health）、OpenAPI 文档、
# 媒体字节流（img / video / model-viewer 无法带请求头）
AUTH_EXEMPT_PREFIXES = ("/docs", "/redoc", "/openapi.json")
AUTH_EXEMPT_SUFFIXES = ("/health", "/content")
AUTH_EXEMPT_PATHS = ("/scrape/proxy-image",)


def is_hidden_fs_name(name: str) -> bool:
    """点开头的文件或目录不参与导入收集。"""
    return name.startswith(HIDDEN_NAME_PREFIX)


def is_auth_exempt(path: str) -> bool:
    """该路径是否免 token 校验（清单集中在本文，不在路由里写条件）。"""
    if path in AUTH_EXEMPT_PATHS:
        return True
    if path.startswith(AUTH_EXEMPT_PREFIXES):
        return True
    return path.endswith(AUTH_EXEMPT_SUFFIXES)


# 协议 → 默认引擎 路由表（aria2 兼 BT 兜底；rqbit 负责现代 BT/流式）
PROTOCOL_TO_ENGINE: dict[Protocol, DownloadEngine] = {
    Protocol.HTTP: DownloadEngine.ARIA2,
    Protocol.FTP: DownloadEngine.ARIA2,
    Protocol.MAGNET: DownloadEngine.RQBIT,
    Protocol.TORRENT: DownloadEngine.RQBIT,
}
