"""Seed demo data: module catalog, permissions, two tenants with differing
module subscriptions, roles, users, and sample course content.

Idempotent — safe to re-run. Runs with RLS bypass (platform-level).

    python -m scripts.seed
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import app.registry  # noqa: F401  — load all models
from app.core.cache import close_redis
from app.core.database.session import engine, tenant_session
from app.core.licensing.constants import CORE_MODULE_CODES, MODULE_CATALOG, ModuleCode
from app.core.licensing.models import Module
from app.core.licensing.service import LicensingService
from app.core.security import hash_password
from app.core.tenancy.models import Tenant
from app.modules.admin.permissions import PERMISSIONS as ADMIN_PERMS
from app.modules.assignments.models import (
    Assignment,
    AssignmentType,
    Quiz,
    QuizAnswer,
    QuizQuestion,
)
from app.modules.assignments.permissions import PERMISSIONS as ASSIGN_PERMS
from app.modules.auth.models import Permission, Role, User
from app.modules.auth.permissions import PERMISSIONS as AUTH_PERMS
from app.modules.auth.permissions import RoleCode
from app.modules.courses.models import Category, Course, CourseStatus
from app.modules.courses.permissions import PERMISSIONS as COURSE_PERMS
from app.modules.learning.models import CourseModule, Lesson, LessonType
from app.modules.learning.permissions import PERMISSIONS as LEARN_PERMS

ALL_PERMISSIONS = AUTH_PERMS + COURSE_PERMS + LEARN_PERMS + ASSIGN_PERMS + ADMIN_PERMS
ALL_CODES = {c for c, _ in ALL_PERMISSIONS}

# Default permission set per role.
ROLE_MATRIX: dict[RoleCode, set[str]] = {
    RoleCode.SUPER_ADMIN: ALL_CODES,
    RoleCode.TENANT_ADMIN: ALL_CODES - {"tenant:manage"},
    RoleCode.INSTRUCTOR: {
        "course:read",
        "course:create",
        "course:update",
        "lesson:read",
        "lesson:create",
        "lesson:update",
        "lesson:delete",
        "assignment:read",
        "assignment:create",
        "assignment:update",
        "grade:read",
        "grade:write",
        "progress:read",
        "report:read",
        "admin:access",
        "user:read",
    },
    RoleCode.STUDENT: {
        "course:read",
        "course:enroll",
        "lesson:read",
        "progress:read",
        "assignment:read",
        "assignment:submit",
        "grade:read",
    },
}

ROLE_NAMES = {
    RoleCode.SUPER_ADMIN: "Super Admin",
    RoleCode.TENANT_ADMIN: "Tenant Admin",
    RoleCode.INSTRUCTOR: "Instructor",
    RoleCode.STUDENT: "Student",
}

# tenant slug -> (name, licensed modules)
TENANTS = {
    "abc-academy": ("ABC Academy", [ModuleCode.AUTH, ModuleCode.COURSES, ModuleCode.LEARNING, ModuleCode.ADMIN]),
    "full-lms": ("Full LMS Inc", list(ModuleCode)),
}


async def seed_modules(s: AsyncSession) -> None:
    existing = {m.code for m in (await s.execute(select(Module))).scalars()}
    for code, desc in MODULE_CATALOG.items():
        if code.value not in existing:
            s.add(
                Module(
                    code=code.value,
                    name=desc,
                    description=desc,
                    is_active=True,
                    is_core=code in CORE_MODULE_CODES,
                )
            )
    await s.flush()


async def seed_permissions(s: AsyncSession) -> dict[str, Permission]:
    existing = {p.code: p for p in (await s.execute(select(Permission))).scalars()}
    for code, desc in ALL_PERMISSIONS:
        if code not in existing:
            p = Permission(code=code, description=desc)
            s.add(p)
            existing[code] = p
    await s.flush()
    return existing


async def seed_tenant(
    s: AsyncSession,
    slug: str,
    name: str,
    modules: list[ModuleCode],
    perms: dict[str, Permission],
) -> Tenant:
    tenant = (await s.execute(select(Tenant).where(Tenant.slug == slug))).scalar_one_or_none()
    if tenant is None:
        tenant = Tenant(name=name, slug=slug)
        s.add(tenant)
        await s.flush()

    # licensing
    lic = LicensingService(s)
    for code in modules:
        await lic.set_module(tenant.id, code, enabled=True)

    # roles
    roles: dict[RoleCode, Role] = {}
    for rc in RoleCode:
        granted = [perms[c] for c in ROLE_MATRIX[rc] if c in perms]
        role = (
            await s.execute(
                select(Role)
                .options(selectinload(Role.permissions))
                .where(Role.tenant_id == tenant.id, Role.code == rc.value)
            )
        ).scalar_one_or_none()
        if role is None:
            role = Role(
                tenant_id=tenant.id,
                code=rc.value,
                name=ROLE_NAMES[rc],
                is_system=True,
                permissions=granted,
            )
            s.add(role)
        else:
            role.permissions = granted  # collection preloaded via selectinload
        roles[rc] = role
    await s.flush()

    # users (domain derived from slug; valid TLD so EmailStr accepts it)
    domain = f"{slug}.com"
    await _seed_user(
        s,
        tenant,
        f"admin@{domain}",
        "Tenant Admin",
        [roles[RoleCode.TENANT_ADMIN]],
        password="Admin123!",
    )
    await _seed_user(
        s,
        tenant,
        f"instructor@{domain}",
        "Jane Instructor",
        [roles[RoleCode.INSTRUCTOR]],
        password="Teach123!",
    )
    await _seed_user(
        s,
        tenant,
        f"student@{domain}",
        "Sam Student",
        [roles[RoleCode.STUDENT]],
        password="Learn123!",
    )

    # platform super admin lives in the full-lms tenant
    if slug == "full-lms":
        await _seed_user(
            s,
            tenant,
            "root@platform.com",
            "Platform Root",
            [roles[RoleCode.SUPER_ADMIN]],
            password="Root123!",
            is_superuser=True,
        )
    return tenant


async def _seed_user(
    s: AsyncSession,
    tenant: Tenant,
    email: str,
    full_name: str,
    roles: list[Role],
    *,
    password: str,
    is_superuser: bool = False,
) -> User:
    user = (
        await s.execute(
            select(User)
            .options(selectinload(User.roles))
            .where(User.tenant_id == tenant.id, User.email == email)
        )
    ).scalar_one_or_none()
    if user is None:
        user = User(
            tenant_id=tenant.id,
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            is_active=True,
            is_verified=True,
            is_superuser=is_superuser,
            roles=roles,
        )
        s.add(user)
    else:
        user.roles = roles  # collection preloaded via selectinload
    await s.flush()
    return user


async def seed_content(s: AsyncSession, tenant: Tenant) -> None:
    """Sample category + published course + lessons (+ quiz for full-lms)."""
    if (await s.execute(select(Course).where(Course.tenant_id == tenant.id))).first():
        return

    category = Category(tenant_id=tenant.id, name="Programming", slug="programming")
    s.add(category)
    await s.flush()

    course = Course(
        tenant_id=tenant.id,
        title="Python for Beginners",
        slug="python-for-beginners",
        summary="Learn Python from scratch.",
        description="A complete introduction to Python programming.",
        category_id=category.id,
        status=CourseStatus.published,
        is_free=True,
        published_at=datetime.now(UTC),
    )
    s.add(course)
    await s.flush()

    module = CourseModule(
        tenant_id=tenant.id, course_id=course.id, title="Getting Started", order_index=0
    )
    s.add(module)
    await s.flush()

    s.add_all(
        [
            Lesson(
                tenant_id=tenant.id,
                course_id=course.id,
                module_id=module.id,
                title="Welcome",
                content_type=LessonType.text,
                content="Welcome to the course!",
                order_index=0,
                is_preview=True,
            ),
            Lesson(
                tenant_id=tenant.id,
                course_id=course.id,
                module_id=module.id,
                title="Installing Python",
                content_type=LessonType.video,
                order_index=1,
                duration_seconds=600,
            ),
        ]
    )
    await s.flush()

    # quiz only where ASSIGNMENTS is licensed (full-lms)
    if tenant.slug == "full-lms":
        assignment = Assignment(
            tenant_id=tenant.id,
            course_id=course.id,
            title="Python Basics Quiz",
            description="Check your understanding.",
            type=AssignmentType.quiz,
            max_points=10,
            pass_points=6,
            is_published=True,
        )
        s.add(assignment)
        await s.flush()
        quiz = Quiz(tenant_id=tenant.id, assignment_id=assignment.id)
        s.add(quiz)
        await s.flush()
        q = QuizQuestion(
            tenant_id=tenant.id,
            quiz_id=quiz.id,
            text="What keyword defines a function in Python?",
            points=10,
        )
        s.add(q)
        await s.flush()
        s.add_all(
            [
                QuizAnswer(tenant_id=tenant.id, question_id=q.id, text="def", is_correct=True),
                QuizAnswer(tenant_id=tenant.id, question_id=q.id, text="func", is_correct=False),
                QuizAnswer(tenant_id=tenant.id, question_id=q.id, text="lambda", is_correct=False),
            ]
        )
    await s.flush()


async def main() -> None:
    async with tenant_session(bypass_rls=True) as s:
        await seed_modules(s)
        perms = await seed_permissions(s)
        tenants = []
        for slug, (name, modules) in TENANTS.items():
            tenants.append(await seed_tenant(s, slug, name, modules, perms))
        for tenant in tenants:
            await seed_content(s, tenant)

    await engine.dispose()
    await close_redis()
    print("Seed complete.")
    print("  Tenants: abc-academy (AUTH/COURSES/LEARNING), full-lms (all modules)")
    print("  Login (send header  X-Tenant-ID: <slug>):")
    print("    admin@abc-academy.com / Admin123!")
    print("    student@full-lms.com  / Learn123!")
    print("    root@platform.com     / Root123!   (super admin)")


if __name__ == "__main__":
    asyncio.run(main())
