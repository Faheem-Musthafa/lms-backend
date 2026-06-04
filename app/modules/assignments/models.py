"""Assignment models: Assignment, Submission, Quiz, QuizQuestion, QuizAnswer, Grade."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import (
    Base,
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
)


class AssignmentType(str, enum.Enum):
    assignment = "assignment"
    quiz = "quiz"


class SubmissionStatus(str, enum.Enum):
    submitted = "submitted"
    graded = "graded"
    returned = "returned"


class QuestionType(str, enum.Enum):
    single = "single"  # one correct answer
    multiple = "multiple"  # multiple correct answers
    boolean = "boolean"  # true/false


class Assignment(UUIDMixin, TenantMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "assignments"

    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[AssignmentType] = mapped_column(
        Enum(AssignmentType, name="assignment_type"),
        nullable=False,
        default=AssignmentType.assignment,
    )
    max_points: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=100)
    pass_points: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=50)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    quiz: Mapped[Quiz | None] = relationship(
        back_populates="assignment", uselist=False, lazy="selectin"
    )


class Quiz(UUIDMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "quizzes"

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    time_limit_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    assignment: Mapped[Assignment] = relationship(back_populates="quiz")
    questions: Mapped[list[QuizQuestion]] = relationship(
        back_populates="quiz", lazy="selectin", order_by="QuizQuestion.order_index"
    )


class QuizQuestion(UUIDMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "quiz_questions"

    quiz_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type"), nullable=False, default=QuestionType.single
    )
    points: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=1)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    quiz: Mapped[Quiz] = relationship(back_populates="questions")
    answers: Mapped[list[QuizAnswer]] = relationship(back_populates="question", lazy="selectin")


class QuizAnswer(UUIDMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "quiz_answers"

    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    question: Mapped[QuizQuestion] = relationship(back_populates="answers")


class Submission(UUIDMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "submissions"

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # quiz answers: {question_id: [answer_id, ...]}
    answers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, name="submission_status"),
        nullable=False,
        default=SubmissionStatus.submitted,
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    grade: Mapped[Grade | None] = relationship(
        back_populates="submission", uselist=False, lazy="selectin"
    )


class Grade(UUIDMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "grades"

    submission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    points: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    max_points: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=100)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_auto: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    graded_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    graded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    submission: Mapped[Submission] = relationship(back_populates="grade")
