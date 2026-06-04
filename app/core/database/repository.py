"""Generic + tenant-aware repositories.

``TenantRepository`` is the workhorse: every read auto-filters by the current
tenant and hides soft-deleted rows; every create stamps ``tenant_id`` from
context. This is layer 2 of the 3-layer isolation (see ADR-0001) — RLS is the
backstop, but the repo makes correct behavior the default.
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import context as ctx
from app.core.database.base import Base, SoftDeleteMixin, TenantMixin
from app.shared.exceptions import NotFoundError
from app.shared.schemas import PageParams

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── query construction ────────────────────────────────────────────────
    def _select(self) -> Select[tuple[ModelT]]:
        stmt = select(self.model)
        if issubclass(self.model, SoftDeleteMixin):
            stmt = stmt.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        return stmt

    def _apply_search(self, stmt: Select[Any], term: str) -> Select[Any]:
        """Override per-repo to enable ?search=. Default: no-op."""
        return stmt

    def _apply_sort(self, stmt: Select[Any], sort: str | None) -> Select[Any]:
        if not sort:
            return stmt
        desc = sort.startswith("-")
        field = sort[1:] if desc else sort
        col = getattr(self.model, field, None)
        if col is None:
            return stmt
        return stmt.order_by(col.desc() if desc else col.asc())

    # ── reads ──────────────────────────────────────────────────────────────
    async def get(self, id: uuid.UUID) -> ModelT | None:
        stmt = self._select().where(self.model.id == id)  # type: ignore[attr-defined]
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_or_404(self, id: uuid.UUID) -> ModelT:
        obj = await self.get(id)
        if obj is None:
            raise NotFoundError(f"{self.model.__name__} {id} not found")
        return obj

    async def list(self, params: PageParams) -> tuple[list[ModelT], int]:
        stmt = self._select()
        if params.search:
            stmt = self._apply_search(stmt, params.search)

        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = self._apply_sort(stmt, params.sort).offset(params.offset).limit(params.limit)
        items = list((await self.session.execute(stmt)).scalars().all())
        return items, total

    async def exists(self, **filters: Any) -> bool:
        stmt = self._select()
        for k, v in filters.items():
            stmt = stmt.where(getattr(self.model, k) == v)
        return (await self.session.execute(stmt.limit(1))).first() is not None

    # ── writes ───────────────────────────────────────────────────────────
    async def add(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def create(self, **values: Any) -> ModelT:
        obj = self.model(**values)
        return await self.add(obj)

    async def delete(self, obj: ModelT, *, hard: bool = False) -> None:
        if not hard and isinstance(obj, SoftDeleteMixin):
            obj.deleted_at = func.now()  # type: ignore[assignment]
            await self.session.flush()
        else:
            await self.session.delete(obj)
            await self.session.flush()


class TenantRepository(BaseRepository[ModelT]):
    """Repository for tenant-scoped models. Filters + stamps ``tenant_id``."""

    def _select(self) -> Select[tuple[ModelT]]:
        stmt = super()._select()
        if issubclass(self.model, TenantMixin):
            tid = ctx.current_tenant_id()
            if tid is not None:
                stmt = stmt.where(self.model.tenant_id == tid)  # type: ignore[attr-defined]
        return stmt

    async def create(self, **values: Any) -> ModelT:
        if issubclass(self.model, TenantMixin) and "tenant_id" not in values:
            values["tenant_id"] = ctx.require_tenant_id()
        return await super().create(**values)
