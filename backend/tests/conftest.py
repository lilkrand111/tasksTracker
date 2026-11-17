import os

TEST_DB_URL = "postgresql+psycopg://tasks:tasks@localhost:5433/taskstracker_test"

os.environ["DB_URL"] = TEST_DB_URL

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.database import Base, get_session
from backend.main import app

test_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    async def create():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    async def drop():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    asyncio.run(create())
    yield
    asyncio.run(drop())


@pytest.fixture(autouse=True)
async def clean_tables():
    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE users, projects, tasks, refresh_tokens RESTART IDENTITY CASCADE"
            )
        )


async def override_get_session():
    transport = ASGITransport(app=app)
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client():
    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def alice_headers(client):
    await client.post("/register", json={"login": "user1", "password": "secret123"})
    response = await client.post(
        "/token", data={"username": "user1", "password": "secret123"}
    )
    tokens = response.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture
async def bob_headers(client):
    await client.post("/register", json={"login": "user2", "password": "secret321"})
    response = await client.post(
        "/token", data={"username": "user2", "password": "secret321"}
    )
    tokens = response.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture
def make_task(client):
    async def _make(headers, **fields):
        payload = {"title": "задача", **fields}
        response = await client.post("/tasks", json=payload, headers=headers)
        assert response.status_code == 201
        return response.json()

    return _make
