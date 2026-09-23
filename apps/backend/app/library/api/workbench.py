"""工作目录与消费记录。"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.application.workbench import add_work_directory, add_work_note, delete_work_note, record_consumption
from app.shared.db.db import get_session
from app.shared.models import ApiModel, Resource

router = APIRouter(tags=["library-workbench"])


class WorkDirectoryCreate(ApiModel):
    path: str = Field(min_length=1)


class WorkNoteCreate(ApiModel):
    title: str = ""
    content: str = ""


class ConsumptionCreate(ApiModel):
    resource_id: int
    action: str = "open"


@router.post("/work-directories", response_model=Resource, status_code=201)
async def create_work_directory(
    body: WorkDirectoryCreate,
    session: AsyncSession = Depends(get_session),
) -> Resource:
    try:
        return await add_work_directory(session, body.path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/resources/{resource_id}/notes", response_model=Resource)
async def create_note(
    resource_id: int,
    body: WorkNoteCreate,
    session: AsyncSession = Depends(get_session),
) -> Resource:
    if not body.content.strip() and not body.title.strip():
        raise HTTPException(status_code=400, detail="empty note")
    resource = await add_work_note(session, resource_id, body.title, body.content)
    if resource is None:
        raise HTTPException(status_code=404, detail="resource not found")
    return resource


@router.delete("/resources/{resource_id}/notes/{note_id}", response_model=Resource)
async def remove_note(
    resource_id: int,
    note_id: str,
    session: AsyncSession = Depends(get_session),
) -> Resource:
    resource = await delete_work_note(session, resource_id, note_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="resource not found")
    return resource


@router.post("/consumptions")
async def create_consumption(
    body: ConsumptionCreate,
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    try:
        await record_consumption(session, body.resource_id, body.action or "open")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}
