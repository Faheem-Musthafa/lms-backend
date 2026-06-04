"""Course catalog schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.courses.models import CourseLevel, CourseStatus, EnrollmentStatus
from app.shared.schemas import ORMModel, PageParams


class CourseFilter(PageParams):
    category_id: uuid.UUID | None = None
    level: CourseLevel | None = None
    status: CourseStatus | None = None
    is_free: bool | None = None


class CategoryOut(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    parent_id: uuid.UUID | None = None


class CourseOut(ORMModel):
    id: uuid.UUID
    title: str
    slug: str
    summary: str | None
    category_id: uuid.UUID | None
    status: CourseStatus
    level: CourseLevel
    is_free: bool
    price: Decimal
    thumbnail_url: str | None
    enrollment_count: int
    published_at: datetime | None
    created_at: datetime


class CourseDetailOut(CourseOut):
    description: str | None = None


class EnrollmentOut(ORMModel):
    id: uuid.UUID
    course_id: uuid.UUID
    user_id: uuid.UUID
    status: EnrollmentStatus
    progress_pct: int
    enrolled_at: datetime
    completed_at: datetime | None


# ── admin-facing write schemas ────────────────────────────────────────────────
class CourseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=220)
    summary: str | None = Field(None, max_length=500)
    description: str | None = None
    category_id: uuid.UUID | None = None
    level: CourseLevel = CourseLevel.beginner
    is_free: bool = True
    price: Decimal = Decimal("0")
    thumbnail_url: str | None = None


class CourseUpdate(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=200)
    summary: str | None = None
    description: str | None = None
    category_id: uuid.UUID | None = None
    level: CourseLevel | None = None
    status: CourseStatus | None = None
    is_free: bool | None = None
    price: Decimal | None = None
    thumbnail_url: str | None = None
