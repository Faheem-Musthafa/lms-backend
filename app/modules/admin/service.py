"""Admin services — user management, tenant/licensing admin, reports.

Admin *orchestrates* other modules through their published services/repos.
Platform-level operations (creating tenants, toggling another tenant's modules)
run on a dedicated RLS-bypass session via ``tenant_session``.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import context as ctx
from app.core.database.session import tenant_session
from app.core.events import event_bus
from app.core.licensing.constants import MODULE_CATALOG, ModuleCode
from app.core.licensing.models import Module
from app.core.licensing.service import LicensingService
from app.core.security import hash_password
from app.core.tenancy.models import Tenant
from app.core.tenancy.service import TenantService
from app.modules.admin.schemas import (
    AdminUserCreate,
    AdminUserUpdate,
    ReportOut,
    TenantCreate,
    TenantModuleOut,
)
from app.modules.assignments.models import Submission
from app.modules.auth.events import UserRegisteredEvent, UserUpdatedEvent
from app.modules.auth.models import User
from app.modules.auth.repository import RoleRepository, UserRepository
from app.modules.courses.models import Course, CourseEnrollment
from app.shared.exceptions import ConflictError, NotFoundError, ValidationError
from app.shared.schemas import PageParams


class AdminUserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)

    async def list_users(self, params: PageParams) -> tuple[list[User], int]:
        return await self.users.list(params)

    async def create_user(self, data: AdminUserCreate) -> User:
        tenant_id = ctx.require_tenant_id()
        if await self.users.get_by_email(data.email.lower()):
            raise ConflictError("Email already registered")
        user = await self.users.create(
            email=data.email.lower(),
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            is_active=data.is_active,
        )
        if data.role_codes:
            user.roles = await self.roles.get_by_codes(data.role_codes)
        await self.session.flush()
        await event_bus.publish(
            UserRegisteredEvent(tenant_id=tenant_id, user_id=user.id, email=user.email)
        )
        return user

    async def update_user(self, user_id: uuid.UUID, data: AdminUserUpdate) -> User:
        user = await self.users.get_or_404(user_id)
        changes = data.model_dump(exclude_unset=True)
        if "full_name" in changes:
            user.full_name = changes["full_name"]
        if "is_active" in changes:
            user.is_active = changes["is_active"]
        if data.role_codes is not None:
            user.roles = await self.roles.get_by_codes(data.role_codes)
        await self.session.flush()
        await event_bus.publish(
            UserUpdatedEvent(
                tenant_id=ctx.require_tenant_id(),
                user_id=user.id,
                changes={k: v for k, v in changes.items() if k != "role_codes"},
            )
        )
        return user


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def tenant_report(self) -> ReportOut:
        tenant_id = ctx.require_tenant_id()

        async def count(model) -> int:
            return (
                await self.session.execute(select(func.count()).select_from(model))
            ).scalar_one()

        active_modules = sorted(await LicensingService(self.session).enabled_codes(tenant_id))
        return ReportOut(
            users=await count(User),
            courses=await count(Course),
            enrollments=await count(CourseEnrollment),
            submissions=await count(Submission),
            active_modules=active_modules,
        )


class TenantAdminService:
    """Platform-level (super admin) tenant + licensing administration."""

    async def create_tenant(self, data: TenantCreate) -> Tenant:
        async with tenant_session(bypass_rls=True) as session:
            svc = TenantService(session)
            if await svc.get_by_slug(data.slug):
                raise ConflictError(f"Tenant slug '{data.slug}' already exists")
            tenant = await svc.create(name=data.name, slug=data.slug)
            await session.flush()

            lic = LicensingService(session)
            codes = set(data.modules) | {ModuleCode.AUTH}
            for code in codes:
                await lic.set_module(tenant.id, code, enabled=True)
            return tenant

    async def list_modules(self, tenant_id: uuid.UUID) -> list[TenantModuleOut]:
        async with tenant_session(bypass_rls=True) as session:
            enabled = await LicensingService(session).enabled_codes(tenant_id)
            modules = (await session.execute(select(Module))).scalars().all()
            return [
                TenantModuleOut(
                    code=m.code,
                    name=MODULE_CATALOG.get(ModuleCode(m.code), m.name),
                    enabled=m.code in enabled,
                )
                for m in modules
            ]

    async def set_module(self, tenant_id: uuid.UUID, code: ModuleCode, *, enabled: bool) -> None:
        if code == ModuleCode.AUTH and not enabled:
            raise ValidationError("AUTH is a core module and cannot be disabled")
        async with tenant_session(bypass_rls=True) as session:
            # ensure tenant exists
            if (await session.get(Tenant, tenant_id)) is None:
                raise NotFoundError(f"Tenant {tenant_id} not found")
            await LicensingService(session).set_module(tenant_id, code, enabled=enabled)
