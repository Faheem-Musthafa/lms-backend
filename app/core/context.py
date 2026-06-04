"""Request-scoped context — tenant, user, request id.

Backed by ``contextvars`` so every layer (repository, RLS session, audit,
event handlers) can read the current tenant/user without threading it through
every function signature. Set by middleware; never mutated by handlers.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar, Token
from dataclasses import dataclass, field

_ctx: ContextVar[RequestContext | None] = ContextVar("request_context", default=None)


@dataclass(slots=True)
class RequestContext:
    request_id: str
    tenant_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    roles: frozenset[str] = field(default_factory=frozenset)
    permissions: frozenset[str] = field(default_factory=frozenset)
    ip_address: str | None = None
    is_superadmin: bool = False


def set_context(ctx: RequestContext) -> Token:
    """Bind the context for the current task; returns a token for reset()."""
    return _ctx.set(ctx)


def reset_context(token: Token) -> None:
    _ctx.reset(token)


def get_context() -> RequestContext | None:
    return _ctx.get()


def current_tenant_id() -> uuid.UUID | None:
    ctx = _ctx.get()
    return ctx.tenant_id if ctx else None


def require_tenant_id() -> uuid.UUID:
    tid = current_tenant_id()
    if tid is None:
        raise RuntimeError("No tenant in context — tenant-scoped operation attempted unscoped")
    return tid


def current_user_id() -> uuid.UUID | None:
    ctx = _ctx.get()
    return ctx.user_id if ctx else None
