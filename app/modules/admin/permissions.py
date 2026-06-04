"""Admin module permissions."""

from __future__ import annotations

PERMISSIONS: list[tuple[str, str]] = [
    ("report:read", "View reports & analytics"),
    ("admin:access", "Access the admin module"),
]
