"""Assignment domain events."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.core.events.base import DomainEvent


@dataclass(frozen=True, kw_only=True)
class AssignmentSubmittedEvent(DomainEvent):
    assignment_id: uuid.UUID
    submission_id: uuid.UUID

    def audit(self) -> dict:
        return {
            "action": "assignment.submitted",
            "resource": "submission",
            "resource_id": self.submission_id,
            "new_values": {"assignment_id": str(self.assignment_id)},
        }


@dataclass(frozen=True, kw_only=True)
class SubmissionGradedEvent(DomainEvent):
    submission_id: uuid.UUID
    points: float
    is_auto: bool

    def audit(self) -> dict:
        return {
            "action": "submission.graded",
            "resource": "submission",
            "resource_id": self.submission_id,
            "new_values": {"points": self.points, "auto": self.is_auto},
        }
