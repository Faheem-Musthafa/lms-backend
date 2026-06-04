"""RBAC: permission-gated endpoints."""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from tests.conftest import auth_headers, login


async def test_student_cannot_create_course(client: AsyncClient, student_token: str) -> None:
    resp = await client.post(
        "/api/v1/admin/courses",
        headers=auth_headers(student_token),
        json={"title": "Hacker Course", "slug": "hacker-course"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "permission_denied"


async def test_admin_can_create_course(client: AsyncClient) -> None:
    token = await login(client, "full-lms", "admin@full-lms.com", "Admin123!")
    slug = f"rbac-test-course-{uuid.uuid4().hex[:8]}"  # unique per run
    resp = await client.post(
        "/api/v1/admin/courses",
        headers=auth_headers(token),
        json={"title": "RBAC Test Course", "slug": slug},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["title"] == "RBAC Test Course"


async def test_student_can_enroll(client: AsyncClient, student_token: str) -> None:
    courses = await client.get("/api/v1/courses?size=1", headers=auth_headers(student_token))
    course_id = courses.json()["items"][0]["id"]
    resp = await client.post(
        f"/api/v1/courses/{course_id}/enroll", headers=auth_headers(student_token)
    )
    # 201 first time, 409 if already enrolled from a prior run — both prove the gate passed
    assert resp.status_code in (201, 409)
