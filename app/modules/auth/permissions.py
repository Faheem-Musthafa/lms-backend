"""Auth-owned permissions + canonical role codes + default role→perm matrix.

Each module exports its own ``PERMISSIONS``; the seed script aggregates them
into the global ``permissions`` catalog. ``ROLE_PERMISSIONS`` defines the
default permission set each system role is seeded with, per tenant.
"""

from __future__ import annotations

import enum


class RoleCode(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    INSTRUCTOR = "instructor"
    STUDENT = "student"


# (code, description)
PERMISSIONS: list[tuple[str, str]] = [
    ("user:read", "View users"),
    ("user:create", "Create users"),
    ("user:update", "Update users"),
    ("user:delete", "Delete users"),
    ("role:read", "View roles"),
    ("role:assign", "Assign roles to users"),
    ("tenant:read", "View tenant settings"),
    ("tenant:manage", "Manage tenants & module licensing"),
]
