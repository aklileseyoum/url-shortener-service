import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.url_shortener_service.routers import urls
from src.url_shortener_service.settings import settings


def create_app() -> FastAPI:
    app = FastAPI(title="URL Shortener")
    app.include_router(urls.router, tags=["urls"])

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        print(
            f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s"
        )
        return response

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        if settings.environment == "development":
            detail = str(exc)
        else:
            detail = "An unexpected error occurred."
        return JSONResponse(status_code=500, content={"detail": detail})

    return app


app = create_app()
