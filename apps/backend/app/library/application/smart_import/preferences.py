"""智能导入的开关：是否允许调用 AI 清洗标题。

存在 `ai_preferences`（键值表）里，默认关闭——本地优先，AI 是可选增强。
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

KEY = "smart_import_ai"
# 默认开启：规则只能覆盖已知模式，标题清洗以模型为主，模型不可用时自动降级
DEFAULT_ENABLED = True


async def is_ai_enabled(session: AsyncSession) -> bool:
    row = (
        await session.execute(
            text("SELECT value FROM ai_preferences WHERE key = :key"), {"key": KEY}
        )
    ).first()
    if not row:
        return DEFAULT_ENABLED
    return str(row[0]).strip() in {"1", "true", "on", "yes"}


async def set_ai_enabled(session: AsyncSession, enabled: bool) -> None:
    await session.execute(
        text(
            "INSERT INTO ai_preferences (key, value, updated_at) "
            "VALUES (:key, :value, datetime('now')) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
            "updated_at = excluded.updated_at"
        ),
        {"key": KEY, "value": "1" if enabled else "0"},
    )
    await session.commit()
