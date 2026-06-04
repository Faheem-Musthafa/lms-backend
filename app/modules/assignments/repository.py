"""Assignment repositories."""

from __future__ import annotations

import uuid

from sqlalchemy import Select

from app.core.database.repository import TenantRepository
from app.modules.assignments.models import Assignment, Grade, Submission
from app.modules.assignments.schemas import AssignmentFilter


class AssignmentRepository(TenantRepository[Assignment]):
    model = Assignment

    def filtered(self, f: AssignmentFilter, *, published_only: bool) -> Select:
        stmt = self._select()
        if f.course_id:
            stmt = stmt.where(Assignment.course_id == f.course_id)
        if f.type:
            stmt = stmt.where(Assignment.type == f.type)
        if published_only:
            stmt = stmt.where(Assignment.is_published.is_(True))
        return stmt.order_by(Assignment.created_at.desc())


class SubmissionRepository(TenantRepository[Submission]):
    model = Submission


class GradeRepository(TenantRepository[Grade]):
    model = Grade

    async def get_by_submission(self, submission_id: uuid.UUID) -> Grade | None:
        stmt = self._select().where(Grade.submission_id == submission_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def for_user(self, user_id: uuid.UUID) -> Select:
        return self._select().where(Grade.user_id == user_id).order_by(Grade.graded_at.desc())
