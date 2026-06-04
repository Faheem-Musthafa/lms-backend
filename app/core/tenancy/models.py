"""Tenant — the root of the multi-tenant hierarchy. NOT tenant-scoped itself."""

from __future__ import annotations

import enum

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class IsolationMode(str, enum.Enum):
    """Hybrid tenancy promotion levels (see ADR-0001).

    ``shared`` rows live in the shared schema with a tenant_id discriminator.
    ``schema`` / ``database`` are promotion targets for heavy/regulated tenants;
    the app switches search_path / connection — repositories & RLS are unchanged.
    """

    shared = "shared"
    schema = "schema"
    database = "database"


class Tenant(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    isolation_mode: Mapped[IsolationMode] = mapped_column(
        Enum(IsolationMode, name="isolation_mode"),
        nullable=False,
        default=IsolationMode.shared,
    )
    # populated only when isolation_mode != shared
    schema_name: Mapped[str | None] = mapped_column(String(80), nullable=True)

    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Tenant {self.slug}>"
