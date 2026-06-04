"""Course module permissions."""

from __future__ import annotations

PERMISSIONS: list[tuple[str, str]] = [
    ("course:read", "View courses"),
    ("course:create", "Create courses"),
    ("course:update", "Update courses"),
    ("course:delete", "Delete courses"),
    ("course:enroll", "Enroll in courses"),
    ("category:manage", "Manage categories"),
]
