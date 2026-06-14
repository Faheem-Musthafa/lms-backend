"""Assignment service — submission, auto-grading, manual grading."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import context as ctx
from app.core.events import event_bus
from app.modules.assignments.events import (
    AssignmentSubmittedEvent,
    SubmissionGradedEvent,
)
from app.modules.assignments.models import (
    Assignment,
    AssignmentType,
    Grade,
    Submission,
    SubmissionStatus,
)
from app.modules.assignments.repository import (
    AssignmentRepository,
    GradeRepository,
    SubmissionRepository,
)
from app.modules.assignments.schemas import (
    AssignmentFilter,
    GradeRequest,
    SubmitRequest,
)
from app.shared.exceptions import ValidationError
from app.shared.schemas import PageParams


class AssignmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.assignments = AssignmentRepository(session)
        self.submissions = SubmissionRepository(session)
        self.grades = GradeRepository(session)

    async def list_assignments(
        self, f: AssignmentFilter, *, published_only: bool = True
    ) -> tuple[list[Assignment], int]:
        stmt = self.assignments.filtered(f, published_only=published_only)
        total = (
            await self.session.execute(
                select(func.count()).select_from(stmt.order_by(None).subquery())
            )
        ).scalar_one()
        rows = list(
            (await self.session.execute(stmt.offset(f.offset).limit(f.limit))).scalars().all()
        )
        return rows, total

    async def get_assignment(self, assignment_id: uuid.UUID) -> Assignment:
        return await self.assignments.get_or_404(assignment_id)

    # ── submission + grading ─────────────────────────────────────────────
    async def submit(
        self, assignment_id: uuid.UUID, user_id: uuid.UUID, data: SubmitRequest
    ) -> Submission:
        tenant_id = ctx.require_tenant_id()
        assignment = await self.assignments.get_or_404(assignment_id)
        if not assignment.is_published:
            raise ValidationError("Assignment is not open for submission")

        submission = await self.submissions.create(
            assignment_id=assignment_id,
            user_id=user_id,
            content=data.content,
            file_url=data.file_url,
            answers={str(k): [str(a) for a in v] for k, v in (data.answers or {}).items()} or None,
            status=SubmissionStatus.submitted,
            submitted_at=datetime.now(UTC),
        )
        await event_bus.publish(
            AssignmentSubmittedEvent(
                tenant_id=tenant_id,
                user_id=user_id,
                assignment_id=assignment_id,
                submission_id=submission.id,
            )
        )

        if assignment.type == AssignmentType.quiz and assignment.quiz is not None:
            await self._auto_grade(assignment, submission, data.answers or {})

        # load the grade relationship for serialization (async-safe explicit load)
        await self.session.refresh(submission, ["grade"])
        return submission

    async def _auto_grade(
        self,
        assignment: Assignment,
        submission: Submission,
        answers: dict[uuid.UUID, list[uuid.UUID]],
    ) -> Grade:
        quiz = assignment.quiz
        assert quiz is not None
        earned = Decimal(0)
        possible = Decimal(0)
        for q in quiz.questions:
            possible += Decimal(q.points)
            correct = {a.id for a in q.answers if a.is_correct}
            selected = set(answers.get(q.id, []))
            if selected and selected == correct:
                earned += Decimal(q.points)

        max_pts = Decimal(assignment.max_points)
        scaled = (earned / possible * max_pts) if possible else Decimal(0)
        return await self._record_grade(
            submission, points=scaled, max_points=max_pts, is_auto=True, graded_by=None
        )

    async def grade_submission(
        self, submission_id: uuid.UUID, data: GradeRequest, grader_id: uuid.UUID
    ) -> Grade:
        submission = await self.submissions.get_or_404(submission_id)
        assignment = await self.assignments.get_or_404(submission.assignment_id)
        if data.points > Decimal(assignment.max_points):
            raise ValidationError("Points exceed assignment maximum")
        return await self._record_grade(
            submission,
            points=data.points,
            max_points=Decimal(assignment.max_points),
            is_auto=False,
            graded_by=grader_id,
            feedback=data.feedback,
        )

    async def _record_grade(
        self,
        submission: Submission,
        *,
        points: Decimal,
        max_points: Decimal,
        is_auto: bool,
        graded_by: uuid.UUID | None,
        feedback: str | None = None,
    ) -> Grade:
        tenant_id = ctx.require_tenant_id()
        now = datetime.now(UTC)
        grade = await self.grades.get_by_submission(submission.id)
        if grade is None:
            grade = Grade(
                tenant_id=tenant_id,
                submission_id=submission.id,
                assignment_id=submission.assignment_id,
                user_id=submission.user_id,
                points=points,
                max_points=max_points,
                is_auto=is_auto,
                graded_by=graded_by,
                feedback=feedback,
                graded_at=now,
            )
            self.session.add(grade)
        else:
            grade.points = points
            grade.feedback = feedback if feedback is not None else grade.feedback
            grade.is_auto = is_auto
            grade.graded_by = graded_by
            grade.graded_at = now
        submission.status = SubmissionStatus.graded
        await self.session.flush()

        await event_bus.publish(
            SubmissionGradedEvent(
                tenant_id=tenant_id,
                user_id=submission.user_id,
                submission_id=submission.id,
                points=float(points),
                is_auto=is_auto,
            )
        )
        return grade

    async def list_grades(self, user_id: uuid.UUID, params: PageParams) -> tuple[list[Grade], int]:
        stmt = self.grades.for_user(user_id)
        total = (
            await self.session.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        rows = list(
            (await self.session.execute(stmt.offset(params.offset).limit(params.limit)))
            .scalars()
            .all()
        )
        return rows, total

    async def list_submissions_for_assignment(self, assignment_id: uuid.UUID) -> list[Submission]:
        stmt = self.submissions._select().where(Submission.assignment_id == assignment_id).order_by(Submission.submitted_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())
