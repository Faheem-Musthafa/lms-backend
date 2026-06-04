"""Audit writes — both in-request (shares the UoW) and out-of-band (own txn)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import context as ctx
from app.core.audit.models import AuditLog
from app.core.database.session import tenant_session


class AuditService:
    """Record audit entries inside the current request transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self,
        *,
        action: str,
        resource: str,
        resource_id: uuid.UUID | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        tenant_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
    ) -> AuditLog:
        rc = ctx.get_context()
        entry = AuditLog(
            tenant_id=tenant_id or (rc.tenant_id if rc else None),  # type: ignore[arg-type]
            user_id=user_id or (rc.user_id if rc else None),
            action=action,
            resource=resource,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=rc.ip_address if rc else None,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry


async def write_audit(
    *,
    tenant_id: uuid.UUID,
    action: str,
    resource: str,
    resource_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """Out-of-band audit write (event handlers, jobs) — own transaction."""
    async with tenant_session(tenant_id) as session:
        session.add(
            AuditLog(
                tenant_id=tenant_id,
                user_id=user_id,
                action=action,
                resource=resource,
                resource_id=resource_id,
                old_values=old_values,
                new_values=new_values,
                ip_address=ip_address,
            )
        )
