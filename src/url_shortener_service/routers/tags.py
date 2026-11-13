from fastapi import APIRouter, Depends, HTTPException

from src.url_shortener_service.database import get_db
from src.url_shortener_service.responses import SuccessResponse
from src.url_shortener_service.services import (
    UrlShortenerService,
    get_url_service,
)

router = APIRouter()


@router.post("/api/tags", status_code=201)
async def create_tag(
    name: str,
    service: UrlShortenerService = Depends(get_url_service),
    db=Depends(get_db),
):
    try:
        tag = service.create_tag(name, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SuccessResponse(
        status_code=201,
        message="Tag created",
        data={"id": tag.id, "name": tag.name},
    )


@router.post("/api/urls/{short_code}/tags")
async def attach_tag(
    short_code: str,
    email: str,
    tag_name: str,
    service: UrlShortenerService = Depends(get_url_service),
    db=Depends(get_db),
):
    try:
        url = service.attach_tag(email, short_code, tag_name, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SuccessResponse(
        status_code=200,
        message="Tag attached",
        data={"short_code": url.short_code, "tags": [t.name for t in url.tags]},
    )
