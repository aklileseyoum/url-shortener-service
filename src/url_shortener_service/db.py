"""PostgreSQL connection pool (settings match docker-compose.yml)."""

from psycopg2 import pool
from psycopg2.extensions import connection

from src.url_shortener_service.settings import settings

_pool = pool.SimpleConnectionPool(
    1,
    5,
    host=settings.postgres_host,
    port=int(settings.postgres_port),
    user=settings.postgres_user,
    password=settings.postgres_password,
    dbname=settings.postgres_db,
)


def get_connection() -> connection:
    """Borrow a connection from the pool. Always give it back."""
    return _pool.getconn()


def release_connection(conn: connection) -> None:
    """Return a borrowed connection to the pool."""
    _pool.putconn(conn)


def close_pool() -> None:
    """Close every connection (call once when the program ends)."""
    _pool.closeall()
