from fastapi import APIRouter, Depends, Path, Query
from ..schemas import TaskCreate, TaskRead
from ..models import Task
from ..deps import get_owned_project, get_owned_task
from ..security import get_current_user_id
from ..database import get_session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=201)
async def create_task(
    task_in: TaskCreate,
    session: AsyncSession = Depends(get_session),
    current_id: int = Depends(get_current_user_id),
):
    if task_in.project_id is not None:
        await get_owned_project(session, task_in.project_id, current_id)
    task = Task(
        title=task_in.title,
        description=task_in.description,
        priority=task_in.priority,
        user_id=current_id,
        project_id=task_in.project_id,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.get("", response_model=list[TaskRead])
async def get_tasks(
    session: AsyncSession = Depends(get_session),
    current_id: int = Depends(get_current_user_id),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    priority: Annotated[int | None, Query(ge=1, le=4)] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    project_id: int | None = None,
):
    stmt = select(Task).where(Task.user_id == current_id)
    if priority is not None:
        stmt = stmt.where(Task.priority == priority)
    if search is not None:
        stmt = stmt.where(Task.title.icontains(search, autoescape=True))
    if project_id is not None:
        await get_owned_project(session, project_id, current_id)
        stmt = stmt.where(Task.project_id == project_id)
    stmt = stmt.order_by(Task.id).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: Annotated[int, Path(ge=1)],
    session: AsyncSession = Depends(get_session),
    current_id: int = Depends(get_current_user_id),
):
    task = await get_owned_task(session, task_id, current_id)
    return task


@router.put("/{task_id}", response_model=TaskRead)
async def edit_task(
    task_id: Annotated[int, Path(ge=1)],
    task_in: TaskCreate,
    session: AsyncSession = Depends(get_session),
    current_id: int = Depends(get_current_user_id),
):
    if task_in.project_id is not None:
        await get_owned_project(session, task_in.project_id, current_id)
    task = await get_owned_task(session, task_id, current_id)
    task.title = task_in.title
    task.description = task_in.description
    task.priority = task_in.priority
    task.project_id = task_in.project_id
    await session.commit()
    await session.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: Annotated[int, Path(ge=1)],
    session: AsyncSession = Depends(get_session),
    current_id: int = Depends(get_current_user_id),
):
    task = await get_owned_task(session, task_id, current_id)
    await session.delete(task)
    await session.commit()
