"""Learning endpoints — mounted at /api/v1/learning.

Routes:
  GET  /courses/{course_id}/lessons   (under learning prefix)
  POST /lessons/{lesson_id}/complete
  GET  /progress
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import CurrentUser, DbSession, require_permission
from app.modules.learning.schemas import (
    CompleteLessonRequest,
    LessonOut,
    LessonProgressOut,
)
from app.modules.learning.service import LearningService
from app.shared.schemas import Page, PageParams

router = APIRouter(prefix="/learning", tags=["Learning"])


def get_learning_service(session: DbSession) -> LearningService:
    return LearningService(session)


LearnSvc = Annotated[LearningService, Depends(get_learning_service)]


@router.get(
    "/courses/{course_id}/lessons",
    response_model=list[LessonOut],
    dependencies=[require_permission("lesson:read")],
)
async def list_lessons(course_id: uuid.UUID, svc: LearnSvc, _: CurrentUser) -> list[LessonOut]:
    lessons = await svc.list_lessons(course_id)
    return [LessonOut.model_validate(lo) for lo in lessons]


@router.post("/lessons/{lesson_id}/complete", response_model=LessonProgressOut)
async def complete_lesson(
    lesson_id: uuid.UUID, data: CompleteLessonRequest, svc: LearnSvc, user: CurrentUser
) -> LessonProgressOut:
    progress = await svc.complete_lesson(
        lesson_id, user.id, last_position_seconds=data.last_position_seconds
    )
    return LessonProgressOut.model_validate(progress)


@router.get(
    "/progress",
    response_model=Page[LessonProgressOut],
    dependencies=[require_permission("progress:read")],
)
async def my_progress(
    svc: LearnSvc, user: CurrentUser, params: Annotated[PageParams, Depends()]
) -> Page[LessonProgressOut]:
    rows, total = await svc.my_progress(user.id, params)
    return Page.create([LessonProgressOut.model_validate(r) for r in rows], total, params)
