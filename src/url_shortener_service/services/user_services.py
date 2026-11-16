from pwdlib import PasswordHash
from sqlalchemy.exc import IntegrityError

from src.url_shortener_service.auth import create_access_token, hash_password
from src.url_shortener_service.models import User

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

    def login_user(self, email: str, password: str, db) -> str:
        user = db.query(User).filter(User.email == email).first()
        if user is None or not password_hasher.verify(password, user.hashed_password):
            raise ValueError("Incorrect email or password")

        return create_access_token(user.id)


def get_user_service() -> UserService:
    return UserService()
