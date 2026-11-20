from fastapi import APIRouter, Depends, HTTPException

from src.url_shortener_service.auth import CurrentUser
from src.url_shortener_service.database import get_db
from src.url_shortener_service.responses import SuccessResponse
from src.url_shortener_service.services.tag_services import (
    TagService,
    get_tag_service,
)

router = APIRouter()


@router.post("/api/tags", status_code=201)
async def create_tag(
    name: str,
    service: TagService = Depends(get_tag_service),
    db=Depends(get_db),
):
    try:
        tag = await service.create_tag(name, db)
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
    current_user: CurrentUser,
    tag_name: str,
    service: TagService = Depends(get_tag_service),
    db=Depends(get_db),
):
    try:
        url = await service.attach_tag(current_user.id, short_code, tag_name, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SuccessResponse(
        status_code=200,
        message="Tag attached",
        data={
            "short_code": url.short_code,
            "custom_alias": url.custom_alias,
            "original_url": url.original_url,
            "tags": [t.name for t in url.tags],
        },
    )
