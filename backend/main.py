from fastapi import FastAPI
from .routers import projects, tasks, auth

app = FastAPI()

app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(auth.router)


@app.get("/health")
async def health():
    return {"status": "OK"}
