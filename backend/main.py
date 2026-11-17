from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .routers import projects, tasks, auth
import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from sqlalchemy import delete
from .database import SessionLocal
from .models import RefreshToken

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


logger = logging.getLogger("uvicorn.error")


async def cleanup_loop():
    while True:
        try:
            async with SessionLocal() as session:
                result = await session.execute(
                    delete(RefreshToken).where(
                        RefreshToken.expires_at < datetime.now(timezone.utc)
                    )
                )
                await session.commit()
            logger.info("Удалено истёкших refresh-токенов: %d", result.rowcount)
        except Exception:
            logger.exception("Ошибка очистки refresh-токенов")
        await asyncio.sleep(24 * 3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(cleanup_loop())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(lifespan=lifespan)


app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(auth.router)


@app.get("/health")
async def health():
    return {"status": "OK"}


# Статика фронтенда монтируется последней, чтобы API-маршруты имели приоритет.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
