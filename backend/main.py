from fastapi import FastAPI, Depends, HTTPException
from .schemas import TaskCreate, TaskRead, UserOut, UserCreate
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_session
from .models import User
from .security import get_password_hash
from sqlalchemy.exc import IntegrityError
import asyncio


app = FastAPI()


@app.get('/health')
async def health():
    return {'status': 'OK'}

@app.post('/register', status_code=201, response_model=UserOut)
async def register_user(
    user_in: UserCreate,
    session: AsyncSession = Depends(get_session)
):
    user = User(
        login=user_in.login.lower(),
        hashed_password=await asyncio.to_thread(get_password_hash, user_in.password)
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
    