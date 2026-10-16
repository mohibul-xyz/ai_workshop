from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import ColumnElement, and_, not_, select
from sqlalchemy.orm import Session

from app.models import Task, TaskStatus
from app.schemas import TaskCreate, TaskUpdate


def create_task(session: Session, project_id: int, data: TaskCreate) -> Task:
    task = Task(project_id=project_id, **data.model_dump())
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
    return session.scalars(stmt.order_by(Task.id)).all()


def overdue_clause(now: datetime) -> ColumnElement[bool]:
    """Overdue = has a due date strictly before `now` (timezone-aware) and is not done."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return and_(Task.due_at.is_not(None), Task.due_at < now, Task.status != TaskStatus.done)


def get_task(session: Session, task_id: int) -> Task | None:
    return session.get(Task, task_id)


def update_task(session: Session, task: Task, data: TaskUpdate) -> Task:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    session.commit()
    session.refresh(task)
    return task


def delete_task(session: Session, task: Task) -> None:
    session.delete(task)
    session.commit()
