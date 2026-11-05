from fastapi import FastAPI, Depends, HTTPException, status, Path, Query
from sqlalchemy.exc import IntegrityError
from .schemas import UserOut, UserCreate, Token, RefreshRequest, TaskCreate, TaskRead
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_session
from .models import User, RefreshToken, Task
from .security import (
    get_password_hash,
    authenticate_user,
    generate_refresh_token,
    create_access_token,
    hash_refresh_token,
    get_current_user_id,
)
import asyncio
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, delete
from datetime import datetime, timezone

app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "OK"}


@app.post("/register", status_code=201, response_model=UserOut)
async def register_user(
    user_in: UserCreate, session: AsyncSession = Depends(get_session)
):
    user = User(
        login=user_in.login.lower(),
        hashed_password=await asyncio.to_thread(get_password_hash, user_in.password),
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=400, detail="Пользователь с таким логином уже существует!"
        )
    await session.refresh(user)
    return user


@app.post("/token", response_model=Token)
async def token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: AsyncSession = Depends(get_session),
):
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    raw, token_hash, expires_at = generate_refresh_token()
    session.add(
        RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at)
    )
    await session.commit()
    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, refresh_token=raw, token_type="bearer")


@app.post("/token/refresh", response_model=Token)
async def refresh(body: RefreshRequest, session: AsyncSession = Depends(get_session)):
    record = await session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(body.refresh_token)
        )
    )
    if not record or record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    raw, token_hash, expires_at = generate_refresh_token()
    record.token_hash = token_hash
    record.expires_at = expires_at
    await session.commit()
    return Token(
        access_token=create_access_token(data={"sub": str(record.user_id)}),
        refresh_token=raw,
        token_type="bearer",
    )


@app.post("/logout", status_code=204)
async def logout(body: RefreshRequest, session: AsyncSession = Depends(get_session)):
    await session.execute(
        delete(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(body.refresh_token)
        )
    )
    await session.commit()


@app.post("/tasks", response_model=TaskRead, status_code=201)
async def create_task(
    task_in: TaskCreate,
    session: AsyncSession = Depends(get_session),
    current_id: int = Depends(get_current_user_id),
):
    task = Task(
        title=task_in.title,
        description=task_in.description,
        priority=task_in.priority,
        user_id=current_id,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@app.get("/tasks", response_model=list[TaskRead])
async def get_tasks(
    session: AsyncSession = Depends(get_session),
    current_id: int = Depends(get_current_user_id),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    priority: Annotated[int | None, Query(ge=1, le=4)] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
):
    stmt = select(Task).where(Task.user_id == current_id)
    if priority is not None:
        stmt = stmt.where(Task.priority == priority)
    if search is not None:
        stmt = stmt.where(Task.title.icontains(search, autoescape=True))
    stmt = stmt.order_by(Task.id).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return result.scalars().all()


@app.get("/tasks/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: Annotated[int, Path(ge=1)],
    session: AsyncSession = Depends(get_session),
    current_id: int = Depends(get_current_user_id),
):
    task = await session.scalar(
        select(Task).where(Task.user_id == current_id, Task.id == task_id)
    )
    if task is None:
        raise HTTPException(
            status_code=404, detail=f"Задача с {task_id} ID не найдена!"
        )
    return task


@app.put("/tasks/{task_id}", response_model=TaskRead)
async def edit_task(
    task_id: Annotated[int, Path(ge=1)],
    task_in: TaskCreate,
    session: AsyncSession = Depends(get_session),
    current_id: int = Depends(get_current_user_id),
):
    task = await session.scalar(
        select(Task).where(Task.user_id == current_id, Task.id == task_id)
    )
    if task is None:
        raise HTTPException(
            status_code=404, detail=f"Задача с {task_id} ID не найдена!"
        )
    task.title = task_in.title
    task.description = task_in.description
    task.priority = task_in.priority
    await session.commit()
    await session.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: Annotated[int, Path(ge=1)],
    session: AsyncSession = Depends(get_session),
    current_id: int = Depends(get_current_user_id),
):
    task = await session.scalar(
        select(Task).where(Task.user_id == current_id, Task.id == task_id)
    )
    if task is None:
        raise HTTPException(
            status_code=404, detail=f"Задача с {task_id} ID не найдена!"
        )
    await session.delete(task)
    await session.commit()
