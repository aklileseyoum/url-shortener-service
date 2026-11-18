from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.url_shortener_service.models import URL, Tag


class TagService:
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

    def attach_tag(self, user_id: int, short_code: str, tag_name: str, db) -> URL:
        url = db.execute(
            select(URL).where(
                (URL.short_code == short_code) | (URL.custom_alias == short_code),
                URL.owner_id == user_id,
            )
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


def get_tag_service() -> TagService:
    return TagService()
