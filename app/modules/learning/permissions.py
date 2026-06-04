"""Learning module permissions."""

from __future__ import annotations

PERMISSIONS: list[tuple[str, str]] = [
    ("lesson:read", "View lessons"),
    ("lesson:create", "Create lessons"),
    ("lesson:update", "Update lessons"),
    ("lesson:delete", "Delete lessons"),
    ("progress:read", "View own progress"),
]
