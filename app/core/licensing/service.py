"""Licensing service — resolve & mutate per-tenant module entitlements.

Enabled-module sets are Redis-cached (short TTL) because the module guard runs
on nearly every request. Writes invalidate the tenant's cache key.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_redis
from app.core.licensing.constants import CORE_MODULE_CODES, ModuleCode
from app.core.licensing.models import Module, TenantModule
from app.shared.exceptions import NotFoundError

_CACHE_TTL = 60
_CACHE_PREFIX = "lic:enabled:"


class LicensingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _key(tenant_id: uuid.UUID) -> str:
        return f"{_CACHE_PREFIX}{tenant_id}"

    async def enabled_codes(self, tenant_id: uuid.UUID) -> set[str]:
        """Set of module codes currently enabled for the tenant (cached)."""
        redis = get_redis()
        if redis is not None:
            cached = await redis.get(self._key(tenant_id))
            if cached is not None:
                return set(json.loads(cached))

        codes = await self._compute_enabled(tenant_id)
        if redis is not None:
            await redis.set(self._key(tenant_id), json.dumps(sorted(codes)), ex=_CACHE_TTL)
        return codes

    async def _compute_enabled(self, tenant_id: uuid.UUID) -> set[str]:
        now = datetime.now(UTC)
        stmt = (
            select(Module.code)
            .join(TenantModule, TenantModule.module_id == Module.id)
            .where(
                TenantModule.tenant_id == tenant_id,
                TenantModule.enabled.is_(True),
                Module.is_active.is_(True),
            )
        )
        codes = set((await self.session.execute(stmt)).scalars().all())
        # expiry check (cheap re-query path kept simple)
        expired_stmt = (
            select(Module.code)
            .join(TenantModule, TenantModule.module_id == Module.id)
            .where(
                TenantModule.tenant_id == tenant_id,
                TenantModule.expires_at.is_not(None),
                TenantModule.expires_at < now,
            )
        )
        expired = set((await self.session.execute(expired_stmt)).scalars().all())
        codes -= expired
        # core modules are always available
        codes |= {c.value for c in CORE_MODULE_CODES}
        return codes

    async def tenant_has_module(self, tenant_id: uuid.UUID, code: ModuleCode | str) -> bool:
        code_str = code.value if isinstance(code, ModuleCode) else code
        if code_str in {c.value for c in CORE_MODULE_CODES}:
            return True
        return code_str in await self.enabled_codes(tenant_id)

    async def invalidate(self, tenant_id: uuid.UUID) -> None:
        redis = get_redis()
        if redis is not None:
            await redis.delete(self._key(tenant_id))

    # ── admin operations ─────────────────────────────────────────────────
    async def set_module(
        self, tenant_id: uuid.UUID, code: ModuleCode | str, *, enabled: bool
    ) -> TenantModule:
        code_str = code.value if isinstance(code, ModuleCode) else code
        module = (
            await self.session.execute(select(Module).where(Module.code == code_str))
        ).scalar_one_or_none()
        if module is None:
            raise NotFoundError(f"Module {code_str} not in catalog")

        tm = (
            await self.session.execute(
                select(TenantModule).where(
                    TenantModule.tenant_id == tenant_id,
                    TenantModule.module_id == module.id,
                )
            )
        ).scalar_one_or_none()

        now = datetime.now(UTC)
        if tm is None:
            tm = TenantModule(
                tenant_id=tenant_id,
                module_id=module.id,
                enabled=enabled,
                enabled_at=now if enabled else None,
            )
            self.session.add(tm)
        else:
            tm.enabled = enabled
            tm.enabled_at = now if enabled else tm.enabled_at
        await self.session.flush()
        await self.invalidate(tenant_id)
        return tm
