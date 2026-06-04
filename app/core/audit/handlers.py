"""Universal audit consumer.

Subscribes to the ``DomainEvent`` base, so *every* published event that defines
an ``audit()`` descriptor is logged — with zero coupling between ``core/audit``
and any module's concrete event types.
"""

from __future__ import annotations

from app.core.audit.service import write_audit
from app.core.events.base import DomainEvent
from app.core.events.bus import subscribe


@subscribe(DomainEvent)
async def audit_domain_event(event: DomainEvent) -> None:
    descriptor = event.audit()
    if descriptor is None or event.tenant_id is None:
        return
    await write_audit(
        tenant_id=event.tenant_id,
        user_id=event.user_id,
        action=descriptor.get("action", event.name),
        resource=descriptor.get("resource", "unknown"),
        resource_id=descriptor.get("resource_id"),
        new_values=descriptor.get("new_values"),
        old_values=descriptor.get("old_values"),
    )
