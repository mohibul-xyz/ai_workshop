from fastapi import APIRouter

from app.api import projects, tasks

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
