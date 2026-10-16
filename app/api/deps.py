from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.services.pagination import MAX_LIMIT

SessionDep = Annotated[Session, Depends(get_session)]
LimitParam = Annotated[int, Query(ge=1, le=MAX_LIMIT, description="Page size (1-100)")]
OffsetParam = Annotated[int, Query(ge=0, description="Rows to skip")]
