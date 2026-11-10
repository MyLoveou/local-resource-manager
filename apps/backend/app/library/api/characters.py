"""Character and work dimension API."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.application.schemas import (
    CharacterCreate,
    CharacterList,
    CharacterMergeRequest,
    CharacterPatch,
    WorkList,
)
from app.library.domain.models import Character, Collection
from app.library.infrastructure.repositories import CharacterRepository, CollectionRepository
from app.shared.db.db import get_session

router = APIRouter(prefix="/characters", tags=["library-characters"])


def _repo(session: AsyncSession = Depends(get_session)) -> CharacterRepository:
    return CharacterRepository(session)


def _collections(session: AsyncSession = Depends(get_session)) -> CollectionRepository:
    return CollectionRepository(session)


@router.get("", response_model=CharacterList)
async def list_characters(
    q: str | None = Query(default=None, max_length=200),
    work_id: int | None = Query(default=None, alias="workId"),
    repo: CharacterRepository = Depends(_repo),
) -> CharacterList:
    return CharacterList(items=await repo.list(q, work_id))


@router.get("/works", response_model=WorkList)
async def list_works(repo: CharacterRepository = Depends(_repo)) -> WorkList:
    return WorkList(items=await repo.works())


@router.get("/{character_id}", response_model=Character)
async def get_character(
    character_id: int,
    repo: CharacterRepository = Depends(_repo),
) -> Character:
    character = await repo.get(character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="character not found")
    return character


@router.get("/{character_id}/collections", response_model=list[Collection])
async def character_collections(
    character_id: int,
    repo: CharacterRepository = Depends(_repo),
    collections: CollectionRepository = Depends(_collections),
) -> list[Collection]:
    if await repo.get(character_id) is None:
        raise HTTPException(status_code=404, detail="character not found")
    return await collections.for_character(character_id)


@router.post("", response_model=Character)
async def create_character(
    body: CharacterCreate,
    repo: CharacterRepository = Depends(_repo),
) -> Character:
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="name required")
    return await repo.create(
        name,
        body.work_name,
        body.description,
        body.cover_resource_id,
        body.aliases,
    )


@router.patch("/{character_id}", response_model=Character)
async def patch_character(
    character_id: int,
    body: CharacterPatch,
    repo: CharacterRepository = Depends(_repo),
) -> Character:
    values = body.model_dump(exclude_unset=True)
    if "name" in values and not str(values["name"] or "").strip():
        raise HTTPException(status_code=422, detail="name required")
    updated = await repo.update(character_id, **values)
    if updated is None:
        raise HTTPException(status_code=404, detail="character not found")
    return updated


@router.delete("/{character_id}", status_code=204)
async def delete_character(
    character_id: int,
    repo: CharacterRepository = Depends(_repo),
) -> None:
    if not await repo.delete(character_id):
        raise HTTPException(status_code=404, detail="character not found")


@router.post("/{character_id}/merge", response_model=Character)
async def merge_character(
    character_id: int,
    body: CharacterMergeRequest,
    repo: CharacterRepository = Depends(_repo),
) -> Character:
    if character_id == body.source_id:
        raise HTTPException(status_code=422, detail="cannot merge into itself")
    merged = await repo.merge(character_id, body.source_id)
    if merged is None:
        raise HTTPException(status_code=404, detail="character not found")
    return merged
