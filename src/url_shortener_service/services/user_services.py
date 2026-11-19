from fastapi.concurrency import run_in_threadpool
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.url_shortener_service.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_access_token,
)
from src.url_shortener_service.models import RefreshToken, User

password_hasher = PasswordHash.recommended()


class UserService:
    def register_user(self, email: str, password: str, db) -> User:
        hashed_password = hash_password(password)
        user = User(email=email, hashed_password=hashed_password)
        db.add(user)
        try:
            db.commit()

        except IntegrityError:
            db.rollback()
            raise ValueError("Email already registered")

        db.refresh(user)
        return user

    async def login_user(
        self, email: str, password: str, db: AsyncSession
    ) -> tuple[str, str]:
        user = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()

        if user is None or not await run_in_threadpool(
            password_hasher.verify, password, user.hashed_password
        ):
            raise ValueError("Incorrect email or password")

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        db.add(RefreshToken(token=refresh_token, user_id=user.id))
        await db.commit()

        return access_token, refresh_token

    def refresh_tokens(self, refresh_token: str, db) -> tuple[str, str]:
        payload = verify_access_token(refresh_token)
        user_id = payload.get("user_id")
        if user_id is None:
            raise ValueError("Invalid refresh token")

        stored = (
            db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
        )
        if stored is None or stored.is_revoked:
            raise ValueError("Refresh token is invalid or has been revoked")

        stored.is_revoked = True

        new_access_token: str = create_access_token(user_id)
        new_refresh_token: str = create_refresh_token(user_id)
        db.add(RefreshToken(token=new_refresh_token, user_id=user_id))
        db.commit()

        return new_access_token, new_refresh_token


def get_user_service() -> UserService:
    return UserService()
