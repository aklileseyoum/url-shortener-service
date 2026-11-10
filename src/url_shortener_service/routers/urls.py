import secrets
import string

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import HttpUrl

from src.url_shortener_service.db import get_connection, release_connection

router = APIRouter()


def generate_code():
    alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


def save_to_db(short_code: str, url: str) -> bool:
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


def lookup_short_code(short_code: str) -> str | None:
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


@router.post("/api/urls", status_code=201)
async def shorten_url(url: HttpUrl):
    for _ in range(3):
        short_code = generate_code()

        if not save_to_db(short_code, str(url)):
            raise HTTPException(status_code=500, detail="Could not save URL")

    return JSONResponse(
        content={"short_code": short_code, "message": "It was successful"}
    )


@router.get("/{short_code}")
async def access_url(short_code: str):
    url = lookup_short_code(short_code)
    if url is None:
        raise HTTPException(status_code=404, detail="Short code not found")

    return RedirectResponse(url=url)
