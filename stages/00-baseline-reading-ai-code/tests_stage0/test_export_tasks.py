"""export_tasks.py — invented APIs + a Pydantic v1 call."""

import warnings

from sqlalchemy.orm import Session

from app.models import Project, Task


def _seed(session: Session, n: int) -> int:
    project = Project(name="p")
    session.add(project)
    session.flush()
    session.add_all(Task(project_id=project.id, title=f"t{i}", priority=3) for i in range(n))
    session.commit()
    return project.id


def test_module_imports(load) -> None:  # invented API: fastapi.responses.CSVResponse
    load("export_tasks")


def test_paginates_with_sqlalchemy_2(load, sqlite_session: Session) -> None:  # .paginate()
    mod = load("export_tasks")
    pid = _seed(sqlite_session, 5)
    body = mod.export_tasks_csv(sqlite_session, pid, page=2, per_page=2).body.decode()
    rows = body.strip().splitlines()
    assert rows[0].startswith("id,title")
    assert [r.split(",")[1] for r in rows[1:]] == ["t2", "t3"]


def test_uses_pydantic_v2_api(load, sqlite_session: Session) -> None:  # .dict() is v1
    mod = load("export_tasks")
    pid = _seed(sqlite_session, 1)
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        resp = mod.export_tasks_csv(sqlite_session, pid)
    assert resp.media_type.startswith("text/csv")
