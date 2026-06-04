"""Learning repositories."""

from __future__ import annotations

import uuid

from sqlalchemy import Select

from app.core.database.repository import TenantRepository
from app.modules.learning.models import Lesson, LessonProgress


class LessonRepository(TenantRepository[Lesson]):
    model = Lesson

    def for_course(self, course_id: uuid.UUID) -> Select:
        return (
            self._select().where(Lesson.course_id == course_id).order_by(Lesson.order_index.asc())
        )


class LessonProgressRepository(TenantRepository[LessonProgress]):
    model = LessonProgress

    async def get_for_user_lesson(
        self, user_id: uuid.UUID, lesson_id: uuid.UUID
    ) -> LessonProgress | None:
        stmt = self._select().where(
            LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def for_user(self, user_id: uuid.UUID) -> Select:
        return self._select().where(LessonProgress.user_id == user_id)
