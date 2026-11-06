"""Person and character aggregate repositories."""

from __future__ import annotations

from sqlalchemy import and_, delete, desc, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.domain.media_types import FILE_ROLE_THUMBNAIL
from app.library.domain.models import (
    Character,
    CharacterBrief,
    Person,
    ResourceStatus,
    Work,
)
from app.library.infrastructure.media_paths import file_content_url as _file_content_url
from app.library.infrastructure.orm import (
    CharacterAliasRow,
    CharacterRow,
    FileRow,
    PersonAliasRow,
    PersonRow,
    ResourceCharacterRow,
    ResourcePersonRow,
    ResourceRow,
    WorkRow,
)
from app.shared.utils.time import db_now


class PersonRepository:
    """Cosplayer/person dimension with aliases and resource links."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def list(self, query: str | None = None, person_id: int | None = None) -> list[Person]:
        stmt = select(PersonRow).order_by(PersonRow.name)
        if person_id is not None:
            stmt = stmt.where(PersonRow.id == person_id)
        clean = (query or "").strip()
        if clean:
            like = f"%{clean}%"
            alias_match = exists(
                select(PersonAliasRow.id).where(
                    PersonAliasRow.person_id == PersonRow.id,
                    PersonAliasRow.alias.ilike(like),
                )
            )
            stmt = stmt.where(or_(PersonRow.name.ilike(like), alias_match))
        rows = (await self._session.execute(stmt)).scalars().all()
        return await self._hydrate(rows)

    async def get(self, person_id: int) -> Person | None:
        items = await self.list(person_id=person_id)
        return items[0] if items else None

    async def _hydrate(self, rows: list[PersonRow]) -> list[Person]:
        if not rows:
            return []
        ids = [row.id for row in rows]
        aliases: dict[int, list[str]] = {}
        for person_id, alias in (await self._session.execute(
            select(PersonAliasRow.person_id, PersonAliasRow.alias)
            .where(PersonAliasRow.person_id.in_(ids))
            .order_by(PersonAliasRow.alias)
        )).all():
            aliases.setdefault(int(person_id), []).append(alias)
        counts = {
            int(person_id): int(count)
            for person_id, count in (await self._session.execute(
                select(ResourcePersonRow.person_id, func.count())
                .join(ResourceRow, ResourceRow.id == ResourcePersonRow.resource_id)
                .where(
                    ResourcePersonRow.person_id.in_(ids),
                    ResourceRow.status == ResourceStatus.ACTIVE.value,
                )
                .group_by(ResourcePersonRow.person_id)
            )).all()
        }
        cover_ids = {row.cover_resource_id for row in rows if row.cover_resource_id is not None}
        explicit_thumbs: dict[int, int] = {}
        if cover_ids:
            for resource_id, file_id in (await self._session.execute(
                select(FileRow.resource_id, FileRow.id).where(
                    FileRow.resource_id.in_(cover_ids),
                    FileRow.role == FILE_ROLE_THUMBNAIL,
                )
            )).all():
                explicit_thumbs[int(resource_id)] = int(file_id)
        latest: dict[int, tuple[int, int]] = {}
        for person_id, resource_id, file_id in (await self._session.execute(
            select(ResourcePersonRow.person_id, ResourceRow.id, FileRow.id)
            .join(ResourceRow, ResourceRow.id == ResourcePersonRow.resource_id)
            .join(FileRow, and_(
                FileRow.resource_id == ResourceRow.id,
                FileRow.role == FILE_ROLE_THUMBNAIL,
            ))
            .where(
                ResourcePersonRow.person_id.in_(ids),
                ResourceRow.status == ResourceStatus.ACTIVE.value,
            )
            .order_by(ResourcePersonRow.person_id, desc(ResourceRow.created_at))
        )).all():
            latest.setdefault(int(person_id), (int(resource_id), int(file_id)))
        result: list[Person] = []
        for row in rows:
            cover = None
            if row.cover_resource_id is not None and row.cover_resource_id in explicit_thumbs:
                cover = _file_content_url(row.cover_resource_id, explicit_thumbs[row.cover_resource_id])
            elif row.id in latest:
                resource_id, file_id = latest[row.id]
                cover = _file_content_url(resource_id, file_id)
            result.append(
                Person(
                    id=row.id,
                    name=row.name,
                    description=row.description,
                    cover_resource_id=row.cover_resource_id,
                    cover_path=cover,
                    aliases=aliases.get(row.id, []),
                    resource_count=counts.get(row.id, 0),
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
            )
        return result

    async def create(
        self,
        name: str,
        description: str | None,
        cover_resource_id: int | None,
        aliases: list[str],
    ) -> Person:
        row = PersonRow(name=name.strip(), description=description, cover_resource_id=cover_resource_id)
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        await self._replace_aliases(row.id, aliases)
        created = await self.get(row.id)
        assert created is not None
        return created

    async def update(self, person_id: int, **values) -> Person | None:
        row = await self._session.get(PersonRow, person_id)
        if row is None:
            return None
        if "name" in values and values["name"] is not None:
            row.name = str(values["name"]).strip()
        if "description" in values:
            row.description = values["description"]
        if "cover_resource_id" in values:
            row.cover_resource_id = values["cover_resource_id"]
        row.updated_at = db_now()
        await self._session.commit()
        if "aliases" in values and values["aliases"] is not None:
            await self._replace_aliases(person_id, values["aliases"])
        return await self.get(person_id)

    async def _replace_aliases(
        self, person_id: int, aliases: list[str], *, commit: bool = True
    ) -> None:
        await self._session.execute(delete(PersonAliasRow).where(PersonAliasRow.person_id == person_id))
        seen: set[str] = set()
        for raw in aliases:
            alias = str(raw).strip()
            key = alias.lower()
            if not alias or key in seen:
                continue
            seen.add(key)
            self._session.add(PersonAliasRow(person_id=person_id, alias=alias))
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()

    async def delete(self, person_id: int) -> bool:
        row = await self._session.get(PersonRow, person_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    async def merge(self, target_id: int, source_id: int) -> Person | None:
        if target_id == source_id:
            return await self.get(target_id)
        target = await self._session.get(PersonRow, target_id)
        source = await self._session.get(PersonRow, source_id)
        if target is None or source is None:
            return None
        target_links = set((await self._session.scalars(
            select(ResourcePersonRow.resource_id).where(ResourcePersonRow.person_id == target_id)
        )).all())
        source_links = (await self._session.scalars(
            select(ResourcePersonRow.resource_id).where(ResourcePersonRow.person_id == source_id)
        )).all()
        for resource_id in source_links:
            if int(resource_id) not in target_links:
                self._session.add(ResourcePersonRow(resource_id=int(resource_id), person_id=target_id))
        source_aliases = (await self._session.scalars(
            select(PersonAliasRow.alias).where(PersonAliasRow.person_id == source_id)
        )).all()
        target_aliases = list((await self._session.scalars(
            select(PersonAliasRow.alias).where(PersonAliasRow.person_id == target_id).order_by(PersonAliasRow.alias)
        )).all())
        aliases = target_aliases
        for alias in [*source_aliases, source.name]:
            if alias and alias.lower() not in {item.lower() for item in aliases}:
                aliases.append(alias)
        if target.cover_resource_id is None:
            target.cover_resource_id = source.cover_resource_id
        await self._session.delete(source)
        await self._replace_aliases(target_id, aliases, commit=False)
        await self._session.commit()
        return await self.get(target_id)

    async def set_resources(
        self, resource_id: int, person_ids: list[int], *, commit: bool = True
    ) -> None:
        await self._session.execute(
            delete(ResourcePersonRow).where(ResourcePersonRow.resource_id == resource_id)
        )
        for person_id in dict.fromkeys(person_ids):
            self._session.add(ResourcePersonRow(resource_id=resource_id, person_id=person_id))
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()

    async def add_resources(self, resource_ids: list[int], person_ids: list[int]) -> int:
        added = 0
        existing = set((await self._session.execute(
            select(ResourcePersonRow.resource_id, ResourcePersonRow.person_id).where(
                ResourcePersonRow.resource_id.in_(resource_ids),
                ResourcePersonRow.person_id.in_(person_ids),
            )
        )).all())
        for resource_id in resource_ids:
            for person_id in person_ids:
                if (resource_id, person_id) in existing:
                    continue
                self._session.add(ResourcePersonRow(resource_id=resource_id, person_id=person_id))
                added += 1
        await self._session.commit()
        return added

    async def remove_resources(self, resource_ids: list[int], person_ids: list[int]) -> int:
        result = await self._session.execute(
            delete(ResourcePersonRow).where(
                ResourcePersonRow.resource_id.in_(resource_ids),
                ResourcePersonRow.person_id.in_(person_ids),
            )
        )
        await self._session.commit()
        return int(result.rowcount or 0)

    async def characters_for_person(self, person_id: int) -> list[CharacterBrief]:
        rows = (await self._session.execute(
            select(CharacterRow, WorkRow.name)
            .join(ResourceCharacterRow, ResourceCharacterRow.character_id == CharacterRow.id)
            .join(ResourcePersonRow, ResourcePersonRow.resource_id == ResourceCharacterRow.resource_id)
            .outerjoin(WorkRow, WorkRow.id == CharacterRow.work_id)
            .where(ResourcePersonRow.person_id == person_id)
            .distinct()
            .order_by(CharacterRow.name)
        )).all()
        return [
            CharacterBrief(
                id=row[0].id,
                name=row[0].name,
                work_id=row[0].work_id,
                work_name=row[1],
            )
            for row in rows
        ]

class CharacterRepository:
    """Character/work dimension with aliases and resource links."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def works(self) -> list[Work]:
        rows = (await self._session.execute(select(WorkRow).order_by(WorkRow.name))).scalars().all()
        return [
            Work(
                id=row.id,
                name=row.name,
                description=row.description,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    async def work_by_name(self, name: str) -> Work | None:
        clean = name.strip()
        if not clean:
            return None
        row = (await self._session.execute(
            select(WorkRow).where(func.lower(WorkRow.name) == clean.lower()).limit(1)
        )).scalars().first()
        if row is None:
            return None
        return Work(
            id=row.id,
            name=row.name,
            description=row.description,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def work_get_or_create(self, name: str | None) -> Work | None:
        clean = (name or "").strip()
        if not clean:
            return None
        existing = await self.work_by_name(clean)
        if existing is not None:
            return existing
        row = WorkRow(name=clean)
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return Work(id=row.id, name=row.name, description=row.description,
                    created_at=row.created_at, updated_at=row.updated_at)

    async def list(
        self,
        query: str | None = None,
        work_id: int | None = None,
        character_id: int | None = None,
    ) -> list[Character]:
        stmt = (
            select(CharacterRow, WorkRow.name)
            .outerjoin(WorkRow, WorkRow.id == CharacterRow.work_id)
            .order_by(CharacterRow.name)
        )
        if character_id is not None:
            stmt = stmt.where(CharacterRow.id == character_id)
        if work_id is not None:
            stmt = stmt.where(CharacterRow.work_id == work_id)
        clean = (query or "").strip()
        if clean:
            like = f"%{clean}%"
            alias_match = exists(
                select(CharacterAliasRow.id).where(
                    CharacterAliasRow.character_id == CharacterRow.id,
                    CharacterAliasRow.alias.ilike(like),
                )
            )
            stmt = stmt.where(or_(CharacterRow.name.ilike(like), alias_match))
        rows = (await self._session.execute(stmt)).all()
        return await self._hydrate(rows)

    async def get(self, character_id: int) -> Character | None:
        items = await self.list(character_id=character_id)
        return items[0] if items else None

    async def _hydrate(self, rows: list[tuple[CharacterRow, str | None]]) -> list[Character]:
        if not rows:
            return []
        ids = [row.id for row, _work in rows]
        aliases: dict[int, list[str]] = {}
        for character_id, alias in (await self._session.execute(
            select(CharacterAliasRow.character_id, CharacterAliasRow.alias)
            .where(CharacterAliasRow.character_id.in_(ids))
            .order_by(CharacterAliasRow.alias)
        )).all():
            aliases.setdefault(int(character_id), []).append(alias)
        counts = {
            int(character_id): int(count)
            for character_id, count in (await self._session.execute(
                select(ResourceCharacterRow.character_id, func.count())
                .join(ResourceRow, ResourceRow.id == ResourceCharacterRow.resource_id)
                .where(
                    ResourceCharacterRow.character_id.in_(ids),
                    ResourceRow.status == ResourceStatus.ACTIVE.value,
                )
                .group_by(ResourceCharacterRow.character_id)
            )).all()
        }
        cover_ids = {row.cover_resource_id for row, _work in rows if row.cover_resource_id is not None}
        explicit_thumbs: dict[int, int] = {}
        if cover_ids:
            for resource_id, file_id in (await self._session.execute(
                select(FileRow.resource_id, FileRow.id).where(
                    FileRow.resource_id.in_(cover_ids),
                    FileRow.role == FILE_ROLE_THUMBNAIL,
                )
            )).all():
                explicit_thumbs[int(resource_id)] = int(file_id)
        latest: dict[int, tuple[int, int]] = {}
        for character_id, resource_id, file_id in (await self._session.execute(
            select(ResourceCharacterRow.character_id, ResourceRow.id, FileRow.id)
            .join(ResourceRow, ResourceRow.id == ResourceCharacterRow.resource_id)
            .join(FileRow, and_(
                FileRow.resource_id == ResourceRow.id,
                FileRow.role == FILE_ROLE_THUMBNAIL,
            ))
            .where(
                ResourceCharacterRow.character_id.in_(ids),
                ResourceRow.status == ResourceStatus.ACTIVE.value,
            )
            .order_by(ResourceCharacterRow.character_id, desc(ResourceRow.created_at))
        )).all():
            latest.setdefault(int(character_id), (int(resource_id), int(file_id)))
        result: list[Character] = []
        for row, work_name in rows:
            cover = None
            if row.cover_resource_id is not None and row.cover_resource_id in explicit_thumbs:
                cover = _file_content_url(row.cover_resource_id, explicit_thumbs[row.cover_resource_id])
            elif row.id in latest:
                resource_id, file_id = latest[row.id]
                cover = _file_content_url(resource_id, file_id)
            result.append(
                Character(
                    id=row.id,
                    name=row.name,
                    work_id=row.work_id,
                    work_name=work_name,
                    description=row.description,
                    cover_resource_id=row.cover_resource_id,
                    cover_path=cover,
                    aliases=aliases.get(row.id, []),
                    resource_count=counts.get(row.id, 0),
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
            )
        return result

    async def create(
        self,
        name: str,
        work_name: str | None,
        description: str | None,
        cover_resource_id: int | None,
        aliases: list[str],
    ) -> Character:
        work = await self.work_get_or_create(work_name)
        row = CharacterRow(
            name=name.strip(),
            work_id=work.id if work else None,
            description=description,
            cover_resource_id=cover_resource_id,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        await self._replace_aliases(row.id, aliases)
        created = await self.get(row.id)
        assert created is not None
        return created

    async def update(self, character_id: int, **values) -> Character | None:
        row = await self._session.get(CharacterRow, character_id)
        if row is None:
            return None
        if "name" in values and values["name"] is not None:
            row.name = str(values["name"]).strip()
        if "work_name" in values:
            work = await self.work_get_or_create(values["work_name"])
            row.work_id = work.id if work else None
        if "description" in values:
            row.description = values["description"]
        if "cover_resource_id" in values:
            row.cover_resource_id = values["cover_resource_id"]
        row.updated_at = db_now()
        await self._session.commit()
        if "aliases" in values and values["aliases"] is not None:
            await self._replace_aliases(character_id, values["aliases"])
        return await self.get(character_id)

    async def _replace_aliases(
        self, character_id: int, aliases: list[str], *, commit: bool = True
    ) -> None:
        await self._session.execute(delete(CharacterAliasRow).where(CharacterAliasRow.character_id == character_id))
        seen: set[str] = set()
        for raw in aliases:
            alias = str(raw).strip()
            key = alias.lower()
            if not alias or key in seen:
                continue
            seen.add(key)
            self._session.add(CharacterAliasRow(character_id=character_id, alias=alias))
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()

    async def delete(self, character_id: int) -> bool:
        row = await self._session.get(CharacterRow, character_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    async def merge(self, target_id: int, source_id: int) -> Character | None:
        if target_id == source_id:
            return await self.get(target_id)
        target = await self._session.get(CharacterRow, target_id)
        source = await self._session.get(CharacterRow, source_id)
        if target is None or source is None:
            return None
        target_links = set((await self._session.scalars(
            select(ResourceCharacterRow.resource_id).where(ResourceCharacterRow.character_id == target_id)
        )).all())
        source_links = (await self._session.scalars(
            select(ResourceCharacterRow.resource_id).where(ResourceCharacterRow.character_id == source_id)
        )).all()
        for resource_id in source_links:
            if int(resource_id) not in target_links:
                self._session.add(ResourceCharacterRow(resource_id=int(resource_id), character_id=target_id))
        source_aliases = (await self._session.scalars(
            select(CharacterAliasRow.alias).where(CharacterAliasRow.character_id == source_id)
        )).all()
        target_aliases = list((await self._session.scalars(
            select(CharacterAliasRow.alias).where(CharacterAliasRow.character_id == target_id).order_by(CharacterAliasRow.alias)
        )).all())
        aliases = target_aliases
        for alias in [*source_aliases, source.name]:
            if alias and alias.lower() not in {item.lower() for item in aliases}:
                aliases.append(alias)
        if target.work_id is None:
            target.work_id = source.work_id
        if target.cover_resource_id is None:
            target.cover_resource_id = source.cover_resource_id
        await self._session.delete(source)
        await self._replace_aliases(target_id, aliases, commit=False)
        await self._session.commit()
        return await self.get(target_id)

    async def set_resources(
        self, resource_id: int, character_ids: list[int], *, commit: bool = True
    ) -> None:
        await self._session.execute(
            delete(ResourceCharacterRow).where(ResourceCharacterRow.resource_id == resource_id)
        )
        for character_id in dict.fromkeys(character_ids):
            self._session.add(ResourceCharacterRow(resource_id=resource_id, character_id=character_id))
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()

    async def add_resources(self, resource_ids: list[int], character_ids: list[int]) -> int:
        added = 0
        existing = set((await self._session.execute(
            select(ResourceCharacterRow.resource_id, ResourceCharacterRow.character_id).where(
                ResourceCharacterRow.resource_id.in_(resource_ids),
                ResourceCharacterRow.character_id.in_(character_ids),
            )
        )).all())
        for resource_id in resource_ids:
            for character_id in character_ids:
                key = (resource_id, character_id)
                if key in existing:
                    continue
                self._session.add(ResourceCharacterRow(resource_id=resource_id, character_id=character_id))
                added += 1
        await self._session.commit()
        return added

    async def remove_resources(self, resource_ids: list[int], character_ids: list[int]) -> int:
        result = await self._session.execute(
            delete(ResourceCharacterRow).where(
                ResourceCharacterRow.resource_id.in_(resource_ids),
                ResourceCharacterRow.character_id.in_(character_ids),
            )
        )
        await self._session.commit()
        return int(result.rowcount or 0)
