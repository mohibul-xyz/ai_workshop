"""Export a project's tasks as CSV — reference fix.

Fixes: CSVResponse does not exist (use Response + media_type); Query.paginate() is
Flask-SQLAlchemy only (use limit/offset); .dict() is Pydantic v1 (use model_dump).
"""

import csv
import io

from fastapi import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Task
from app.schemas import TaskRead

CSV_COLUMNS = ["id", "title", "status", "priority", "due_at"]


def export_tasks_csv(
    session: Session, project_id: int, page: int = 1, per_page: int = 50
) -> Response:
    stmt = (
        select(Task)
        .where(Task.project_id == project_id)
        .order_by(Task.id)
        .limit(per_page)
        .offset((page - 1) * per_page)
    )
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for task in session.scalars(stmt):
        writer.writerow(TaskRead.model_validate(task).model_dump(mode="json"))
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=project-{project_id}.csv"},
    )
