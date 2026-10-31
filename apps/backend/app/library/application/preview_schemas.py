"""导入预览的请求/响应模型。

单独放一个模块：`schemas.py` 已经接近 500 行目标，预览是新增的一小块，
拆出来比继续把它撑大更好。
"""

from __future__ import annotations

from pydantic import Field

from app.library.domain.models import ResourceType
from app.shared.models import ApiModel


class ImportPreviewIn(ApiModel):
    """预览请求：只支持整目录。"""

    type: ResourceType
    path: str


class PreviewEpisodeOut(ApiModel):
    season: int
    episode: int
    title: str | None = None
    file: str


class PreviewSeasonOut(ApiModel):
    season: int
    episodes: list[PreviewEpisodeOut] = Field(default_factory=list)


class PreviewExtraOut(ApiModel):
    title: str
    file: str


class ImportPreviewOut(ApiModel):
    """预览结果：导入会建成什么样。"""

    ok: bool
    code: str | None = None
    message: str
    details: list[str] = Field(default_factory=list)
    total_files: int = 0
    seasons: list[PreviewSeasonOut] = Field(default_factory=list)
    extras: list[PreviewExtraOut] = Field(default_factory=list)
