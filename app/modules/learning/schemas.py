"""Learning schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.modules.learning.models import LessonType, ProgressStatus
from app.shared.schemas import ORMModel


class VideoAssetOut(ORMModel):
    url: str
    hls_url: str | None
    duration_seconds: int


class DocumentAssetOut(ORMModel):
    file_url: str
    file_type: str
    size_bytes: int


class LessonOut(ORMModel):
    id: uuid.UUID
    course_id: uuid.UUID
    module_id: uuid.UUID | None
    title: str
    content_type: LessonType
    order_index: int
    duration_seconds: int
    is_preview: bool
    video: VideoAssetOut | None = None
    document: DocumentAssetOut | None = None


class LessonProgressOut(ORMModel):
    id: uuid.UUID
    lesson_id: uuid.UUID
    course_id: uuid.UUID
    status: ProgressStatus
    last_position_seconds: int
    completed_at: datetime | None


class CompleteLessonRequest(BaseModel):
    last_position_seconds: int = 0
