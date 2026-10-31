"""设置应用 · SQLAlchemy ORM 表模型。"""
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db.base import Base


class SettingsRow(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
