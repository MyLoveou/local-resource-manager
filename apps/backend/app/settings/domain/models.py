"""设置应用 · 领域实体与站点适配器标识。"""
from enum import Enum
from typing import Any

from pydantic import Field

from app.shared.models import ApiModel


class AdapterKey(str, Enum):
    """元数据站点适配器标识（SearXNG 检索 + 站点详情适配器）。"""

    OG = "og"
    TMDB = "tmdb"
    BANGUMI = "bangumi"
    MIKAN = "mikan"
    PIXIV = "pixiv"
    DOUBAN = "douban"


class Settings(ApiModel):
    """应用设置（KV 结构）。"""

    key: str
    value: dict[str, Any]


class SiteAdapter(ApiModel):
    """站点适配器配置（插件式）。key 为常量枚举 AdapterKey。"""

    id: int | None = None
    key: AdapterKey
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
