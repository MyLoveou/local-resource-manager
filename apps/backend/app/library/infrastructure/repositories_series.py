"""详情页的季/集/特典装载。

从 `repositories_resources` 拆出来：那个文件已到规模基线，且这段逻辑与
资源列表无关（只在详情 hydrate 时执行）。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.domain.media_types import is_series_type
from app.library.domain.models import (
    Resource,
    SeriesEpisode,
    SeriesExtra,
    SeriesSeason,
)
from app.library.infrastructure.media_paths import episode_cover_url
from app.library.infrastructure.orm import (
    EpisodeRow,
    ExtraRow,
    SeasonRow,
    SubtitleTrackRow,
)


async def attach_series_tree(session: AsyncSession, resource: Resource) -> None:
    """给资源装上 seasons / extras；非系列类型直接返回。"""
    if resource.id is None or not is_series_type(resource.type):
        return

    files_by_id = {f.id: f for f in resource.files if f.id is not None}
    season_rows = (
        await session.execute(
            select(SeasonRow)
            .where(SeasonRow.resource_id == resource.id)
            .order_by(SeasonRow.sort_index, SeasonRow.season_number, SeasonRow.id)
        )
    ).scalars().all()

    subtitle_episode_ids = set(
        (
            await session.execute(
                select(SubtitleTrackRow.episode_id).where(
                    SubtitleTrackRow.resource_id == resource.id,
                    SubtitleTrackRow.episode_id.is_not(None),
                )
            )
        ).scalars().all()
    )

    seasons: list[SeriesSeason] = []
    for season in season_rows:
        ep_rows = (
            await session.execute(
                select(EpisodeRow)
                .where(EpisodeRow.season_id == season.id, EpisodeRow.status == "active")
                .order_by(EpisodeRow.sort_index, EpisodeRow.episode_number, EpisodeRow.id)
            )
        ).scalars().all()
        episodes: list[SeriesEpisode] = []
        for episode in ep_rows:
            media = files_by_id.get(episode.file_id)
            episodes.append(
                SeriesEpisode(
                    id=episode.id,
                    file_id=episode.file_id,
                    episode_number=episode.episode_number,
                    title=episode.title,
                    duration=media.duration if media else None,
                    width=media.width if media else None,
                    height=media.height if media else None,
                    cover_url=episode_cover_url(resource.id, episode.cover_file_id),
                    has_cover=episode.cover_file_id is not None,
                    has_subtitles=episode.id in subtitle_episode_ids,
                )
            )
        seasons.append(
            SeriesSeason(
                id=season.id,
                season_number=season.season_number,
                title=season.title,
                episodes=episodes,
            )
        )

    extra_rows = (
        await session.execute(
            select(ExtraRow)
            .where(ExtraRow.resource_id == resource.id, ExtraRow.status == "active")
            .order_by(ExtraRow.sort_index, ExtraRow.id)
        )
    ).scalars().all()
    extras: list[SeriesExtra] = []
    for extra in extra_rows:
        media = files_by_id.get(extra.file_id)
        extras.append(
            SeriesExtra(
                id=extra.id,
                file_id=extra.file_id,
                title=extra.title,
                duration=media.duration if media else None,
            )
        )

    resource.seasons = seasons
    resource.extras = extras
