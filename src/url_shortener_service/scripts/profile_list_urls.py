# scripts/profile_list_urls.py
import asyncio

import httpx

from src.url_shortener_service.auth import create_access_token
from src.url_shortener_service.main import create_app


async def main() -> None:
    app = create_app()
    token = create_access_token(5)
    headers = {"Authorization": f"Bearer {token}"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(50):
            response = await client.get("/api/urls", headers=headers)
        print(response.status_code)


asyncio.run(main())
