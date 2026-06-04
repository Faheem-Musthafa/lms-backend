"""Async engine, session factory, and the request unit-of-work.

``get_db`` is the FastAPI dependency: it opens one transaction per request and
binds the Postgres RLS GUCs (``app.tenant_id`` / ``app.bypass_rls``) for that
transaction so row-level security is enforced for every query in the request.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core import context as ctx
from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
    pool_recycle=1800,
)

session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


async def _bind_rls(session: AsyncSession, tenant_id: uuid.UUID | None, *, bypass: bool) -> None:
    """Set transaction-local GUCs that the RLS policies read."""
    if not settings.enable_row_level_security:
        return
    await session.execute(
        text("SELECT set_config('app.bypass_rls', :v, true)"),
        {"v": "on" if bypass else "off"},
    )
    if tenant_id is not None:
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": str(tenant_id)},
        )


async def get_db() -> AsyncIterator[AsyncSession]:
    """Per-request session: one transaction, RLS bound from RequestContext."""
    rc = ctx.get_context()
    tenant_id = rc.tenant_id if rc else None
    bypass = bool(rc and rc.is_superadmin)

    async with session_factory() as session:
        await session.begin()
        try:
            await _bind_rls(session, tenant_id, bypass=bypass)
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()


@asynccontextmanager
async def tenant_session(
    tenant_id: uuid.UUID | None = None, *, bypass_rls: bool = False
) -> AsyncIterator[AsyncSession]:
    """Session for non-request code (seed scripts, jobs, event handlers).

    Explicitly scope to a tenant, or set ``bypass_rls=True`` for platform-level
    work (creating tenants, cross-tenant reports).
    """
    async with session_factory() as session:
        await session.begin()
        try:
            await _bind_rls(session, tenant_id, bypass=bypass_rls)
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()
