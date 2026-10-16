from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import SessionDep
from app.models import Task, TaskStatus
from app.schemas import TaskCreate, TaskRead, TaskUpdate
from app.services import projects as project_service
from app.services import tasks as service

router = APIRouter(tags=["tasks"])


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


@router.get("/projects/{project_id}/tasks", response_model=list[TaskRead])
def list_tasks(
    project_id: int,
    session: SessionDep,
    status_: Annotated[TaskStatus | None, Query(alias="status")] = None,
    max_priority: Annotated[int | None, Query(ge=1, le=5)] = None,
) -> Sequence[Task]:
    _require_project(session, project_id)
    return service.list_tasks(session, project_id, status=status_, max_priority=max_priority)


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
