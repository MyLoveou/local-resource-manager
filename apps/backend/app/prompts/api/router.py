"""提示词工作台 API。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.prompts.application import transfer
from app.prompts.application.library import library_payload
from app.prompts.infrastructure import repo
from app.shared.db.db import get_session
from app.shared.models import StrictApiModel

router = APIRouter(prefix="/prompts", tags=["prompts"])


class SaveIn(StrictApiModel):
    title: str
    model: str = "anima"
    positive: str = ""
    negative: str = ""
    note: str | None = None
    params: dict | str | None = None
    categories: list[str] | None = None
    favorite: bool = False
    resource_id: int | None = None
    image_data: str | None = None
    tags: list[str] = Field(default_factory=list)


class SavePatch(StrictApiModel):
    title: str | None = None
    model: str | None = None
    positive: str | None = None
    negative: str | None = None
    note: str | None = None
    params: dict | str | None = None
    categories: list[str] | None = None
    favorite: bool | None = None
    image_data: str | None = None
    tags: list[str] | None = None


class HistoryIn(StrictApiModel):
    model: str = "anima"
    positive: str = ""
    negative: str = ""
    save_id: int | None = None


class PinIn(StrictApiModel):
    pinned: bool = True


class CustomTagIn(StrictApiModel):
    en: str
    zh: str | None = None
    category: str = "其他"


class CustomPresetIn(StrictApiModel):
    name: str
    category: str | None = None
    tags: str = ""


@router.get("/library")
async def get_library() -> dict:
    """内置库：分类/标签/角色/预设/模板/规则。前端缓存一次即可。"""
    return library_payload()


@router.get("/saves")
async def list_saves(
    q: str | None = Query(None),
    tag: str | None = Query(None),
    favorite: bool = Query(False),
    limit: int = Query(100, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict:
    items = await repo.list_saves(session, query=q, tag=tag, favorite=favorite, limit=limit)
    return {"items": items, "total": len(items)}


@router.post("/saves", status_code=201)
async def create_save(body: SaveIn, session: AsyncSession = Depends(get_session)) -> dict:
    if not body.positive.strip():
        raise HTTPException(status_code=400, detail="正向提示词不能为空")
    save_id = await repo.create_save(session, body.model_dump(), body.tags)
    return {"id": save_id}


@router.get("/saves/{save_id}")
async def get_save(save_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    row = await repo.get_save(session, save_id)
    if row is None:
        raise HTTPException(status_code=404, detail="存档不存在")
    return row


@router.patch("/saves/{save_id}")
async def patch_save(
    save_id: int, body: SavePatch, session: AsyncSession = Depends(get_session)
) -> dict:
    ok = await repo.update_save(session, save_id, body.model_dump(exclude_none=True), body.tags)
    if not ok:
        raise HTTPException(status_code=404, detail="存档不存在")
    return {"ok": True}


@router.delete("/saves/{save_id}")
async def delete_save(save_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    if not await repo.delete_save(session, save_id):
        raise HTTPException(status_code=404, detail="存档不存在")
    return {"ok": True}


@router.post("/saves/{save_id}/copy", status_code=201)
async def copy_save(save_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    row = await repo.get_save(session, save_id)
    if row is None:
        raise HTTPException(status_code=404, detail="存档不存在")
    row.pop("id", None)
    row["title"] = f"{row['title']} 副本"
    row.pop("created_at", None)
    row.pop("updated_at", None)
    tags = list(
        (
            await session.execute(
                repo.text("SELECT tag FROM prompt_save_tags WHERE save_id = :id"),
                {"id": save_id},
            )
        ).scalars()
    )
    new_id = await repo.create_save(session, row, tags)
    return {"id": new_id}


@router.get("/history")
async def list_history(session: AsyncSession = Depends(get_session)) -> dict:
    return {"items": await repo.list_history(session)}


@router.post("/history", status_code=201)
async def add_history(body: HistoryIn, session: AsyncSession = Depends(get_session)) -> dict:
    history_id = await repo.add_history(
        session,
        model=body.model,
        positive=body.positive,
        negative=body.negative,
        save_id=body.save_id,
    )
    return {"id": history_id}


@router.post("/history/{history_id}/pin")
async def pin_history(
    history_id: int, body: PinIn, session: AsyncSession = Depends(get_session)
) -> dict:
    if not await repo.pin_history(session, history_id, body.pinned):
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"ok": True}


@router.get("/custom/tags")
async def list_custom_tags(session: AsyncSession = Depends(get_session)) -> dict:
    return {"items": await repo.list_custom(session, "prompt_custom_tags")}


@router.post("/custom/tags", status_code=201)
async def add_custom_tag(body: CustomTagIn, session: AsyncSession = Depends(get_session)) -> dict:
    item_id = await repo.add_custom(session, "prompt_custom_tags", body.model_dump())
    return {"id": item_id}


@router.delete("/custom/tags/{item_id}")
async def delete_custom_tag(item_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    if not await repo.delete_custom(session, "prompt_custom_tags", item_id):
        raise HTTPException(status_code=404, detail="标签不存在")
    return {"ok": True}


@router.get("/custom/presets")
async def list_custom_presets(session: AsyncSession = Depends(get_session)) -> dict:
    return {"items": await repo.list_custom(session, "prompt_custom_presets")}


@router.post("/custom/presets", status_code=201)
async def add_custom_preset(
    body: CustomPresetIn, session: AsyncSession = Depends(get_session)
) -> dict:
    item_id = await repo.add_custom(session, "prompt_custom_presets", body.model_dump())
    return {"id": item_id}


@router.delete("/custom/presets/{item_id}")
async def delete_custom_preset(
    item_id: int, session: AsyncSession = Depends(get_session)
) -> dict:
    if not await repo.delete_custom(session, "prompt_custom_presets", item_id):
        raise HTTPException(status_code=404, detail="预设不存在")
    return {"ok": True}


@router.get("/settings")
async def get_settings(session: AsyncSession = Depends(get_session)) -> dict:
    return await repo.get_settings(session)


@router.put("/settings")
async def put_settings(body: dict, session: AsyncSession = Depends(get_session)) -> dict:
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="需要对象")
    await repo.put_settings(session, body)
    return {"ok": True}


@router.get("/export")
async def export_saves(session: AsyncSession = Depends(get_session)) -> dict:
    """导出全部存档与自定义内容，可直接保存为 JSON 备份。"""
    return await transfer.export_all(session)


@router.post("/import")
async def import_saves(body: dict, session: AsyncSession = Depends(get_session)) -> dict:
    """导入备份或 PromptForge 的导出 JSON；按正向内容去重。"""
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="需要 JSON 对象")
    return await transfer.import_payload(session, body)
