from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import LimitParam, OffsetParam, SessionDep
from app.models import Task, TaskStatus
from app.schemas import TAG_PATTERN, Page, TaskCreate, TaskRead, TaskUpdate, normalise_tag
from app.services import projects as project_service
from app.services import tasks as service
from app.services.pagination import DEFAULT_LIMIT, paginate

router = APIRouter(tags=["tasks"])

MAX_QUERY_LENGTH = 200  # F07: ?q= is 1-200 chars after trimming (the title column's limit)


def _require_task(session: SessionDep, task_id: int) -> Task:
    task = service.get_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


def _require_project(session: SessionDep, project_id: int) -> None:
    if project_service.get_project(session, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_task(project_id: int, data: TaskCreate, session: SessionDep) -> Task:
    _require_project(session, project_id)
    return service.create_task(session, project_id, data)


@router.get("/projects/{project_id}/tasks", response_model=Page[TaskRead])
def list_tasks(
    project_id: int,
    session: SessionDep,
    status_: Annotated[TaskStatus | None, Query(alias="status")] = None,
    max_priority: Annotated[int | None, Query(ge=1, le=5)] = None,
    overdue: bool | None = None,
    tag: str | None = None,
    q: Annotated[str | None, Query(description="Case-insensitive title substring")] = None,
    limit: LimitParam = DEFAULT_LIMIT,
    offset: OffsetParam = 0,
) -> dict[str, object]:
    if tag is not None:
        tag = normalise_tag(tag)
        if not TAG_PATTERN.fullmatch(str(tag)):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="tag must be 1-32 chars of a-z, 0-9 or '-'",
            )
    if q is not None:
        q = q.strip()
        if not 1 <= len(q) <= MAX_QUERY_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"q must be 1-{MAX_QUERY_LENGTH} characters after trimming",
            )
    _require_project(session, project_id)
    stmt = service.tasks_query(
        project_id, status=status_, max_priority=max_priority, overdue=overdue, tag=tag, q=q
    )
    items, total = paginate(session, stmt, limit, offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/tasks/{task_id}", response_model=TaskRead)
def get_task(task_id: int, session: SessionDep) -> Task:
    return _require_task(session, task_id)


@router.patch("/tasks/{task_id}", response_model=TaskRead)
def update_task(task_id: int, data: TaskUpdate, session: SessionDep) -> Task:
    return service.update_task(session, _require_task(session, task_id), data)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, session: SessionDep) -> Response:
    service.delete_task(session, _require_task(session, task_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
