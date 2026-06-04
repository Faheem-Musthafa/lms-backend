"""Auth flow: login, me, refresh, bad credentials."""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import auth_headers, login


async def test_login_and_me(client: AsyncClient) -> None:
    token = await login(client, "full-lms", "student@full-lms.com", "Learn123!")
    resp = await client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "student@full-lms.com"
    assert "course:read" in body["permissions"]
    assert {r["code"] for r in body["roles"]} == {"student"}


async def test_login_wrong_password(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        headers={"X-Tenant-ID": "full-lms"},
        json={"email": "student@full-lms.com", "password": "wrong"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "unauthenticated"


async def test_refresh_rotates(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        headers={"X-Tenant-ID": "full-lms"},
        json={"email": "student@full-lms.com", "password": "Learn123!"},
    )
    refresh = resp.json()["refresh_token"]
    r2 = await client.post(
        "/api/v1/auth/refresh",
        headers={"X-Tenant-ID": "full-lms"},
        json={"refresh_token": refresh},
    )
    assert r2.status_code == 200
    assert r2.json()["access_token"]

    # old refresh token is now revoked (rotation)
    r3 = await client.post(
        "/api/v1/auth/refresh",
        headers={"X-Tenant-ID": "full-lms"},
        json={"refresh_token": refresh},
    )
    assert r3.status_code == 401


async def test_unauthenticated_rejected(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
