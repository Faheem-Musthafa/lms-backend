"""Auth service — the auth use-cases. HTTP-free; raises domain errors."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import context as ctx
from app.core.cache import get_redis
from app.core.config import settings
from app.core.events import event_bus
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.security.jwt import TokenError
from app.modules.auth.events import (
    UserLoggedInEvent,
    UserRegisteredEvent,
)
from app.modules.auth.models import User, UserSession
from app.modules.auth.permissions import RoleCode
from app.modules.auth.repository import (
    RoleRepository,
    SessionRepository,
    UserRepository,
)
from app.modules.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.shared.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)

_RESET_PREFIX = "pwreset:"
_reset_store: dict[str, tuple[str, float]] = {}


def _store_reset(token: str, value: str, ttl: int) -> None:
    import time

    _reset_store[token] = (value, time.time() + ttl)


def _get_reset(token: str) -> str | None:
    import time

    entry = _reset_store.get(token)
    if entry is None:
        return None
    value, expires = entry
    if time.time() > expires:
        del _reset_store[token]
        return None
    return value


def _delete_reset(token: str) -> None:
    _reset_store.pop(token, None)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)
        self.sessions = SessionRepository(session)

    # ── registration ────────────────────────────────────────────────────
    async def register(self, data: RegisterRequest) -> User:
        tenant_id = ctx.require_tenant_id()
        email = data.email.lower()
        if await self.users.get_by_email(email):
            raise ConflictError("Email already registered")

        user = await self.users.create(
            email=email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            is_active=True,
        )
        # default role = student
        student = await self.roles.get_by_code(RoleCode.STUDENT.value)
        if student:
            user.roles.append(student)
        await self.session.flush()

        await event_bus.publish(
            UserRegisteredEvent(tenant_id=tenant_id, user_id=user.id, email=user.email)
        )
        return user

    # ── login / tokens ───────────────────────────────────────────────────
    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(email.lower())
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid credentials")
        if not user.is_active:
            raise AuthenticationError("Account disabled")
        return user

    async def login(
        self, data: LoginRequest, *, user_agent: str | None = None, ip: str | None = None
    ) -> TokenResponse:
        tenant_id = ctx.require_tenant_id()
        user = await self.authenticate(data.email, data.password)

        tokens = await self._issue_tokens(user, tenant_id, user_agent=user_agent, ip=ip)
        user.last_login_at = datetime.now(UTC)
        await self.session.flush()

        await event_bus.publish(
            UserLoggedInEvent(tenant_id=tenant_id, user_id=user.id, email=user.email)
        )
        return tokens

    async def _issue_tokens(
        self,
        user: User,
        tenant_id: uuid.UUID,
        *,
        user_agent: str | None,
        ip: str | None,
    ) -> TokenResponse:
        refresh_token, jti = create_refresh_token(user.id, tenant_id)
        self.session.add(
            UserSession(
                tenant_id=tenant_id,
                user_id=user.id,
                jti=jti,
                user_agent=user_agent,
                ip_address=ip,
                expires_at=datetime.now(UTC)
                + timedelta(seconds=settings.refresh_token_ttl_seconds),
            )
        )
        access_token = create_access_token(user.id, tenant_id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_ttl_seconds,
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except TokenError as e:
            raise AuthenticationError(str(e)) from e

        session = await self.sessions.get_by_jti(payload.jti)
        if session is None or not session.is_active:
            raise AuthenticationError("Session revoked or expired")
        if session.expires_at < datetime.now(UTC):
            raise AuthenticationError("Refresh token expired")

        user = await self.users.get_or_404(payload.sub)
        # rotate: revoke old session, issue new
        session.revoked_at = datetime.now(UTC)
        await self.session.flush()
        return await self._issue_tokens(
            user, payload.tid, user_agent=session.user_agent, ip=session.ip_address
        )

    async def logout(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except TokenError:
            return
        session = await self.sessions.get_by_jti(payload.jti)
        if session and session.is_active:
            session.revoked_at = datetime.now(UTC)
            await self.session.flush()

    # ── password reset ───────────────────────────────────────────────────
    async def forgot_password(self, email: str) -> str | None:
        """Create a reset token. Returns it (dev); production would email it.

        Always succeeds silently to avoid email enumeration.
        """
        tenant_id = ctx.require_tenant_id()
        user = await self.users.get_by_email(email.lower())
        if user is None:
            return None
        token = secrets.token_urlsafe(32)
        value = f"{tenant_id}:{user.id}"
        redis = get_redis()
        if redis is not None:
            await redis.set(f"{_RESET_PREFIX}{token}", value, ex=settings.password_reset_ttl_seconds)
        else:
            _store_reset(token, value, settings.password_reset_ttl_seconds)
        return token

    async def reset_password(self, token: str, new_password: str) -> None:
        redis = get_redis()
        if redis is not None:
            raw = await redis.get(f"{_RESET_PREFIX}{token}")
        else:
            raw = _get_reset(token)
        if not raw:
            raise ValidationError("Invalid or expired reset token")
        tenant_part, _, user_part = raw.partition(":")
        if uuid.UUID(tenant_part) != ctx.require_tenant_id():
            raise ValidationError("Invalid reset token for tenant")

        user = await self.users.get(uuid.UUID(user_part))
        if user is None:
            raise NotFoundError("User not found")
        user.hashed_password = hash_password(new_password)
        await self.session.flush()
        await self.sessions.revoke_all_for_user(user.id)
        if redis is not None:
            await redis.delete(f"{_RESET_PREFIX}{token}")
        else:
            _delete_reset(token)
