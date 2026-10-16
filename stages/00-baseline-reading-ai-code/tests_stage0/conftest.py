"""Stage 0 tests run against ai_written/ (default: they FAIL — each proves a seeded flaw)
or against your fixes / the reference solutions: STAGE0_TARGET=solutions."""

import importlib
import os
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base

HERE = Path(__file__).resolve().parents[1]
TARGET = os.environ.get("STAGE0_TARGET", "ai_written")


@pytest.fixture
def load() -> Iterator[object]:
    """load('overdue') imports the module from the target folder (fresh every test)."""
    sys.path.insert(0, str(HERE / TARGET))
    loaded: list[str] = []

    def _load(name: str) -> ModuleType:
        sys.modules.pop(name, None)
        loaded.append(name)
        return importlib.import_module(name)

    yield _load
    sys.path.remove(str(HERE / TARGET))
    for name in loaded:
        sys.modules.pop(name, None)


@pytest.fixture
def sqlite_session() -> Iterator[Session]:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()
