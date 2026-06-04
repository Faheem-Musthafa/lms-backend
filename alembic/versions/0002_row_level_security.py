"""row level security policies

Enables Postgres RLS on every tenant-scoped table (layer 3 of the isolation
model — see ADR-0001). Policies key on the transaction-local GUC
``app.tenant_id`` set by the app per request, with an ``app.bypass_rls`` escape
hatch for platform-level (super admin / seed) operations.

FORCE is required: the app connects as the table owner, and owners bypass RLS
unless it is FORCEd.

Revision ID: 0002_rls
Revises: 0b3936dfb7ef
Create Date: 2026-06-04
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_rls"
down_revision: str | None = "0b3936dfb7ef"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Every table carrying a tenant_id that must be isolated per tenant.
# NB: `tenant_modules` is intentionally excluded — it is control-plane data
# read with RLS bypass during tenant/licensing resolution.
RLS_TABLES = [
    "users",
    "roles",
    "user_sessions",
    "categories",
    "courses",
    "course_instructors",
    "course_enrollments",
    "course_modules",
    "lessons",
    "video_assets",
    "document_assets",
    "lesson_progress",
    "assignments",
    "quizzes",
    "quiz_questions",
    "quiz_answers",
    "submissions",
    "grades",
    "audit_logs",
]

_PREDICATE = (
    "(tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
    " OR current_setting('app.bypass_rls', true) = 'on')"
)


def upgrade() -> None:
    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} USING {_PREDICATE} WITH CHECK {_PREDICATE}"
        )


def downgrade() -> None:
    for table in RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
