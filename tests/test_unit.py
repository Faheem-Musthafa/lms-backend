"""Pure unit tests — no DB/Redis needed."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from app.core.events.base import DomainEvent
from app.core.events.bus import EventBus
from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.security.jwt import TokenError


def test_password_hash_roundtrip() -> None:
    h = hash_password("s3cret-password")
    assert h != "s3cret-password"
    assert verify_password("s3cret-password", h)
    assert not verify_password("wrong", h)


def test_access_token_roundtrip() -> None:
    uid, tid = uuid.uuid4(), uuid.uuid4()
    token = create_access_token(uid, tid)
    payload = decode_token(token, expected_type="access")
    assert payload.sub == uid
    assert payload.tid == tid


def test_token_type_mismatch_rejected() -> None:
    token = create_access_token(uuid.uuid4(), uuid.uuid4())
    with pytest.raises(TokenError):
        decode_token(token, expected_type="refresh")


@dataclass(frozen=True, kw_only=True)
class _Thing(DomainEvent):
    value: int = 0


async def test_event_bus_dispatches_to_subscribers() -> None:
    bus = EventBus()
    received: list[int] = []

    async def handler(event: DomainEvent) -> None:
        assert isinstance(event, _Thing)
        received.append(event.value)

    bus.subscribe(_Thing, handler)
    await bus.publish(_Thing(value=42))
    assert received == [42]


async def test_event_bus_isolates_handler_errors() -> None:
    bus = EventBus()
    ok: list[int] = []

    async def bad(_: DomainEvent) -> None:
        raise RuntimeError("boom")

    async def good(_: DomainEvent) -> None:
        ok.append(1)

    bus.subscribe(_Thing, bad)
    bus.subscribe(_Thing, good)
    await bus.publish(_Thing(value=1))  # must not raise
    assert ok == [1]
