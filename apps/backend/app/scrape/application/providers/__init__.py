"""按资源类型选择发现源。同一类型可有多个渠道。"""

from app.scrape.application.providers.bangumi import BangumiProvider
from app.scrape.application.providers.base import MetadataProvider
from app.scrape.application.providers.bilibili import BilibiliProvider
from app.scrape.application.providers.mikan import MikanProvider
from app.scrape.application.providers.og import OgProvider
from app.scrape.application.providers.tmdb import TmdbProvider
from app.shared.models import ResourceType

_SCRAPEABLE = frozenset({ResourceType.VIDEO, ResourceType.ANIME, ResourceType.IMAGE})
_IMPORT_ENQUEUE = frozenset({ResourceType.VIDEO, ResourceType.ANIME})


def is_scrapeable(type_: ResourceType) -> bool:
    return type_ in _SCRAPEABLE


def enqueue_after_import(type_: ResourceType) -> bool:
    return type_ in _IMPORT_ENQUEUE


def providers_for(type_: ResourceType) -> list[MetadataProvider]:
    if type_ == ResourceType.VIDEO:
        return [TmdbProvider(), BilibiliProvider()]
    if type_ == ResourceType.ANIME:
        return [BangumiProvider(), MikanProvider()]
    if type_ == ResourceType.IMAGE:
        return [OgProvider()]
    raise RuntimeError("类型不支持获取元数据")


def provider_for(type_: ResourceType) -> MetadataProvider:
    return providers_for(type_)[0]


def provider_for_key(key: str) -> MetadataProvider:
    prefix = (key.split(":", 1)[0] if key else "").lower()
    if prefix == "tmdb":
        return TmdbProvider()
    if prefix == "bangumi":
        return BangumiProvider()
    if prefix == "mikan":
        return MikanProvider()
    if prefix == "bilibili":
        return BilibiliProvider()
    if prefix == "og":
        return OgProvider()
    raise RuntimeError("未知元数据来源")
