"""Task search — reference fix: bound parameters via the ORM, LIKE wildcards escaped."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Task


def search_tasks(session: Session, project_id: int, q: str) -> list[dict[str, Any]]:
    stmt = (
        select(Task.id, Task.title)
        .where(Task.project_id == project_id)
        .where(func.lower(Task.title).contains(q.lower(), autoescape=True))
        .order_by(Task.id)
    )
    return [dict(row._mapping) for row in session.execute(stmt)]
