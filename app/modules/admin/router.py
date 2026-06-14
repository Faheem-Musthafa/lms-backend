"""Admin endpoints — mounted at /api/v1/admin (ADMIN module + RBAC gated)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.modules.admin.schemas import (
    AdminLessonCreate,
    AdminUserCreate,
    AdminUserUpdate,
    ModuleToggle,
    ReportOut,
    TenantCreate,
    TenantModuleOut,
    TenantOut,
)
from app.modules.admin.service import (
    AdminUserService,
    ReportService,
    TenantAdminService,
)
from app.modules.auth.dependencies import CurrentUser, DbSession, require_permission
from app.modules.auth.schemas import UserOut
from app.modules.courses.schemas import CourseCreate, CourseFilter, CourseOut, CourseUpdate
from app.modules.courses.service import CourseService
from app.modules.learning.schemas import LessonOut
from app.shared.schemas import Message, Page, PageParams

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Course management ─────────────────────────────────────────────────────────
@router.get(
    "/courses",
    response_model=Page[CourseOut],
    dependencies=[require_permission("course:read")],
)
async def list_admin_courses(
    session: DbSession, _: CurrentUser, filters: Annotated[CourseFilter, Depends()]
) -> Page[CourseOut]:
    items, total = await CourseService(session).list_courses(filters, published_only=False)
    return Page.create([CourseOut.model_validate(c) for c in items], total, filters)


@router.get(
    "/courses/{course_id}",
    response_model=CourseOut,
    dependencies=[require_permission("course:read")],
)
async def get_admin_course(course_id: uuid.UUID, session: DbSession, _: CurrentUser) -> CourseOut:
    course = await CourseService(session).get_course(course_id, published_only=False)
    return CourseOut.model_validate(course)


@router.post(
    "/courses",
    response_model=CourseOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_permission("course:create")],
)
async def create_course(data: CourseCreate, session: DbSession, _: CurrentUser) -> CourseOut:
    course = await CourseService(session).create_course(data)
    return CourseOut.model_validate(course)


@router.put(
    "/courses/{course_id}",
    response_model=CourseOut,
    dependencies=[require_permission("course:update")],
)
async def update_course(
    course_id: uuid.UUID, data: CourseUpdate, session: DbSession, _: CurrentUser
) -> CourseOut:
    course = await CourseService(session).update_course(course_id, data)
    return CourseOut.model_validate(course)


@router.delete(
    "/courses/{course_id}",
    response_model=Message,
    dependencies=[require_permission("course:delete")],
)
async def delete_course(course_id: uuid.UUID, session: DbSession, _: CurrentUser) -> Message:
    await CourseService(session).delete_course(course_id)
    return Message(message="Course deleted")


@router.get(
    "/courses/{course_id}/lessons",
    response_model=list[LessonOut],
    dependencies=[require_permission("course:read")],
)
async def get_admin_course_lessons(course_id: uuid.UUID, session: DbSession, _: CurrentUser) -> list[LessonOut]:
    from app.modules.learning.service import LearningService
    lessons = await LearningService(session).list_lessons(course_id)
    return [LessonOut.model_validate(lo) for lo in lessons]


@router.post(
    "/courses/{course_id}/lessons",
    response_model=LessonOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_permission("course:update")],
)
async def create_admin_course_lesson(
    course_id: uuid.UUID, data: AdminLessonCreate, session: DbSession, _: CurrentUser
) -> LessonOut:
    from app.modules.admin.service import AdminLessonService
    lesson = await AdminLessonService(session).create_lesson(course_id, data)
    return LessonOut.model_validate(lesson)


# ── User management ───────────────────────────────────────────────────────────
@router.get(
    "/users",
    response_model=Page[UserOut],
    dependencies=[require_permission("user:read")],
)
async def list_users(
    session: DbSession, _: CurrentUser, params: Annotated[PageParams, Depends()]
) -> Page[UserOut]:
    users, total = await AdminUserService(session).list_users(params)
    return Page.create([UserOut.model_validate(u) for u in users], total, params)


@router.post(
    "/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_permission("user:create")],
)
async def create_user(data: AdminUserCreate, session: DbSession, _: CurrentUser) -> UserOut:
    user = await AdminUserService(session).create_user(data)
    return UserOut.model_validate(user)


@router.put(
    "/users/{user_id}",
    response_model=UserOut,
    dependencies=[require_permission("user:update")],
)
async def update_user(
    user_id: uuid.UUID, data: AdminUserUpdate, session: DbSession, _: CurrentUser
) -> UserOut:
    user = await AdminUserService(session).update_user(user_id, data)
    return UserOut.model_validate(user)


# ── Reports ───────────────────────────────────────────────────────────────────
@router.get(
    "/reports",
    response_model=ReportOut,
    dependencies=[require_permission("report:read")],
)
async def reports(session: DbSession, _: CurrentUser) -> ReportOut:
    return await ReportService(session).tenant_report()


# ── Tenant + module licensing (super admin / tenant:manage) ────────────────────
@router.post(
    "/tenants",
    response_model=TenantOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_permission("tenant:manage")],
)
async def create_tenant(data: TenantCreate, _: CurrentUser) -> TenantOut:
    tenant = await TenantAdminService().create_tenant(data)
    return TenantOut.model_validate(tenant, from_attributes=True)


@router.get(
    "/tenants",
    response_model=list[TenantOut],
    dependencies=[require_permission("tenant:manage")],
)
async def list_tenants(_: CurrentUser) -> list[TenantOut]:
    tenants = await TenantAdminService().list_tenants()
    return [TenantOut.model_validate(t, from_attributes=True) for t in tenants]


@router.get(
    "/tenants/{tenant_id}/modules",
    response_model=list[TenantModuleOut],
    dependencies=[require_permission("tenant:manage")],
)
async def list_tenant_modules(tenant_id: uuid.UUID, _: CurrentUser) -> list[TenantModuleOut]:
    return await TenantAdminService().list_modules(tenant_id)


@router.put(
    "/tenants/{tenant_id}/modules",
    response_model=Message,
    dependencies=[require_permission("tenant:manage")],
)
async def toggle_tenant_module(tenant_id: uuid.UUID, data: ModuleToggle, _: CurrentUser) -> Message:
    await TenantAdminService().set_module(tenant_id, data.code, enabled=data.enabled)
    state = "enabled" if data.enabled else "disabled"
    return Message(message=f"Module {data.code.value} {state} for tenant")
