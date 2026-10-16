from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, status

from app.api.deps import SessionDep
from app.models import Project
from app.schemas import ProjectCreate, ProjectRead
from app.services import projects as service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectCreate, session: SessionDep) -> Project:
    try:
        return service.create_project(session, data)
    except service.DuplicateProjectError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project named {data.name!r} already exists",
        ) from None


@router.get("", response_model=list[ProjectRead])
def list_projects(session: SessionDep) -> Sequence[Project]:
    return service.list_projects(session)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, session: SessionDep) -> Project:
    project = service.get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project
