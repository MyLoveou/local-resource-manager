"""抓取应用 · SQLAlchemy ORM 表模型。"""
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db.base import Base


class ScrapeJobRow(Base):
    __tablename__ = "scrape_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String, nullable=False, default="queued")
    started_at: Mapped[str | None] = mapped_column(String)
    finished_at: Mapped[str | None] = mapped_column(String)
    error: Mapped[str | None] = mapped_column(Text)
    match_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    query: Mapped[str | None] = mapped_column(Text)


class CandidateRow(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("scrape_jobs.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String)
    source: Mapped[str] = mapped_column(String, nullable=False)
    relevance: Mapped[float | None] = mapped_column(Float)
    selected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str | None] = mapped_column(String)

