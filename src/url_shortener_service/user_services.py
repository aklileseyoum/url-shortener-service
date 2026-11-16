from sqlalchemy.exc import IntegrityError

from src.url_shortener_service.auth import hash_password
from src.url_shortener_service.models import User


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


def get_user_service() -> UserService:
    return UserService()
