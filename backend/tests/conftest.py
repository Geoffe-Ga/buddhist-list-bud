import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.app.db import reset_client
from backend.app.main import app


@pytest_asyncio.fixture
async def client():
    reset_client()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    reset_client()
