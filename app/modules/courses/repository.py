"""Course catalog repositories."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, or_

from app.core.database.repository import TenantRepository
from app.modules.courses.models import (
    Category,
    Course,
    CourseEnrollment,
    CourseStatus,
)
from app.modules.courses.schemas import CourseFilter


class CategoryRepository(TenantRepository[Category]):
    model = Category


class CourseRepository(TenantRepository[Course]):
    model = Course

    def _apply_search(self, stmt: Select, term: str) -> Select:
        like = f"%{term}%"
        return stmt.where(or_(Course.title.ilike(like), Course.summary.ilike(like)))

    def filtered(self, f: CourseFilter, *, published_only: bool) -> Select:
        stmt = self._select()
        if f.search:
            stmt = self._apply_search(stmt, f.search)
        if f.category_id:
            stmt = stmt.where(Course.category_id == f.category_id)
        if f.level:
            stmt = stmt.where(Course.level == f.level)
        if f.is_free is not None:
            stmt = stmt.where(Course.is_free == f.is_free)
        if published_only:
            stmt = stmt.where(Course.status == CourseStatus.published)
        elif f.status:
            stmt = stmt.where(Course.status == f.status)
        return stmt


class EnrollmentRepository(TenantRepository[CourseEnrollment]):
    model = CourseEnrollment

    async def get_for_user_course(
        self, user_id: uuid.UUID, course_id: uuid.UUID
    ) -> CourseEnrollment | None:
        stmt = self._select().where(
            CourseEnrollment.user_id == user_id,
            CourseEnrollment.course_id == course_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def for_user(self, user_id: uuid.UUID) -> Select:
        return self._select().where(CourseEnrollment.user_id == user_id)
