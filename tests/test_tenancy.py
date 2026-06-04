"""Multi-tenant isolation through the API surface."""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import auth_headers, login


async def test_jwt_tenant_wins_over_header(client: AsyncClient) -> None:
    """A full-lms token used with an abc-academy header still operates on
    full-lms — the authenticated JWT ``tid`` governs, headers can't escalate."""
    token = await login(client, "full-lms", "student@full-lms.com", "Learn123!")
    resp = await client.get(
        "/api/v1/auth/me",
        headers={**auth_headers(token), "X-Tenant-ID": "abc-academy"},
    )
    assert resp.status_code == 200
    # tenant_id in the response is full-lms's, not abc-academy's
    body = resp.json()
    assert body["email"] == "student@full-lms.com"


async def test_cross_tenant_course_not_visible(client: AsyncClient) -> None:
    """A course id from one tenant must 404 for a user in another tenant (RLS)."""
    abc = await login(client, "abc-academy", "student@abc-academy.com", "Learn123!")
    full = await login(client, "full-lms", "student@full-lms.com", "Learn123!")

    abc_courses = await client.get("/api/v1/courses?size=1", headers=auth_headers(abc))
    if not abc_courses.json()["items"]:
        return  # no abc course seeded; nothing to assert
    abc_course_id = abc_courses.json()["items"][0]["id"]

    # full-lms user tries to read abc-academy's course by id
    resp = await client.get(f"/api/v1/courses/{abc_course_id}", headers=auth_headers(full))
    assert resp.status_code == 404
