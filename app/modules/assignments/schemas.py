"""Assignment schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.assignments.models import (
    AssignmentType,
    QuestionType,
    SubmissionStatus,
)
from app.shared.schemas import ORMModel, PageParams


class AssignmentFilter(PageParams):
    course_id: uuid.UUID | None = None
    type: AssignmentType | None = None


class QuizAnswerOut(ORMModel):
    id: uuid.UUID
    text: str
    # is_correct intentionally omitted from learner-facing output


class QuizQuestionOut(ORMModel):
    id: uuid.UUID
    text: str
    type: QuestionType
    points: Decimal
    order_index: int
    answers: list[QuizAnswerOut] = []


class QuizOut(ORMModel):
    id: uuid.UUID
    time_limit_seconds: int
    questions: list[QuizQuestionOut] = []


class AssignmentOut(ORMModel):
    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    description: str | None
    type: AssignmentType
    max_points: Decimal
    pass_points: Decimal
    due_at: datetime | None
    is_published: bool
    quiz: QuizOut | None = None


class SubmitRequest(BaseModel):
    content: str | None = None
    file_url: str | None = None
    # quiz answers: {question_id: [answer_id, ...]}
    answers: dict[uuid.UUID, list[uuid.UUID]] | None = None


class GradeRequest(BaseModel):
    points: Decimal = Field(ge=0)
    feedback: str | None = None


class GradeOut(ORMModel):
    id: uuid.UUID
    submission_id: uuid.UUID
    assignment_id: uuid.UUID
    user_id: uuid.UUID
    points: Decimal
    max_points: Decimal
    feedback: str | None
    is_auto: bool
    graded_at: datetime


class SubmissionOut(ORMModel):
    id: uuid.UUID
    assignment_id: uuid.UUID
    user_id: uuid.UUID
    content: str | None
    file_url: str | None
    status: SubmissionStatus
    submitted_at: datetime
    grade: GradeOut | None = None
