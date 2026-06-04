"""Course catalog service — listing, details, enrollment, admin CRUD."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import context as ctx
from app.core.events import event_bus
from app.modules.courses.events import CourseCreatedEvent, CourseEnrolledEvent
from app.modules.courses.models import (
    Course,
    CourseEnrollment,
    CourseStatus,
    EnrollmentStatus,
)
from app.modules.courses.repository import (
    CourseRepository,
    EnrollmentRepository,
)
from app.modules.courses.schemas import CourseCreate, CourseFilter, CourseUpdate
from app.shared.exceptions import ConflictError, NotFoundError, ValidationError


class CourseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.courses = CourseRepository(session)
        self.enrollments = EnrollmentRepository(session)

    # ── reads ──────────────────────────────────────────────────────────────
    async def list_courses(
        self, f: CourseFilter, *, published_only: bool = True
    ) -> tuple[list[Course], int]:
        stmt = self.courses.filtered(f, published_only=published_only)
        total = (
            await self.session.execute(
                select(func.count()).select_from(stmt.order_by(None).subquery())
            )
        ).scalar_one()
        stmt = self.courses._apply_sort(stmt, f.sort or "-created_at")
        stmt = stmt.offset(f.offset).limit(f.limit)
        items = list((await self.session.execute(stmt)).scalars().all())
        return items, total

    async def get_course(self, course_id: uuid.UUID, *, published_only: bool = True) -> Course:
        course = await self.courses.get_or_404(course_id)
        if published_only and course.status != CourseStatus.published:
            raise NotFoundError("Course not found")
        return course

    # ── enrollment ───────────────────────────────────────────────────────
    async def enroll(self, course_id: uuid.UUID, user_id: uuid.UUID) -> CourseEnrollment:
        tenant_id = ctx.require_tenant_id()
        course = await self.courses.get_or_404(course_id)
        if course.status != CourseStatus.published:
            raise ValidationError("Course is not open for enrollment")

        existing = await self.enrollments.get_for_user_course(user_id, course_id)
        if existing and existing.status != EnrollmentStatus.cancelled:
            raise ConflictError("Already enrolled in this course")

        enrollment = await self.enrollments.create(
            course_id=course_id,
            user_id=user_id,
            status=EnrollmentStatus.active,
            enrolled_at=datetime.now(UTC),
        )
        course.enrollment_count += 1
        await self.session.flush()

        await event_bus.publish(
            CourseEnrolledEvent(
                tenant_id=tenant_id,
                user_id=user_id,
                course_id=course_id,
                enrollment_id=enrollment.id,
            )
        )
        return enrollment

    # ── admin CRUD ───────────────────────────────────────────────────────
    async def create_course(self, data: CourseCreate) -> Course:
        tenant_id = ctx.require_tenant_id()
        if await self.courses.exists(slug=data.slug):
            raise ConflictError(f"Course slug '{data.slug}' already exists")
        course = await self.courses.create(**data.model_dump())
        await event_bus.publish(
            CourseCreatedEvent(
                tenant_id=tenant_id,
                user_id=ctx.current_user_id(),
                course_id=course.id,
                title=course.title,
            )
        )
        return course

    async def update_course(self, course_id: uuid.UUID, data: CourseUpdate) -> Course:
        course = await self.courses.get_or_404(course_id)
        changes = data.model_dump(exclude_unset=True)
        if changes.get("status") == CourseStatus.published and course.published_at is None:
            course.published_at = datetime.now(UTC)
        for k, v in changes.items():
            setattr(course, k, v)
        await self.session.flush()
        return course

    async def delete_course(self, course_id: uuid.UUID) -> None:
        course = await self.courses.get_or_404(course_id)
        await self.courses.delete(course)  # soft delete
