from fastapi import APIRouter, Depends, HTTPException

from src.url_shortener_service.database import get_db
from src.url_shortener_service.requests import RegisterRequest
from src.url_shortener_service.responses import SuccessResponse
from src.url_shortener_service.user_services import UserService, get_user_service

router = APIRouter()


@router.post("/api/register", status_code=201)
def register_user(
    data: RegisterRequest,
    user_service: UserService = Depends(get_user_service),
    db=Depends(get_db),
):
    try:
        user = user_service.register_user(data.email, data.password, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SuccessResponse(
        status_code=201,
        message="User registered successfully",
        data={"user_id": user.id, "email": user.email},
    )
