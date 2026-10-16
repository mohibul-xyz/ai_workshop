from fastapi import APIRouter, HTTPException, status

from app.api.deps import LimitParam, OffsetParam, SessionDep
from app.models import Project
from app.schemas import Page, ProjectCreate, ProjectRead
from app.services import projects as service
from app.services.pagination import DEFAULT_LIMIT, paginate

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


@router.get("", response_model=Page[ProjectRead])
def list_projects(
    session: SessionDep, limit: LimitParam = DEFAULT_LIMIT, offset: OffsetParam = 0
) -> dict[str, object]:
    items, total = paginate(session, service.projects_query(), limit, offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, session: SessionDep) -> Project:
    project = service.get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project
