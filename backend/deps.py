from sqlalchemy.ext.asyncio import AsyncSession
from .models import Task, Project
from sqlalchemy import select
from fastapi import HTTPException


async def get_owned_task(session: AsyncSession, task_id: int, user_id: int) -> Task:
    task = await session.scalar(
        select(Task).where(Task.user_id == user_id, Task.id == task_id)
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task


async def get_owned_project(
    session: AsyncSession, project_id: int, user_id: int
) -> Project:
    project = await session.scalar(
        select(Project).where(Project.user_id == user_id, Project.id == project_id)
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Проект не найден")
    return project
