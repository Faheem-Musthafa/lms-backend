"""Domain event base. Events are immutable facts ("X happened")."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Base for all domain events.

    Subclasses add their own payload fields. ``tenant_id`` / ``user_id`` are
    captured so consumers (audit, dashboard) need no extra context lookups.
    """

    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    tenant_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None

    @property
    def name(self) -> str:
        return type(self).__name__

    def audit(self) -> dict | None:
        """Audit descriptor, or ``None`` to skip auditing this event.

        Override in subclasses to feed the universal audit consumer without
        coupling ``core/audit`` to any module's event types. Shape::

            {"action": str, "resource": str,
             "resource_id": uuid | None, "new_values": dict | None}
        """
        return None
