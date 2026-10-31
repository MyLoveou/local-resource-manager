"""资源库应用 · SQLAlchemy ORM 表模型。"""
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db.base import Base, _SQLITE_NOW


class ResourceRow(Base):
    __tablename__ = "resources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False, default="")
    description: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String)
    rating: Mapped[float | None] = mapped_column(Float)
    cover_path: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    deleted_at: Mapped[str | None] = mapped_column(String)
    last_scraped_at: Mapped[str | None] = mapped_column(String)
    scraped_source: Mapped[str | None] = mapped_column(String)
    extra: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    synopsis: Mapped[str | None] = mapped_column(Text)
    storage_kind: Mapped[str] = mapped_column(String, nullable=False, default="owned")
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL")
    )
    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=_SQLITE_NOW)
    updated_at: Mapped[str] = mapped_column(String, nullable=False, server_default=_SQLITE_NOW)
    sha256: Mapped[str] = mapped_column(String, nullable=False, default="")
    source_name: Mapped[str | None] = mapped_column(String)
    timeline_visible: Mapped[int | None] = mapped_column(Integer)
    map_visible: Mapped[int | None] = mapped_column(Integer)


class WorkRow(Base):
    __tablename__ = "works"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=_SQLITE_NOW)
    updated_at: Mapped[str] = mapped_column(String, nullable=False, server_default=_SQLITE_NOW)


class PersonRow(Base):
    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    cover_resource_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("resources.id", ondelete="SET NULL")
    )
    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=_SQLITE_NOW)
    updated_at: Mapped[str] = mapped_column(String, nullable=False, server_default=_SQLITE_NOW)


class PersonAliasRow(Base):
    __tablename__ = "person_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("persons.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String, nullable=False)


class ResourcePersonRow(Base):
    __tablename__ = "resource_persons"

    resource_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True
    )
    person_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("persons.id", ondelete="CASCADE"), primary_key=True
    )


class CharacterRow(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    work_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("works.id", ondelete="SET NULL")
    )
    description: Mapped[str | None] = mapped_column(Text)
    cover_resource_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("resources.id", ondelete="SET NULL")
    )
    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=_SQLITE_NOW)
    updated_at: Mapped[str] = mapped_column(String, nullable=False, server_default=_SQLITE_NOW)


class CharacterAliasRow(Base):
    __tablename__ = "character_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String, nullable=False)


class ResourceCharacterRow(Base):
    __tablename__ = "resource_characters"

    resource_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True
    )
    character_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True
    )


class CategoryRow(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_system: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ResourceCategoryRow(Base):
    __tablename__ = "resource_categories"

    resource_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )


class TagRow(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)


class ResourceTagRow(Base):
    __tablename__ = "resource_tags"

    resource_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )


class SeasonRow(Base):
    """作品的一季。"""

    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"))
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String)
    sort_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class EpisodeRow(Base):
    """一集，指向 files。"""

    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id", ondelete="CASCADE"))
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"))
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String)
    sort_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    cover_file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"))


class ExtraRow(Base):
    """特典文件。"""

    __tablename__ = "extras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"))
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String, nullable=False, default="")
    sort_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    cover_file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"))


class FileRow(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"))
    path: Mapped[str] = mapped_column(String, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String)
    size: Mapped[int | None] = mapped_column(Integer)
    format: Mapped[str | None] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, nullable=False, default="primary")
    duration: Mapped[float | None] = mapped_column(Float)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    codec: Mapped[str | None] = mapped_column(String)
    fps: Mapped[float | None] = mapped_column(Float)
    bitrate: Mapped[int | None] = mapped_column(Integer)
    audio_codec: Mapped[str | None] = mapped_column(String)
    audio_channels: Mapped[int | None] = mapped_column(Integer)
    audio_language: Mapped[str | None] = mapped_column(String)
    exif_taken_at: Mapped[str | None] = mapped_column(String)
    exif_lat: Mapped[float | None] = mapped_column(Float)
    exif_lng: Mapped[float | None] = mapped_column(Float)
    exif_camera: Mapped[str | None] = mapped_column(String)
    exif_lens: Mapped[str | None] = mapped_column(String)
    exif_iso: Mapped[int | None] = mapped_column(Integer)
    exif_aperture: Mapped[str | None] = mapped_column(String)
    exif_shutter: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str | None] = mapped_column(String)


class PlaybackProgressRow(Base):
    """播放进度。按 file_id 记，一个番剧作品的每一集各有一条。"""

    __tablename__ = "playback_progress"

    file_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("files.id", ondelete="CASCADE"), primary_key=True
    )
    resource_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    duration: Mapped[float | None] = mapped_column(Float)
    completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[str] = mapped_column(
        String, nullable=False, server_default=_SQLITE_NOW
    )


class ResourceTodoRow(Base):
    __tablename__ = "resource_todos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str | None] = mapped_column(String)


class ConsumptionEventRow(Base):
    __tablename__ = "consumption_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str | None] = mapped_column(String)


class CollectionRow(Base):
    __tablename__ = 'collections'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=_SQLITE_NOW)
    updated_at: Mapped[str] = mapped_column(String, nullable=False, server_default=_SQLITE_NOW)


class CollectionItemRow(Base):
    __tablename__ = 'collection_items'

    collection_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('collections.id', ondelete='CASCADE'), primary_key=True
    )
    resource_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('resources.id', ondelete='CASCADE'), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class TimelineNoteRow(Base):
    __tablename__ = "timeline_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[str | None] = mapped_column(String)
    saved_view_id: Mapped[int | None] = mapped_column(
        ForeignKey("saved_views.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body: Mapped[str | None] = mapped_column(Text)
    location_name: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=_SQLITE_NOW)
    updated_at: Mapped[str] = mapped_column(String, nullable=False, server_default=_SQLITE_NOW)


class SubtitleTrackRow(Base):
    """字幕轨：episode_id 为空表示资源级（单文件视频）。"""

    __tablename__ = "subtitle_tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"))
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"))
    episode_id: Mapped[int | None] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"))
    language: Mapped[str | None] = mapped_column(String)
    title: Mapped[str | None] = mapped_column(String)
    is_default: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sort_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=_SQLITE_NOW)


class SavedViewRow(Base):
    __tablename__ = "saved_views"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    filters_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    sort: Mapped[str] = mapped_column(String, nullable=False, default="takenAt")
    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=_SQLITE_NOW)
    updated_at: Mapped[str] = mapped_column(String, nullable=False, server_default=_SQLITE_NOW)
