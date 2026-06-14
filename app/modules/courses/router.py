"""Course catalog endpoints — mounted at /api/v1/courses (learner-facing)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.modules.auth.dependencies import CurrentUser, DbSession, require_permission
from app.modules.courses.schemas import (
    CourseDetailOut,
    CourseFilter,
    CourseOut,
    EnrollmentOut,
)
from app.modules.courses.service import CourseService
from app.shared.schemas import Page

router = APIRouter(prefix="/courses", tags=["Course Catalog"])


def get_course_service(session: DbSession) -> CourseService:
    return CourseService(session)


CourseSvc = Annotated[CourseService, Depends(get_course_service)]


@router.get("", response_model=Page[CourseOut])
@router.get("/", response_model=Page[CourseOut], include_in_schema=False)
async def list_courses(
    filters: Annotated[CourseFilter, Depends()],
    svc: CourseSvc,
    _: CurrentUser,
) -> Page[CourseOut]:
    items, total = await svc.list_courses(filters, published_only=True)
    return Page.create([CourseOut.model_validate(c) for c in items], total, filters)


@router.get("/{course_id}", response_model=CourseDetailOut)
async def get_course(course_id: uuid.UUID, svc: CourseSvc, _: CurrentUser) -> CourseDetailOut:
    course = await svc.get_course(course_id, published_only=True)
    return CourseDetailOut.model_validate(course)


@router.post(
    "/{course_id}/enroll",
    response_model=EnrollmentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_permission("course:enroll")],
)
async def enroll(course_id: uuid.UUID, svc: CourseSvc, user: CurrentUser) -> EnrollmentOut:
    enrollment = await svc.enroll(course_id, user.id)
    return EnrollmentOut.model_validate(enrollment)
