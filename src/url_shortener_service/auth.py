from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from jwt import PyJWTError
from pwdlib import PasswordHash

from src.url_shortener_service.database import get_db
from src.url_shortener_service.models import User
from src.url_shortener_service.settings import settings

security = HTTPBearer()

password_hasher = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hasher.verify(password, hashed_password)


def create_access_token(user_id: int, expires_minutes: int | None = None) -> str:
    to_encode: dict[str, Any] = {"user_id": user_id}
    minutes = expires_minutes if expires_minutes is not None else 60
    expire = datetime.now(UTC) + timedelta(minutes=minutes)

    to_encode.update({"exp": expire})
    access_token = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")

    return access_token


def verify_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), db=Depends(get_db)
) -> User:
    payload = verify_access_token(credentials.credentials)
    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
