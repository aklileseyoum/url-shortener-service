from fastapi import APIRouter, Depends, HTTPException, Request

from src.url_shortener_service.database import get_db
from src.url_shortener_service.rate_limit import limiter
from src.url_shortener_service.requests import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
)
from src.url_shortener_service.responses import SuccessResponse
from src.url_shortener_service.services.user_services import (
    UserService,
    get_user_service,
)

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


@router.post("/api/login")
@limiter.limit("3/minute")
def login(
    request: Request,
    data: LoginRequest,
    user_service: UserService = Depends(get_user_service),
    db=Depends(get_db),
):
    try:
        access_token: str
        refresh_token: str
        access_token, refresh_token = user_service.login_user(
            data.email, data.password, db
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/api/refresh")
def refresh(
    data: RefreshRequest,
    user_service: UserService = Depends(get_user_service),
    db=Depends(get_db),
):
    try:
        access_token, refresh_token = user_service.refresh_tokens(
            data.refresh_token, db
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
