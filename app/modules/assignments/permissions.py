"""Assignment module permissions."""

from __future__ import annotations

PERMISSIONS: list[tuple[str, str]] = [
    ("assignment:read", "View assignments"),
    ("assignment:create", "Create assignments"),
    ("assignment:update", "Update assignments"),
    ("assignment:delete", "Delete assignments"),
    ("assignment:submit", "Submit assignments"),
    ("grade:read", "View grades"),
    ("grade:write", "Grade submissions"),
]
