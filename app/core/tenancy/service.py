"""Tenant CRUD + cached slug/uuid resolution (used by middleware)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_redis
from app.core.database.session import tenant_session
from app.core.tenancy.models import Tenant
from app.shared.exceptions import NotFoundError

_SLUG_CACHE = "tenant:slug:"
_SLUG_TTL = 300


class TenantService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, tenant_id: uuid.UUID) -> Tenant | None:
        return await self.session.get(Tenant, tenant_id)

    async def get_by_slug(self, slug: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.slug == slug, Tenant.deleted_at.is_(None))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_or_404(self, tenant_id: uuid.UUID) -> Tenant:
        t = await self.get(tenant_id)
        if t is None:
            raise NotFoundError(f"Tenant {tenant_id} not found")
        return t

    async def create(self, *, name: str, slug: str, settings: dict | None = None) -> Tenant:
        tenant = Tenant(name=name, slug=slug, settings=settings or {})
        self.session.add(tenant)
        await self.session.flush()
        return tenant


def _parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return None


async def resolve_tenant_id(identifier: str) -> uuid.UUID | None:
    """Resolve a tenant from a UUID or slug. Slug lookups are Redis-cached.

    Runs with RLS bypass because the ``tenants`` table is platform-level.
    """
    as_uuid = _parse_uuid(identifier)
    if as_uuid is not None:
        return as_uuid

    redis = get_redis()
    cached = await redis.get(f"{_SLUG_CACHE}{identifier}")
    if cached:
        return uuid.UUID(cached)

    async with tenant_session(bypass_rls=True) as session:
        tenant = await TenantService(session).get_by_slug(identifier)
        if tenant is None or not tenant.is_active:
            return None
        await redis.set(f"{_SLUG_CACHE}{identifier}", str(tenant.id), ex=_SLUG_TTL)
        return tenant.id
