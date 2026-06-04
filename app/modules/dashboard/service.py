"""Dashboard service — the CQRS *read side*.

By design this is the one place that reads across module tables: dashboards are
aggregations of other modules' data. The write sides stay isolated; this
reporting layer composes their read models. (In a microservice split this
becomes a dedicated read service fed by the same domain events.)
"""

from __future__ import annotations

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit.models import AuditLog
from app.modules.assignments.models import Assignment, Submission
from app.modules.courses.models import CourseEnrollment, EnrollmentStatus
from app.modules.dashboard.schemas import ActivityItem, DashboardOut
from app.modules.learning.models import LessonProgress, ProgressStatus


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _scalar(self, stmt) -> int:
        return (await self.session.execute(stmt)).scalar_one() or 0

    async def for_user(self, user_id: uuid.UUID) -> DashboardOut:
        enrolled = await self._scalar(
            select(func.count())
            .select_from(CourseEnrollment)
            .where(
                CourseEnrollment.user_id == user_id,
                CourseEnrollment.status != EnrollmentStatus.cancelled,
            )
        )

        completed_lessons = await self._scalar(
            select(func.count())
            .select_from(LessonProgress)
            .where(
                LessonProgress.user_id == user_id,
                LessonProgress.status == ProgressStatus.completed,
            )
        )

        submissions = await self._scalar(
            select(func.count()).select_from(Submission).where(Submission.user_id == user_id)
        )

        # pending = published assignments in enrolled courses with no submission by user
        enrolled_courses = select(CourseEnrollment.course_id).where(
            CourseEnrollment.user_id == user_id,
            CourseEnrollment.status == EnrollmentStatus.active,
        )
        pending = await self._scalar(
            select(func.count())
            .select_from(Assignment)
            .outerjoin(
                Submission,
                and_(
                    Submission.assignment_id == Assignment.id,
                    Submission.user_id == user_id,
                ),
            )
            .where(
                Assignment.is_published.is_(True),
                Assignment.course_id.in_(enrolled_courses),
                Submission.id.is_(None),
                Assignment.deleted_at.is_(None),
            )
        )

        activity_rows = (
            (
                await self.session.execute(
                    select(AuditLog)
                    .where(AuditLog.user_id == user_id)
                    .order_by(AuditLog.created_at.desc())
                    .limit(10)
                )
            )
            .scalars()
            .all()
        )

        return DashboardOut(
            enrolled_courses=enrolled,
            completed_lessons=completed_lessons,
            pending_assignments=pending,
            submissions=submissions,
            recent_activity=[
                ActivityItem(
                    action=a.action,
                    resource=a.resource,
                    resource_id=a.resource_id,
                    created_at=a.created_at,
                )
                for a in activity_rows
            ],
        )
