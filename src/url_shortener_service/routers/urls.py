from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import HttpUrl

from src.url_shortener_service.services import (
    UrlShortenerService,
    generate_code,
    get_url_service,
)

router = APIRouter()


@router.post("/api/urls", status_code=201)
async def shorten_url(
    url: HttpUrl, service: UrlShortenerService = Depends(get_url_service)  # noqa: B008
):
    for _ in range(3):
        short_code = generate_code()
        if service.save_to_db(short_code, str(url)):
            return JSONResponse(
                content={"short_code": short_code, "message": "It was successful"}
            )

    raise HTTPException(status_code=500, detail="Could not save URL")


@router.get("/{short_code}")
async def access_url(
    short_code: str,
    service: UrlShortenerService = Depends(get_url_service),  # noqa: B008
):
    url = service.lookup_short_code(short_code)
    if url is None:
        raise HTTPException(status_code=404, detail="Short code not found")

    return RedirectResponse(url=url)
