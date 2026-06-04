"""Learning models: CourseModule, Lesson, VideoAsset, DocumentAsset, LessonProgress.

NOTE: ``CourseModule`` (table ``course_modules``) is the curriculum section — not
to be confused with the *licensing* ``Module``.
"""

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
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import (
    Base,
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
)


class LessonType(str, enum.Enum):
    video = "video"
    document = "document"
    text = "text"


class ProgressStatus(str, enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"


class CourseModule(UUIDMixin, TenantMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "course_modules"

    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Lesson(UUIDMixin, TenantMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "lessons"

    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    module_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("course_modules.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_type: Mapped[LessonType] = mapped_column(
        Enum(LessonType, name="lesson_type"), nullable=False, default=LessonType.text
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_preview: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    video: Mapped[VideoAsset | None] = relationship(
        back_populates="lesson", uselist=False, lazy="selectin"
    )
    document: Mapped[DocumentAsset | None] = relationship(
        back_populates="lesson", uselist=False, lazy="selectin"
    )


class VideoAsset(UUIDMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "video_assets"

    lesson_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="s3")
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    hls_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    lesson: Mapped[Lesson] = relationship(back_populates="video")


class DocumentAsset(UUIDMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "document_assets"

    lesson_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    file_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_type: Mapped[str] = mapped_column(String(40), nullable=False, default="pdf")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    lesson: Mapped[Lesson] = relationship(back_populates="document")


class LessonProgress(UUIDMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (
        UniqueConstraint("lesson_id", "user_id", name="uq_lesson_progress_lesson_user"),
    )

    lesson_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ProgressStatus] = mapped_column(
        Enum(ProgressStatus, name="progress_status"),
        nullable=False,
        default=ProgressStatus.not_started,
    )
    last_position_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
