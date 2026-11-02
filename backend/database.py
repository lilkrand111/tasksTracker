from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from .config import settings
from sqlalchemy.orm import DeclarativeBase


DATABASE_URL = settings.DB_URL

engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_session():
    async with SessionLocal() as session:
        yield session