from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import HttpUrl

from src.url_shortener_service.auth import CurrentUser
from src.url_shortener_service.database import get_db
from src.url_shortener_service.queries import count_active_urls_for_user
from src.url_shortener_service.responses import SuccessResponse
from src.url_shortener_service.services.url_services import (
    UrlShortenerService,
    get_url_service,
)

router = APIRouter()


@router.post("/api/urls", status_code=201)
async def shorten_url(
    current_user: CurrentUser,
    url: HttpUrl,
    service: UrlShortenerService = Depends(get_url_service),
    db=Depends(get_db),
    custom_alias: str | None = None,
):
    if custom_alias and not current_user.is_premium:
        raise HTTPException(
            status_code=403, detail="Custom aliases are a Premium feature"
        )

    if (
        not current_user.is_premium
        and count_active_urls_for_user(current_user.id, db) >= 10
    ):
        raise HTTPException(
            status_code=403, detail="Free tier is limited to 10 active URLs"
        )

    try:
        new_url = service.save_to_db(current_user.id, str(url), db, custom_alias)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SuccessResponse(
        status_code=201,
        message="It was successful",
        data={
            "short_code": new_url.short_code,
            "custom_alias": new_url.custom_alias,
            "original_url": new_url.original_url,
        },
    )


@router.get("/{short_code}")
async def access_url(
    short_code: str,
    service: UrlShortenerService = Depends(get_url_service),
    db=Depends(get_db),
):
    url = service.record_click(short_code, db)
    if url is None:
        raise HTTPException(
            status_code=404, detail="Short code or custom alias not found"
        )

    return RedirectResponse(url=url)


@router.put("/api/urls/{short_code}")
async def update_url(
    short_code: str,
    current_user: CurrentUser,
    new_original_url: str,
    service=Depends(get_url_service),
    db=Depends(get_db),
):
    try:
        url = service.update_url(current_user.id, short_code, new_original_url, db)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(404, str(e))
    return SuccessResponse(
        status_code=200,
        message="URL updated",
        data={
            "short_code": url.short_code,
            "custom_alias": url.custom_alias,
            "original_url": url.original_url,
        },
    )


@router.delete("/api/urls/{short_code}")
async def delete_url(
    short_code: str,
    current_user: CurrentUser,
    service=Depends(get_url_service),
    db=Depends(get_db),
):
    try:
        service.delete_url(current_user.id, short_code, db)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(404, str(e))
    return SuccessResponse(status_code=200, message="Deleted", data=None)


@router.get("/api/urls")
async def list_my_urls(
    current_user: CurrentUser,
    service: UrlShortenerService = Depends(get_url_service),
    db=Depends(get_db),
):
    try:
        urls = service.list_my_urls(current_user.id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return SuccessResponse(
        status_code=200,
        message="URLs retrieved",
        data=[
            {
                "short_code": u.short_code,
                "custom_alias": u.custom_alias,
                "original_url": u.original_url,
                "tags": [t.name for t in u.tags],
            }
            for u in urls
        ],
    )


@router.get("/api/urls/{short_code}")
async def get_url_details(
    short_code: str,
    current_user: CurrentUser,
    service: UrlShortenerService = Depends(get_url_service),
    db=Depends(get_db),
):
    try:
        url = service.get_url_details(current_user.id, short_code, db)
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
