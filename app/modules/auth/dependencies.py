"""Auth/RBAC dependencies — the published interface other modules import.

``get_current_user`` validates the bearer token, loads the user (RLS already
scoped to the tenant), and enriches the request context with the caller's
roles/permissions. ``require_permission`` / ``require_role`` are the gates.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.params import Depends as DependsMarker
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import context as ctx
from app.core.database.session import get_db
from app.core.security.jwt import TokenError, decode_token
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.shared.exceptions import AuthenticationError, PermissionDeniedError

_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    session: DbSession,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if creds is None:
        raise AuthenticationError("Missing bearer token")
    try:
        payload = decode_token(creds.credentials, expected_type="access")
    except TokenError as e:
        raise AuthenticationError(str(e)) from e

    user = await UserRepository(session).get(payload.sub)
    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive")

    # enrich request context for downstream layers (audit, RLS bypass, guards)
    rc = ctx.get_context()
    if rc is not None:
        rc.roles = frozenset(user.role_codes)
        rc.permissions = frozenset(user.permission_codes)
        rc.user_id = user.id
        rc.is_superadmin = user.is_superuser
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(*codes: str) -> DependsMarker:
    """Require ALL listed permission codes (superuser bypasses)."""

    async def _guard(user: CurrentUser) -> User:
        if user.is_superuser:
            return user
        missing = set(codes) - user.permission_codes
        if missing:
            raise PermissionDeniedError(
                f"Missing permission(s): {', '.join(sorted(missing))}",
                details={"required": list(codes)},
            )
        return user

    return Depends(_guard)


def require_role(*role_codes: str) -> DependsMarker:
    async def _guard(user: CurrentUser) -> User:
        if user.is_superuser:
            return user
        if not (set(role_codes) & user.role_codes):
            raise PermissionDeniedError(
                f"Requires role(s): {', '.join(role_codes)}",
                details={"required_roles": list(role_codes)},
            )
        return user

    return Depends(_guard)
