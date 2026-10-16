"""F06: limit/offset pagination over any ordered SELECT (docs/api-conventions.md § Pagination)."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def paginate[T](
    session: Session, stmt: Select[T], limit: int, offset: int
) -> tuple[Sequence[T], int]:
    """Return one page of `stmt` and the total row count matching its filters.

    `stmt` must already carry its ORDER BY so pages are stable; filters apply before paging.
    """
    count_stmt: Select[Any] = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = session.scalar(count_stmt) or 0
    items = session.scalars(stmt.limit(limit).offset(offset)).all()
    return items, total
