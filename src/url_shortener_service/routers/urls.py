from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import HttpUrl

from src.url_shortener_service.database import get_db
from src.url_shortener_service.responses import SuccessResponse
from src.url_shortener_service.services import (
    UrlShortenerService,
    get_url_service,
)

router = APIRouter()


@router.post("/api/urls", status_code=201)
async def shorten_url(
    email: str,
    url: HttpUrl,
    service: UrlShortenerService = Depends(get_url_service),
    db=Depends(get_db),
    custom_alias: str | None = None,
):
    try:
        new_url = service.save_to_db(email, str(url), db, custom_alias)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SuccessResponse(
        status_code=201,
        message="It was successful",
        data={"short_code": new_url.short_code},
    )


@router.get("/{short_code}")
async def access_url(
    short_code: str,
    service: UrlShortenerService = Depends(get_url_service),
    db=Depends(get_db),
):
    url = service.record_click(short_code, db)
    if url is None:
        raise HTTPException(status_code=404, detail="Short code not found")

    return RedirectResponse(url=url)


@router.put("/api/urls/{short_code}")
async def update_url(
    short_code: str,
    email: str,
    new_original_url: str,
    service=Depends(get_url_service),
    db=Depends(get_db),
):
    try:
        url = service.update_url(email, short_code, new_original_url, db)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(404, str(e))
    return SuccessResponse(
        status_code=200,
        message="URL updated",
        data={"short_code": url.short_code, "original_url": url.original_url},
    )


@router.delete("/api/urls/{short_code}")
async def delete_url(
    short_code: str, email: str, service=Depends(get_url_service), db=Depends(get_db)
):
    try:
        service.delete_url(email, short_code, db)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(404, str(e))
    return SuccessResponse(status_code=200, message="Deleted", data=None)


@router.get("/api/urls")
async def list_my_urls(
    email: str,
    service: UrlShortenerService = Depends(get_url_service),
    db=Depends(get_db),
):
    try:
        urls = service.list_my_urls(email, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return SuccessResponse(
        status_code=200,
        message="URLs retrieved",
        data=[
            {
                "short_code": u.short_code,
                "original_url": u.original_url,
                "tags": [t.name for t in u.tags],
            }
            for u in urls
        ],
    )


@router.get("/api/urls/{short_code}")
async def get_url_details(
    short_code: str,
    email: str,
    service: UrlShortenerService = Depends(get_url_service),
    db=Depends(get_db),
):
    try:
        url = service.get_url_details(email, short_code, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return SuccessResponse(
        status_code=200,
        message="URL details retrieved",
        data={
            "short_code": url.short_code,
            "original_url": url.original_url,
            "custom_alias": url.custom_alias,
            "click_count": url.click_count,
            "tags": [t.name for t in url.tags],
        },
    )
