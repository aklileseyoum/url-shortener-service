from fastapi import FastAPI

from src.url_shortener_service.routers import urls


def create_app() -> FastAPI:
    app = FastAPI(title="URL Shortener")
    app.include_router(urls.router, tags=["urls"])
    return app


app = create_app()
