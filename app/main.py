from fastapi import FastAPI
from sqlalchemy import text

from app.api import api_router
from app.db import engine

app = FastAPI(title="TaskHub", version="0.1.0")
app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str]:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
