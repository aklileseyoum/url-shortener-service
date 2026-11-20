from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.url_shortener_service.models import URL, Tag


class TagService:
    async def create_tag(self, name: str, db: AsyncSession) -> Tag:
        tag = Tag(name=name)
        db.add(tag)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise ValueError("Tag already exists")
        await db.refresh(tag)
        return tag

    async def attach_tag(
        self, user_id: int, short_code: str, tag_name: str, db: AsyncSession
    ) -> URL:
        url = (
            await db.execute(
                select(URL)
                .where(
                    (URL.short_code == short_code) | (URL.custom_alias == short_code),
                    URL.owner_id == user_id,
                )
                .options(selectinload(URL.tags))
            )
        ).scalar_one_or_none()
        if url is None:
            raise ValueError("URL not found")

        tag = (
            await db.execute(select(Tag).where(Tag.name == tag_name))
        ).scalar_one_or_none()

        if tag is None:
            raise ValueError("Tag not found, create it first")

        url.tags.append(tag)
        await db.commit()
        return url


def get_tag_service() -> TagService:
    return TagService()
