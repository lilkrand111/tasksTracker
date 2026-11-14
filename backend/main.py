from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routers import projects, tasks, auth

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI()

app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(auth.router)


@app.get("/health")
async def health():
    return {"status": "OK"}


# Статика фронтенда монтируется последней, чтобы API-маршруты имели приоритет.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
