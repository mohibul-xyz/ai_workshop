from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import ColumnElement, and_, not_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Tag, Task, TaskStatus
from app.schemas import TaskCreate, TaskUpdate


def get_or_create_tags(session: Session, names: Sequence[str]) -> list[Tag]:
    """Tags are global and created on first use (F05). Safe under concurrent inserts."""
    if not names:
        return []
    session.execute(
        insert(Tag)
        .values([{"name": n} for n in names])
        .on_conflict_do_nothing(index_elements=["name"])
    )
    return list(session.scalars(select(Tag).where(Tag.name.in_(names)).order_by(Tag.name)))


def create_task(session: Session, project_id: int, data: TaskCreate) -> Task:
    task = Task(project_id=project_id, **data.model_dump(exclude={"tags"}))
    task.tags = get_or_create_tags(session, data.tags)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def list_tasks(
    session: Session,
    project_id: int,
    status: TaskStatus | None = None,
    max_priority: int | None = None,
    overdue: bool | None = None,
    tag: str | None = None,
    now: datetime | None = None,
) -> Sequence[Task]:
    stmt = select(Task).where(Task.project_id == project_id)
    if status is not None:
        stmt = stmt.where(Task.status == status)
    if max_priority is not None:
        stmt = stmt.where(Task.priority <= max_priority)
    if overdue is not None:
        is_overdue = overdue_clause(now or datetime.now(UTC))
        stmt = stmt.where(is_overdue if overdue else not_(is_overdue))
    if tag is not None:
        stmt = stmt.where(Task.tags.any(Tag.name == tag))
    return session.scalars(stmt.order_by(Task.id)).all()


def overdue_clause(now: datetime) -> ColumnElement[bool]:
    """Overdue = has a due date strictly before `now` (timezone-aware) and is not done."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return and_(Task.due_at.is_not(None), Task.due_at < now, Task.status != TaskStatus.done)


def get_task(session: Session, task_id: int) -> Task | None:
    return session.get(Task, task_id)


def update_task(session: Session, task: Task, data: TaskUpdate) -> Task:
    for field, value in data.model_dump(exclude_unset=True, exclude={"tags"}).items():
        setattr(task, field, value)
    if "tags" in data.model_fields_set:  # omitted = unchanged; sent = replace (F05 AC6/AC7)
        task.tags = get_or_create_tags(session, data.tags or [])
    session.commit()
    session.refresh(task)
    return task


def delete_task(session: Session, task: Task) -> None:
    session.delete(task)
    session.commit()
