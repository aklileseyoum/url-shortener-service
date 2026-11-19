import secrets
import string
from collections.abc import Sequence

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.url_shortener_service.models import URL, Click


class UrlShortenerService:

    def save_to_db(
        self, user_id: int, url: str, db, custom_alias: str | None = None
    ) -> URL:
        for _ in range(3):
            short_code = generate_code()

            if custom_alias:
                existing = db.execute(
                    select(URL).where(
                        (URL.short_code == custom_alias)
                        | (URL.custom_alias == custom_alias)
                    )
                ).scalar_one_or_none()
                if existing is not None:
                    raise ValueError("That alias is already taken")

            new_url = URL(
                original_url=url,
                short_code=short_code,
                custom_alias=custom_alias,
                owner_id=user_id,
            )

            db.add(new_url)
            try:
                db.commit()
                db.refresh(new_url)
                return new_url
            except IntegrityError:
                db.rollback()

        raise ValueError("Could not generate a unique short code")

    def update_url(
        self, user_id: int, short_code: str, new_original_url: str, db
    ) -> URL:
        url = db.execute(
            select(URL).where(
                (URL.short_code == short_code) | (URL.custom_alias == short_code)
            )
        ).scalar_one_or_none()
        if url is None:
            raise ValueError("URL not found")
        if url.owner_id != user_id:
            raise PermissionError("Not your URL")

        url.original_url = new_original_url
        db.commit()
        db.refresh(url)
        return url

    def delete_url(self, user_id: int, short_code: str, db) -> None:
        url = db.execute(
            select(URL).where(
                (URL.short_code == short_code) | (URL.custom_alias == short_code)
            )
        ).scalar_one_or_none()
        if url is None:
            raise ValueError("URL not found")
        if url.owner_id != user_id:
            raise PermissionError("Not your URL")

        db.delete(url)
        db.commit()

    async def list_my_urls(self, user_id: int, db: AsyncSession) -> Sequence[URL]:
        result = await db.execute(
            select(URL).where(URL.owner_id == user_id).options(selectinload(URL.tags))
        )
        return result.scalars().all()

    def get_url_details(self, user_id: int, short_code: str, db) -> URL:
        url = db.execute(
            select(URL).where(
                (URL.short_code == short_code) | (URL.custom_alias == short_code),
                URL.owner_id == user_id,
            )
        ).scalar_one_or_none()
        if url is None:
            raise ValueError("URL not found")
        return url

    def record_click(self, short_code: str, db, ip_address: str | None) -> str | None:
        url = db.execute(
            select(URL).where(
                (URL.short_code == short_code) | (URL.custom_alias == short_code)
            )
        ).scalar_one_or_none()
        if url is None:
            return None

        location = (
            get_location_from_ip(ip_address)
            if ip_address
            else {"country": None, "city": None}
        )
        url.click_count += 1
        click = Click(url_id=url.id, country=location["country"], city=location["city"])
        db.add(click)
        db.commit()
        return url.original_url


def generate_code():
    alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


def get_location_from_ip(ip_address: str) -> dict[str, str | None]:
    try:
        response = httpx.get(f"http://ip-api.com/json/{ip_address}", timeout=3.0)
        data = response.json()
        return {"country": data.get("country"), "city": data.get("city")}
    except Exception:  # noqa: BLE001
        return {"country": None, "city": None}


def get_url_service() -> UrlShortenerService:
    return UrlShortenerService()
