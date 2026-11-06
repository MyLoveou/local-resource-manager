"""Cosplayer/person API."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.application.schemas import (
    PersonCreate,
    PersonList,
    PersonMergeRequest,
    PersonPatch,
)
from app.library.domain.models import CharacterBrief, Person
from app.library.infrastructure.repositories import PersonRepository
from app.shared.db.db import get_session

router = APIRouter(prefix="/persons", tags=["library-persons"])


def _repo(session: AsyncSession = Depends(get_session)) -> PersonRepository:
    return PersonRepository(session)


@router.get("", response_model=PersonList)
async def list_persons(
    q: str | None = Query(default=None, max_length=200),
    repo: PersonRepository = Depends(_repo),
) -> PersonList:
    return PersonList(items=await repo.list(q))


@router.get("/{person_id}", response_model=Person)
async def get_person(
    person_id: int,
    repo: PersonRepository = Depends(_repo),
) -> Person:
    person = await repo.get(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="person not found")
    return person


@router.get("/{person_id}/characters", response_model=list[CharacterBrief])
async def person_characters(
    person_id: int,
    repo: PersonRepository = Depends(_repo),
) -> list[CharacterBrief]:
    if await repo.get(person_id) is None:
        raise HTTPException(status_code=404, detail="person not found")
    return await repo.characters_for_person(person_id)


@router.post("", response_model=Person)
async def create_person(
    body: PersonCreate,
    repo: PersonRepository = Depends(_repo),
) -> Person:
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="name required")
    return await repo.create(name, body.description, body.cover_resource_id, body.aliases)


@router.patch("/{person_id}", response_model=Person)
async def patch_person(
    person_id: int,
    body: PersonPatch,
    repo: PersonRepository = Depends(_repo),
) -> Person:
    values = body.model_dump(exclude_unset=True)
    if "name" in values and not str(values["name"] or "").strip():
        raise HTTPException(status_code=422, detail="name required")
    updated = await repo.update(person_id, **values)
    if updated is None:
        raise HTTPException(status_code=404, detail="person not found")
    return updated


@router.delete("/{person_id}", status_code=204)
async def delete_person(
    person_id: int,
    repo: PersonRepository = Depends(_repo),
) -> None:
    if not await repo.delete(person_id):
        raise HTTPException(status_code=404, detail="person not found")


@router.post("/{person_id}/merge", response_model=Person)
async def merge_person(
    person_id: int,
    body: PersonMergeRequest,
    repo: PersonRepository = Depends(_repo),
) -> Person:
    if person_id == body.source_id:
        raise HTTPException(status_code=422, detail="cannot merge into itself")
    merged = await repo.merge(person_id, body.source_id)
    if merged is None:
        raise HTTPException(status_code=404, detail="person not found")
    return merged
