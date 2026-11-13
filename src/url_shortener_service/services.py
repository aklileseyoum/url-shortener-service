import secrets
import string

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.url_shortener_service.models import URL, Click, Tag, User


class UrlShortenerService:

    def register_user(self, email: str, db) -> User:
        user = User(email=email)
        db.add(user)
        try:
            db.commit()

        except IntegrityError:
            db.rollback()
            raise ValueError("Email already registered")

        db.refresh(user)
        return user

    def save_to_db(
        self, email: str, url: str, db, custom_alias: str | None = None
    ) -> URL:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            raise ValueError("User not found, register first")

        for _ in range(3):
            short_code = generate_code()
            new_url = URL(
                original_url=url,
                short_code=short_code,
                custom_alias=custom_alias,
                owner_id=user.id,
            )
            db.add(new_url)
            try:
                db.commit()
                db.refresh(new_url)
                return new_url
            except IntegrityError:
                db.rollback()

        raise ValueError("Could not generate a unique short code")

    def update_url(self, email: str, short_code: str, new_original_url: str, db) -> URL:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            raise ValueError("User not found")

        url = db.execute(
            select(URL).where(URL.short_code == short_code)
        ).scalar_one_or_none()
        if url is None:
            raise ValueError("URL not found")
        if url.owner_id != user.id:
            raise PermissionError("Not your URL")

        url.original_url = new_original_url
        db.commit()
        db.refresh(url)
        return url

    def delete_url(self, email: str, short_code: str, db) -> None:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            raise ValueError("User not found")

        url = db.execute(
            select(URL).where(URL.short_code == short_code)
        ).scalar_one_or_none()
        if url is None:
            raise ValueError("URL not found")
        if url.owner_id != user.id:
            raise PermissionError("Not your URL")

        db.delete(url)
        db.commit()

    def list_my_urls(self, email: str, db) -> list[URL]:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            raise ValueError("User not found")
        return db.execute(select(URL).where(URL.owner_id == user.id)).scalars().all()

    def get_url_details(self, email: str, short_code: str, db) -> URL:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            raise ValueError("User not found")
        url = db.execute(
            select(URL).where(URL.short_code == short_code, URL.owner_id == user.id)
        ).scalar_one_or_none()
        if url is None:
            raise ValueError("URL not found")
        return url

    def record_click(self, short_code: str, db) -> str | None:
        url = db.execute(
            select(URL).where(URL.short_code == short_code)
        ).scalar_one_or_none()
        if url is None:
            return None
        url.click_count += 1
        click = Click(url_id=url.id)
        db.add(click)
        db.commit()
        return url.original_url

    def create_tag(self, name: str, db) -> Tag:
        tag = Tag(name=name)
        db.add(tag)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise ValueError("Tag already exists")
        db.refresh(tag)
        return tag

    def attach_tag(self, email: str, short_code: str, tag_name: str, db) -> URL:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            raise ValueError("User not found")

        url = db.execute(
            select(URL).where(URL.short_code == short_code, URL.owner_id == user.id)
        ).scalar_one_or_none()
        if url is None:
            raise ValueError("URL not found")

        tag = db.execute(select(Tag).where(Tag.name == tag_name)).scalar_one_or_none()
        if tag is None:
            raise ValueError("Tag not found, create it first")

        url.tags.append(tag)
        db.commit()
        db.refresh(url)
        return url


def generate_code():
    alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


def get_url_service() -> UrlShortenerService:
    return UrlShortenerService()
