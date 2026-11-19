import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import update
from backend.models import RefreshToken
import jwt
from backend.config import settings

past = datetime.now(timezone.utc) - timedelta(minutes=1)
expired = jwt.encode({"sub": "1", "exp": past}, settings.SECRET_KEY, algorithm="HS256")
forged = jwt.encode({"sub": "1"}, "not_real_key", algorithm="HS256")


async def test_register(client):
    response = await client.post(
        "/register", json={"login": "user1", "password": "secret123"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["login"] == "user1"
    assert "id" in body
    assert "password" not in body
    assert "hashed_password" not in body


@pytest.mark.parametrize(
    "payload",
    [
        {"login": "", "password": "secret123"},
        {"login": "user1"},
        {"login": "a" * 51, "password": "secret123"},
    ],
    ids=["empty-login", "no-password", "too-long-login"],
)
async def test_register_invalid(client, payload):
    response = await client.post("/register", json=payload)
    assert response.status_code == 422


async def test_register_duplicate(client, user1_headers):
    response = await client.post(
        "/register", json={"login": "user1", "password": "secret123"}
    )
    assert response.status_code == 409
    response = await client.post(
        "/register", json={"login": "User1", "password": "secret123"}
    )
    assert response.status_code == 409


async def test_login_success(client, user1_headers):
    response = await client.post(
        "/token", data={"username": "user1", "password": "secret123"}
    )
    assert response.status_code == 200
    response = await client.post(
        "/token", data={"username": "USER1", "password": "secret123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "wrong", "password": "secret123"},
        {"username": "user1", "password": "wrong"},
        {"username": "wrong", "password": "wrong"},
    ],
)
async def test_login_wrong(client, user1_headers, payload):
    response = await client.post("/token", data=payload)
    assert response.status_code == 401


async def test_refresh_token_rotates(client):
    response = await client.post(
        "/register", json={"login": "user1", "password": "secret123"}
    )
    assert response.status_code == 201

    response = await client.post(
        "/token", data={"username": "user1", "password": "secret123"}
    )
    assert response.status_code == 200

    headers_1 = {"Authorization": f"Bearer {response.json()['access_token']}"}
    refresh_token_json_1 = {"refresh_token": response.json()["refresh_token"]}

    response = await client.get("/tasks", headers=headers_1)
    assert response.status_code == 200

    response = await client.post("/token/refresh", json=refresh_token_json_1)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    headers_2 = {"Authorization": f"Bearer {data['access_token']}"}
    refresh_token_json_2 = {"refresh_token": data["refresh_token"]}
    response = await client.get("/tasks", headers=headers_2)
    assert response.status_code == 200

    response = await client.post("/token/refresh", json=refresh_token_json_1)
    assert response.status_code == 401

    response = await client.post("/token/refresh", json=refresh_token_json_2)
    assert response.status_code == 200


async def test_refresh_invalid(client, db_session):
    response = await client.post(
        "/register", json={"login": "user1", "password": "secret123"}
    )
    assert response.status_code == 201
    response = await client.post(
        "/token", data={"username": "user1", "password": "secret123"}
    )
    assert response.status_code == 200

    refresh_token = {"refresh_token": "Mv9Of933KqjOm_5X57ESxDlbe0gBbU9aPF194-aaCdc"}
    response_bad = await client.post("/token/refresh", json=refresh_token)
    assert response_bad.status_code == 401
    data = response_bad.json()
    assert "access_token" not in data
    assert "refresh_token" not in data

    refresh_token["refresh_token"] = response.json()["refresh_token"]
    await db_session.execute(
        update(RefreshToken).values(
            expires_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
    )
    await db_session.commit()
    response = await client.post("/token/refresh", json=refresh_token)
    assert response.status_code == 401
    data = response.json()
    assert "access_token" not in data
    assert "refresh_token" not in data


async def test_logout(client):
    response = await client.post(
        "/register", json={"login": "user1", "password": "secret123"}
    )
    assert response.status_code == 201
    response = await client.post(
        "/token", data={"username": "user1", "password": "secret123"}
    )
    assert response.status_code == 200
    data = response.json()

    response = await client.post(
        "/token/refresh", json={"refresh_token": data["refresh_token"]}
    )
    assert response.status_code == 200
    data = response.json()

    response = await client.post(
        "/logout", json={"refresh_token": data["refresh_token"]}
    )
    assert response.status_code == 204

    response = await client.post(
        "/token/refresh", json={"refresh_token": data["refresh_token"]}
    )
    assert response.status_code == 401

    response = await client.post(
        "/logout", json={"refresh_token": data["refresh_token"]}
    )
    assert response.status_code == 204


@pytest.mark.parametrize(
    "payload",
    [{}, {"Authorization": f"Bearer {expired}"}, {"Authorization": f"Bearer {forged}"}],
    ids=["without-headers", "trash_token", "expired_token"],
)
async def test_requires_valid_token(client, payload):
    response = await client.get("/tasks", headers=payload)
    assert response.status_code == 401
