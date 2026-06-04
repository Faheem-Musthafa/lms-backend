"""Module licensing guard: per-tenant feature activation."""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import auth_headers


async def test_unlicensed_module_returns_403(client: AsyncClient, abc_student_token: str) -> None:
    # abc-academy is NOT licensed for ASSIGNMENTS
    resp = await client.get("/api/v1/assignments", headers=auth_headers(abc_student_token))
    assert resp.status_code == 403
    assert resp.json()["code"] == "module_not_enabled"
    assert resp.json()["error"] == "Module not enabled for tenant"


async def test_licensed_module_allowed(client: AsyncClient, student_token: str) -> None:
    # full-lms IS licensed for ASSIGNMENTS
    resp = await client.get("/api/v1/assignments", headers=auth_headers(student_token))
    assert resp.status_code == 200


async def test_licensed_courses_for_both(client: AsyncClient, abc_student_token: str) -> None:
    # COURSES is licensed for abc-academy
    resp = await client.get("/api/v1/courses", headers=auth_headers(abc_student_token))
    assert resp.status_code == 200
