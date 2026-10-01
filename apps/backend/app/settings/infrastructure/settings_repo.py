"""设置应用 · settings KV 仓储。"""

from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.settings.infrastructure.orm import SettingsRow


class SettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_json(self, key: str) -> dict:
        row = await self._session.get(SettingsRow, key)
        if row is None or not row.value:
            return {}
        try:
            data = json.loads(row.value)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    async def put_json(self, key: str, value: dict) -> None:
        raw = json.dumps(value, ensure_ascii=False)
        row = await self._session.get(SettingsRow, key)
        if row is None:
            self._session.add(SettingsRow(key=key, value=raw))
        else:
            row.value = raw
        await self._session.commit()
