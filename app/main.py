from fastapi import FastAPI
from sqlalchemy import text

from app.api import api_router
from app.config import get_settings
from app.db import engine
from app.observability import configure_logging, install_request_logging, logger

configure_logging(get_settings().log_level)

app = FastAPI(title="TaskHub", version="0.1.0")
install_request_logging(app)
app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error(
            "database unreachable",
            extra={"fields": {"event": "health", "error": f"{type(exc).__name__}: {exc}"}},
        )
        raise
    return {"status": "ok", "database": "ok"}
