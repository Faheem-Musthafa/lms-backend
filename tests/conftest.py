"""Pytest fixtures.

Integration tests run the real app in-process (httpx ASGITransport) against a
Postgres + Redis backend (the docker-compose stack, or whatever DATABASE_URL /
REDIS_URL point to). The session fixture migrates + seeds once.
"""

from __future__ import annotations

import os

# Ensure env defaults are set *before* importing the app/settings.
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-bytes-long!!")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture(autouse=True)
async def _reset_loop_bound_clients():
    """The async engine + redis client bind to the running event loop. Each
    test gets a fresh loop, so dispose them after every test to avoid reusing
    connections bound to a closed loop."""
    yield
    from app.core.cache import close_redis
    from app.core.database.session import engine

    await engine.dispose()
    await close_redis()


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def login(client: AsyncClient, tenant: str, email: str, password: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        headers={"X-Tenant-ID": tenant},
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def student_token(client: AsyncClient) -> str:
    return await login(client, "full-lms", "student@full-lms.com", "Learn123!")


@pytest_asyncio.fixture
async def abc_student_token(client: AsyncClient) -> str:
    return await login(client, "abc-academy", "student@abc-academy.com", "Learn123!")
