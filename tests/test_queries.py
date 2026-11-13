from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.url_shortener_service.database import LOCAL_DATABASE_URL
from src.url_shortener_service.queries import active_urls, expired_urls, popular_urls


def test_active_urls_only_returns_active():
    engine = create_engine(LOCAL_DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        urls = active_urls(db)
        assert all(u.is_active for u in urls)
    finally:
        db.close()


def test_expired_urls_only_returns_past_expiry():
    engine = create_engine(LOCAL_DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        urls = expired_urls(db)
        now = datetime.now(UTC)
        assert all(u.expires_at is not None and u.expires_at < now for u in urls)
    finally:
        db.close()


def test_popular_urls_are_sorted_descending():
    engine = create_engine(LOCAL_DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        urls = popular_urls(db)
        click_counts = [u.click_count for u in urls]
        assert click_counts == sorted(click_counts, reverse=True)
    finally:
        db.close()
