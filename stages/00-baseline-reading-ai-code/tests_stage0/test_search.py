"""search.py — SQL built with an f-string inside text() → injection."""

from sqlalchemy.orm import Session

from app.models import Project, Task


def _seed(session: Session) -> tuple[int, int]:
    mine, theirs = Project(name="mine"), Project(name="theirs")
    session.add_all([mine, theirs])
    session.flush()
    session.add_all(
        [
            Task(project_id=mine.id, title="O'Brien report", priority=3),
            Task(project_id=mine.id, title="release notes", priority=3),
            Task(project_id=theirs.id, title="secret plans", priority=3),
        ]
    )
    session.commit()
    return mine.id, theirs.id


def test_search_finds_substring(load, sqlite_session: Session) -> None:
    mod = load("search")
    mine, _ = _seed(sqlite_session)
    assert [r["title"] for r in mod.search_tasks(sqlite_session, mine, "RELEASE")] == [
        "release notes"
    ]


def test_quotes_in_query_are_data_not_sql(load, sqlite_session: Session) -> None:
    mod = load("search")
    mine, _ = _seed(sqlite_session)
    assert [r["title"] for r in mod.search_tasks(sqlite_session, mine, "o'brien")] == [
        "O'Brien report"
    ]


def test_cannot_read_other_projects_via_injection(load, sqlite_session: Session) -> None:
    mod = load("search")
    mine, _ = _seed(sqlite_session)
    payload = "') OR 1=1 OR lower(title) LIKE ('"
    titles = [r["title"] for r in mod.search_tasks(sqlite_session, mine, payload)]
    assert "secret plans" not in titles
