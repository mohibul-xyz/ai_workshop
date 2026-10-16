import re
from datetime import datetime
from typing import Annotated, Any

from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from app.models import TaskStatus

MAX_TAGS = 10
TAG_PATTERN = re.compile(r"^[a-z0-9-]{1,32}$")


def normalise_tag(value: Any) -> Any:
    return value.strip().lower() if isinstance(value, str) else value


# F05: tags are trimmed + lowercased, then must be 1-32 chars of a-z, 0-9, "-".
TagName = Annotated[
    str,
    BeforeValidator(normalise_tag),
    StringConstraints(min_length=1, max_length=32, pattern=TAG_PATTERN.pattern),
]


def _dedupe_tags(tags: list[str] | None) -> list[str] | None:
    if tags is None:
        return None
    unique = sorted(set(tags))
    if len(unique) > MAX_TAGS:
        raise ValueError(f"at most {MAX_TAGS} tags per task")
    return unique


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus = TaskStatus.todo
    priority: int = Field(default=3, ge=1, le=5)
    due_at: AwareDatetime | None = None
    tags: list[TagName] = Field(default_factory=list)

    _tags = field_validator("tags")(_dedupe_tags)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    due_at: AwareDatetime | None = None
    tags: list[TagName] | None = None

    _tags = field_validator("tags")(_dedupe_tags)


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: int
    due_at: datetime | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    @field_validator("tags", mode="before")
    @classmethod
    def _tag_names(cls, value: Any) -> list[str]:
        return sorted(t if isinstance(t, str) else t.name for t in value or [])


class Page[ItemT](BaseModel):
    """F06 list envelope: {"items": [...], "total": N, "limit": L, "offset": O}."""

    items: list[ItemT]
    total: int
    limit: int
    offset: int
