from fastapi import APIRouter, Depends, HTTPException

from src.url_shortener_service.database import get_db
from src.url_shortener_service.responses import SuccessResponse
from src.url_shortener_service.services import (
    UrlShortenerService,
    get_url_service,
)

router = APIRouter()


@router.post("/api/register", status_code=201)
def register_user(
    email: str,
    service: UrlShortenerService = Depends(get_url_service),
    db=Depends(get_db),
):
    try:
        user = service.register_user(email, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SuccessResponse(
        status_code=201,
        message="User registered successfully",
        data={"user_id": user.id, "email": user.email},
    )
