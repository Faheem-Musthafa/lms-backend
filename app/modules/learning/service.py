"""Learning service — lessons listing, progress tracking, completion."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import context as ctx
from app.core.events import event_bus
from app.modules.learning.events import LessonCompletedEvent
from app.modules.learning.models import Lesson, LessonProgress, ProgressStatus
from app.modules.learning.repository import (
    LessonProgressRepository,
    LessonRepository,
)
from app.shared.schemas import PageParams


class LearningService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.lessons = LessonRepository(session)
        self.progress = LessonProgressRepository(session)

    async def list_lessons(self, course_id: uuid.UUID) -> list[Lesson]:
        stmt = self.lessons.for_course(course_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def complete_lesson(
        self, lesson_id: uuid.UUID, user_id: uuid.UUID, *, last_position_seconds: int = 0
    ) -> LessonProgress:
        tenant_id = ctx.require_tenant_id()
        lesson = await self.lessons.get_or_404(lesson_id)

        progress = await self.progress.get_for_user_lesson(user_id, lesson_id)
        now = datetime.now(UTC)
        if progress is None:
            progress = await self.progress.create(
                lesson_id=lesson_id,
                course_id=lesson.course_id,
                user_id=user_id,
                status=ProgressStatus.completed,
                last_position_seconds=last_position_seconds,
                completed_at=now,
            )
        else:
            progress.status = ProgressStatus.completed
            progress.completed_at = now
            progress.last_position_seconds = last_position_seconds
            await self.session.flush()

        await event_bus.publish(
            LessonCompletedEvent(
                tenant_id=tenant_id,
                user_id=user_id,
                lesson_id=lesson_id,
                course_id=lesson.course_id,
            )
        )
        return progress

    async def my_progress(
        self, user_id: uuid.UUID, params: PageParams
    ) -> tuple[list[LessonProgress], int]:
        stmt = self.progress.for_user(user_id)
        total = (
            await self.session.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        rows = list(
            (await self.session.execute(stmt.offset(params.offset).limit(params.limit)))
            .scalars()
            .all()
        )
        return rows, total
