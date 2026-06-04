"""Auth domain events."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.events.base import DomainEvent


@dataclass(frozen=True, kw_only=True)
class UserRegisteredEvent(DomainEvent):
    email: str

    def audit(self) -> dict:
        return {
            "action": "user.registered",
            "resource": "user",
            "resource_id": self.user_id,
            "new_values": {"email": self.email},
        }


@dataclass(frozen=True, kw_only=True)
class UserLoggedInEvent(DomainEvent):
    email: str

    def audit(self) -> dict:
        return {"action": "auth.login", "resource": "user", "resource_id": self.user_id}


@dataclass(frozen=True, kw_only=True)
class UserUpdatedEvent(DomainEvent):
    changes: dict

    def audit(self) -> dict:
        return {
            "action": "user.updated",
            "resource": "user",
            "resource_id": self.user_id,
            "new_values": self.changes,
        }
