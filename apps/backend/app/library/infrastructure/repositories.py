"""Repository facade.

Import concrete repositories from their own modules; this module keeps the
existing public import path stable for API and application layers.
"""

from app.library.infrastructure.repositories_collections import CollectionRepository
from app.library.infrastructure.repositories_common import orm_to_resource
from app.library.infrastructure.repositories_people import (
    CharacterRepository,
    PersonRepository,
)
from app.library.infrastructure.repositories_resources import ResourceRepository
from app.library.infrastructure.repositories_views import (
    CategoryRepository,
    SavedViewRepository,
    TaskSummaryRepository,
    TimelineNoteRepository,
)

__all__ = [
    "CategoryRepository",
    "CharacterRepository",
    "CollectionRepository",
    "PersonRepository",
    "ResourceRepository",
    "SavedViewRepository",
    "TaskSummaryRepository",
    "TimelineNoteRepository",
    "orm_to_resource",
]
