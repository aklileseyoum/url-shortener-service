from datetime import UTC, datetime

from sqlalchemy import func, select
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
