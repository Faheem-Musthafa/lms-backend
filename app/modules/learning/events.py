"""Learning domain events."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.core.events.base import DomainEvent


@dataclass(frozen=True, kw_only=True)
class LessonCompletedEvent(DomainEvent):
    lesson_id: uuid.UUID
    course_id: uuid.UUID

    def audit(self) -> dict:
        return {
            "action": "lesson.completed",
            "resource": "lesson",
            "resource_id": self.lesson_id,
            "new_values": {"course_id": str(self.course_id)},
        }
