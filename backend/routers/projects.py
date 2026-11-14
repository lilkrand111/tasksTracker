from fastapi import APIRouter, Depends, Path, Query
from ..schemas import ProjectRead, ProjectCreate
from typing import Annotated
from ..database import get_session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..security import get_current_user_id
from ..models import Project
from ..deps import get_owned_project

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=201)
async def create_project(
    project_in: ProjectCreate,
    session: AsyncSession = Depends(get_session),
    current_id: int = Depends(get_current_user_id),
):
    project = Project(
        name=project_in.name, description=project_in.description, user_id=current_id
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@router.get("", response_model=list[ProjectRead])
async def get_projects(
    session: AsyncSession = Depends(get_session),
    current_id: int = Depends(get_current_user_id),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
):
    stmt = select(Project).where(Project.user_id == current_id)
    if search is not None:
        stmt = stmt.where(Project.name.icontains(search, autoescape=True))
    stmt = stmt.order_by(Project.id).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: Annotated[int, Path(ge=1)],
    session: AsyncSession = Depends(get_session),
    current_id: int = Depends(get_current_user_id),
):
    project = await get_owned_project(session, project_id, current_id)
    return project


@router.put("/{project_id}", response_model=ProjectRead)
async def edit_project(
    project_id: Annotated[int, Path(ge=1)],
    project_in: ProjectCreate,
    session: AsyncSession = Depends(get_session),
    current_id: int = Depends(get_current_user_id),
):
    project = await get_owned_project(session, project_id, current_id)
    project.name = project_in.name
    project.description = project_in.description
    await session.commit()
    await session.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: Annotated[int, Path(ge=1)],
    session: AsyncSession = Depends(get_session),
    current_id: int = Depends(get_current_user_id),
):
    project = await get_owned_project(session, project_id, current_id)
    await session.delete(project)
    await session.commit()
