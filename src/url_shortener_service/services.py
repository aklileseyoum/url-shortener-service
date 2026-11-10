import secrets
import string

from src.url_shortener_service.db import get_connection, release_connection


class UrlShortenerService:

    def save_to_db(self, short_code: str, url: str) -> bool:
        conn = get_connection()
        try:
            with conn, conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO url_table (short_code, url)" " VALUES (%s, %s)",
                    (short_code, url),
                )
                return True

        except Exception as e:  # noqa: BLE001
            print(f"save_to_db failed: {e}")
            return False

        finally:
            release_connection(conn)

    def lookup_short_code(self, short_code: str) -> str | None:
        conn = get_connection()
        try:
            with conn, conn.cursor() as cur:
                cur.execute(
                    "SELECT url FROM url_table WHERE short_code = %s", (short_code,)
                )
                url = cur.fetchone()

                if url is None:
                    return None

                return url[0]

        except Exception as e:  # noqa: BLE001
            print(f"failed to fetch: {e}")
            return None

        finally:
            release_connection(conn)


def generate_code():
    alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


def get_url_service() -> UrlShortenerService:
    return UrlShortenerService()
