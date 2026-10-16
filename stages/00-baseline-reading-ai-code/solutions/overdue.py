"""Overdue-task helpers — reference fix.

Fixes: done tasks are never overdue; strict `<` (due exactly now is not late yet);
timezone-aware `now` (Postgres timestamptz values are aware; utcnow() is naive).
"""

from collections.abc import Iterable
from datetime import UTC, datetime

from app.models import Task, TaskStatus


def is_overdue(task: Task, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    return task.due_at is not None and task.status != TaskStatus.done and task.due_at < now


def overdue_tasks(tasks: Iterable[Task], now: datetime | None = None) -> list[Task]:
    now = now or datetime.now(UTC)
    return [task for task in tasks if is_overdue(task, now)]


def count_overdue(tasks: Iterable[Task], now: datetime | None = None) -> int:
    return len(overdue_tasks(tasks, now))
