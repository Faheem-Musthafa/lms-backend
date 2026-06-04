"""Dashboard schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ActivityItem(BaseModel):
    action: str
    resource: str
    resource_id: uuid.UUID | None
    created_at: datetime


class DashboardOut(BaseModel):
    enrolled_courses: int
    completed_lessons: int
    pending_assignments: int
    submissions: int
    recent_activity: list[ActivityItem]
