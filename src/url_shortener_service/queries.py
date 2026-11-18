from datetime import UTC, datetime

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import joinedload, selectinload

from src.url_shortener_service.models import URL, Click


def active_urls(db):
    query = select(URL).where(URL.is_active == True).options(selectinload(URL.tags))
    return db.execute(query).scalars().all()


def expired_urls(db):
    query = (
        select(URL)
        .where(URL.expires_at != None)
        .where(URL.expires_at < datetime.now(UTC))
        .options(joinedload(URL.owner))
    )
    return db.execute(query).scalars().all()


def popular_urls(db):
    query = (
        select(URL).order_by(URL.click_count.desc()).options(selectinload(URL.clicks))
    )
    return db.execute(query).scalars().all()


def clicks_by_country(db):
    stmt = select(Click.country, func.count(Click.id)).group_by(Click.country)
    return db.execute(stmt).all()


def count_active_urls_for_user(user_id: int, db) -> int:
    stmt = select(func.count(URL.id)).where(
        URL.owner_id == user_id, URL.is_active == True
    )
    return db.execute(stmt).scalar_one()


def clicks_over_time(short_code: str, db) -> list:
    stmt = (
        select(cast(Click.clicked_at, Date), func.count(Click.id))
        .join(URL, Click.url_id == URL.id)
        .where((URL.short_code == short_code) | (URL.custom_alias == short_code))
        .group_by(cast(Click.clicked_at, Date))
        .order_by(cast(Click.clicked_at, Date))
    )
    return db.execute(stmt).all()


def clicks_by_country_for_url(short_code: str, db) -> list:
    stmt = (
        select(Click.country, func.count(Click.id))
        .join(URL, Click.url_id == URL.id)
        .where((URL.short_code == short_code) | (URL.custom_alias == short_code))
        .group_by(Click.country)
    )
    return db.execute(stmt).all()
