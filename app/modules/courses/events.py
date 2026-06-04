"""Course domain events."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.core.events.base import DomainEvent


@dataclass(frozen=True, kw_only=True)
class CourseCreatedEvent(DomainEvent):
    course_id: uuid.UUID
    title: str

    def audit(self) -> dict:
        return {
            "action": "course.created",
            "resource": "course",
            "resource_id": self.course_id,
            "new_values": {"title": self.title},
        }


@dataclass(frozen=True, kw_only=True)
class CourseEnrolledEvent(DomainEvent):
    course_id: uuid.UUID
    enrollment_id: uuid.UUID

    def audit(self) -> dict:
        return {
            "action": "course.enrolled",
            "resource": "enrollment",
            "resource_id": self.enrollment_id,
            "new_values": {"course_id": str(self.course_id)},
        }
