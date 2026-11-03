from pwdlib import PasswordHash
from .config import settings
from datetime import datetime, timezone, timedelta
import jwt
import hashlib
import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from .models import User
from sqlalchemy import select
import asyncio
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

password_hash = PasswordHash.recommended()

DUMMY_HASH = password_hash.hash("dummypassword")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_password_hash(password):
    return password_hash.hash(password)


def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def hash_refresh_token(token: str):
    return hashlib.sha256(token.encode()).hexdigest()


def generate_refresh_token():
    raw = secrets.token_urlsafe(32)
    token_hash = hash_refresh_token(raw)
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return raw, token_hash, expire


async def authenticate_user(session: AsyncSession, login: str, password: str):
    user = await session.scalar(select(User).where(User.login == login.lower()))
    if not user:
        await asyncio.to_thread(verify_password, password, DUMMY_HASH)
        return False
    if not await asyncio.to_thread(verify_password, password, user.hashed_password):
        return False
    return user


def get_current_user_id(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
