from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Project
from app.schemas import ProjectCreate


class DuplicateProjectError(Exception):
    pass


def create_project(session: Session, data: ProjectCreate) -> Project:
    project = Project(name=data.name, description=data.description)
    session.add(project)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DuplicateProjectError(data.name) from exc
    session.refresh(project)
    return project


def projects_query() -> Select[Project]:
    return select(Project).order_by(Project.id)


def list_projects(session: Session) -> Sequence[Project]:
    return session.scalars(projects_query()).all()


def get_project(session: Session, project_id: int) -> Project | None:
    return session.get(Project, project_id)
