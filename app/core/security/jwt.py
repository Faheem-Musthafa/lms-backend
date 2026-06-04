"""JWT encode/decode. Tokens carry identity only (sub, tid, type, jti).

Permissions are resolved per-request (and cached) — never trusted from the
token — so role/permission changes and revocation take effect immediately.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pydantic import BaseModel

from app.core.config import settings


class TokenError(Exception):
    pass


class TokenPayload(BaseModel):
    sub: uuid.UUID  # user id
    tid: uuid.UUID  # tenant id
    type: str  # "access" | "refresh"
    jti: uuid.UUID  # token id (session handle for refresh)
    exp: int
    iat: int


def _now() -> datetime:
    return datetime.now(UTC)


def _encode(
    *, user_id: uuid.UUID, tenant_id: uuid.UUID, token_type: str, ttl: int, jti: uuid.UUID
) -> str:
    now = _now()
    payload = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "type": token_type,
        "jti": str(jti),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    return _encode(
        user_id=user_id,
        tenant_id=tenant_id,
        token_type="access",
        ttl=settings.access_token_ttl_seconds,
        jti=uuid.uuid4(),
    )


def create_refresh_token(
    user_id: uuid.UUID, tenant_id: uuid.UUID, jti: uuid.UUID | None = None
) -> tuple[str, uuid.UUID]:
    """Returns (token, jti). Persist jti as the session handle for revocation."""
    jti = jti or uuid.uuid4()
    token = _encode(
        user_id=user_id,
        tenant_id=tenant_id,
        token_type="refresh",
        ttl=settings.refresh_token_ttl_seconds,
        jti=jti,
    )
    return token, jti


def decode_token(token: str, *, expected_type: str | None = None) -> TokenPayload:
    try:
        raw = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as e:
        raise TokenError("Token expired") from e
    except jwt.PyJWTError as e:
        raise TokenError("Invalid token") from e

    payload = TokenPayload(**raw)
    if expected_type and payload.type != expected_type:
        raise TokenError(f"Expected {expected_type} token, got {payload.type}")
    return payload
