"""工作台：消费渠道默认、工作目录登记、备注、消费审计。"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.infrastructure.repositories import ResourceRepository
from app.shared.db.orm import ConsumptionEventRow, FileRow, ResourceRow, ResourceTodoRow
from app.shared.infrastructure.settings_repo import KEY_CONSUME, SettingsRepository
from app.shared.media_types import FILE_ROLE_PRIMARY
from app.shared.models import Resource, ResourceStatus, ResourceType, StorageKind

ChannelMode = str
MODES = ("embedded", "system", "command", "workbench")
WORK_MODES = ("workbench", "system", "command")

DEFAULT_MODE: dict[str, str] = {
    "image": "embedded",
    "video": "embedded",
    "anime": "embedded",
    "av": "embedded",
    "audio": "embedded",
    "model": "embedded",
    "novel": "system",
    "comic": "system",
    "game": "system",
    "work_directory": "workbench",
}


def normalize_channels(raw: dict | None) -> dict[str, dict[str, str]]:
    """缺省补默认；非法 mode 回退。工作目录不能选内嵌预览。"""
    source = raw if isinstance(raw, dict) else {}
    out: dict[str, dict[str, str]] = {}
    for type_name, default in DEFAULT_MODE.items():
        item = source.get(type_name)
        mode = item.get("mode") if isinstance(item, dict) else None
        allowed = WORK_MODES if type_name == "work_directory" else ("embedded", "system", "command")
        if mode not in allowed:
            mode = default
        command = ""
        if isinstance(item, dict) and isinstance(item.get("command"), str):
            command = item["command"].strip()
        out[type_name] = {"mode": mode, "command": command}
    return out


async def load_channels(session: AsyncSession) -> dict[str, dict[str, str]]:
    raw = await SettingsRepository(session).get_json(KEY_CONSUME)
    stored = raw.get("channels") if isinstance(raw.get("channels"), dict) else raw
    return normalize_channels(stored if isinstance(stored, dict) else {})


async def save_channels(session: AsyncSession, channels: dict) -> dict[str, dict[str, str]]:
    normalized = normalize_channels(channels)
    await SettingsRepository(session).put_json(KEY_CONSUME, {"channels": normalized})
    return normalized


async def add_work_directory(session: AsyncSession, raw_path: str) -> Resource:
    folder = Path(raw_path)
    if not folder.is_dir():
        raise ValueError("path is not a directory")
    resolved = str(folder.resolve())
    repo = ResourceRepository(session)
    existing = await _work_directory_at(session, resolved)
    if existing is not None and existing.id is not None:
        if existing.status == ResourceStatus.ACTIVE:
            raise ValueError("directory already added")
        if existing.is_trashed:
            existing.restore()
        elif existing.is_lost:
            existing.status = ResourceStatus.ACTIVE
            existing._touch()
        else:
            raise ValueError("directory already added")
        updated = await repo.update(existing.id, existing)
        assert updated is not None
        return updated
    created = await repo.create(
        Resource(
            type=ResourceType.WORK_DIRECTORY,
            storage_kind=StorageKind.INDEXED,
            title=folder.name or resolved,
            status=ResourceStatus.ACTIVE,
            extra={"importSourcePath": resolved},
        ),
        commit=False,
    )
    assert created.id is not None
    await repo.add_file(
        created.id,
        path=resolved,
        sha256=None,
        size=None,
        format_=None,
        role=FILE_ROLE_PRIMARY,
        commit=True,
    )
    got = await repo.get(created.id)
    assert got is not None
    return got


async def _work_directory_at(session: AsyncSession, resolved: str) -> Resource | None:
    stmt = (
        select(ResourceRow.id)
        .join(FileRow, FileRow.resource_id == ResourceRow.id)
        .where(
            FileRow.path == resolved,
            FileRow.role == FILE_ROLE_PRIMARY,
            ResourceRow.type == ResourceType.WORK_DIRECTORY.value,
        )
        .limit(1)
    )
    resource_id = await session.scalar(stmt)
    if resource_id is None:
        return None
    return await ResourceRepository(session).get(int(resource_id))


def _notes(resource: Resource) -> list[dict]:
    raw = resource.extra.get("workNotes")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict) and isinstance(item.get("id"), str)]


async def add_work_note(session: AsyncSession, resource_id: int, title: str, content: str) -> Resource | None:
    repo = ResourceRepository(session)
    resource = await repo.get(resource_id)
    if resource is None or resource.type != ResourceType.WORK_DIRECTORY or resource.id is None:
        return None
    notes = _notes(resource)
    notes.append(
        {
            "id": uuid.uuid4().hex[:12],
            "title": title.strip(),
            "content": content.strip(),
        }
    )
    resource.extra["workNotes"] = notes
    resource._touch()
    return await repo.update(resource.id, resource)


async def delete_work_note(session: AsyncSession, resource_id: int, note_id: str) -> Resource | None:
    repo = ResourceRepository(session)
    resource = await repo.get(resource_id)
    if resource is None or resource.type != ResourceType.WORK_DIRECTORY or resource.id is None:
        return None
    resource.extra["workNotes"] = [item for item in _notes(resource) if item.get("id") != note_id]
    resource._touch()
    return await repo.update(resource.id, resource)


async def record_consumption(session: AsyncSession, resource_id: int, action: str) -> None:
    repo = ResourceRepository(session)
    if await repo.get(resource_id) is None:
        raise ValueError("resource not found")
    session.add(
        ConsumptionEventRow(
            resource_id=resource_id,
            action=action[:32],
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
    )
    await session.commit()


async def active_work(session: AsyncSession, limit: int = 10) -> list[Resource]:
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    open_ids = select(ResourceTodoRow.resource_id).where(ResourceTodoRow.done == 0)
    recent_open = select(ConsumptionEventRow.resource_id).where(ConsumptionEventRow.created_at >= cutoff)
    stmt = (
        select(ResourceRow)
        .where(
            ResourceRow.type == ResourceType.WORK_DIRECTORY.value,
            ResourceRow.status == ResourceStatus.ACTIVE.value,
            or_(
                ResourceRow.id.in_(open_ids),
                ResourceRow.updated_at >= cutoff,
                ResourceRow.id.in_(recent_open),
            ),
        )
        .order_by(ResourceRow.updated_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    repo = ResourceRepository(session)
    return await repo.attach_listed([_row(row) for row in rows])


def _row(row: ResourceRow) -> Resource:
    from app.library.infrastructure.repositories import orm_to_resource

    return orm_to_resource(row)


async def recent_consumption(session: AsyncSession, limit: int = 10) -> list[dict]:
    stmt = (
        select(ConsumptionEventRow, ResourceRow)
        .join(ResourceRow, ResourceRow.id == ConsumptionEventRow.resource_id)
        .order_by(ConsumptionEventRow.id.desc())
        .limit(limit)
    )
    found = (await session.execute(stmt)).all()
    return [
        {
            "id": event.id,
            "resource_id": event.resource_id,
            "title": resource.title,
            "type": resource.type,
            "action": event.action,
            "created_at": event.created_at,
        }
        for event, resource in found
    ]
