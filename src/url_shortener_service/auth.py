from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash

from src.url_shortener_service.settings import settings

password_hasher = PasswordHash.recommended()


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


print(create_access_token(1, 60))
