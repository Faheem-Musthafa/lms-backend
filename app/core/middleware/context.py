"""Pure-ASGI request-context middleware.

Runs in the *same task* as the endpoint, so the ``contextvar`` it sets is
visible everywhere downstream (repositories, RLS session binding, audit,
events). It resolves tenant + user **without a DB hit on the hot path**:

* tenant/user come from the JWT ``tid``/``sub`` claims when a valid bearer
  token is present;
* otherwise the tenant comes from the ``X-Tenant-ID`` header (UUID or slug —
  slug needs one cached lookup).

It never rejects requests — auth enforcement is the dependencies' job. It only
establishes context so RLS can bind correctly.
"""

from __future__ import annotations

import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core import context as ctx
from app.core.config import settings
from app.core.security.jwt import TokenError, decode_token
from app.core.tenancy.service import resolve_tenant_id


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = headers.get("x-request-id") or str(uuid.uuid4())
        ip = self._client_ip(scope, headers)

        tenant_id, user_id = await self._resolve_identity(headers)

        rc = ctx.RequestContext(
            request_id=request_id,
            tenant_id=tenant_id,
            user_id=user_id,
            ip_address=ip,
        )
        token = ctx.set_context(rc)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)["x-request-id"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            ctx.reset_context(token)

    @staticmethod
    def _client_ip(scope: Scope, headers: Headers) -> str | None:
        fwd = headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
        client = scope.get("client")
        return client[0] if client else None

    async def _resolve_identity(
        self, headers: Headers
    ) -> tuple[uuid.UUID | None, uuid.UUID | None]:
        auth = headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            try:
                payload = decode_token(auth[7:], expected_type="access")
                return payload.tid, payload.sub
            except TokenError:
                pass  # fall through to header-based resolution

        raw_tenant = headers.get(settings.tenant_header.lower())
        if raw_tenant:
            return await resolve_tenant_id(raw_tenant), None
        return None, None
