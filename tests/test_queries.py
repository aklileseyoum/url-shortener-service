from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.url_shortener_service.database import LOCAL_DATABASE_URL
from src.url_shortener_service.queries import active_urls, expired_urls, popular_urls


async def test_active_urls_only_returns_active():
    engine = create_async_engine(LOCAL_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as db:
        urls = await active_urls(db)
        assert all(u.is_active for u in urls)
    await engine.dispose()


async def test_expired_urls_only_returns_past_expiry():
    engine = create_async_engine(LOCAL_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as db:
        urls = await expired_urls(db)
        now = datetime.now(UTC).replace(tzinfo=None)
        assert all(u.expires_at is not None and u.expires_at < now for u in urls)
    await engine.dispose()


async def test_popular_urls_are_sorted_descending():
    engine = create_async_engine(LOCAL_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as db:
        urls = await popular_urls(db)
        click_counts = [u.click_count for u in urls]
        assert click_counts == sorted(click_counts, reverse=True)
    await engine.dispose()
