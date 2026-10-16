"""overdue.py — weak logic + a naive/aware datetime bug."""

from datetime import UTC, datetime, timedelta

from app.models import Task, TaskStatus

NOW = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)


def _task(due: datetime | None, status: TaskStatus = TaskStatus.todo) -> Task:
    return Task(title="t", status=status, priority=3, due_at=due)


def test_done_tasks_are_not_overdue(load) -> None:
    mod = load("overdue")
    assert mod.is_overdue(_task(NOW - timedelta(days=1), TaskStatus.done), NOW) is False


def test_due_exactly_now_is_not_yet_overdue(load) -> None:
    mod = load("overdue")
    assert mod.is_overdue(_task(NOW), NOW) is False
    assert mod.is_overdue(_task(NOW - timedelta(seconds=1)), NOW) is True


def test_default_now_works_with_aware_due_dates(load) -> None:
    mod = load("overdue")
    past = datetime.now(UTC) - timedelta(days=1)
    assert mod.is_overdue(_task(past)) is True  # due_at from Postgres is timezone-aware
