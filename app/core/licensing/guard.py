"""``@require_module`` — the module-licensing gate.

Usage on a router or route::

    router = APIRouter(dependencies=[require_module(ModuleCode.ASSIGNMENTS)])
    # or
    @router.get(..., dependencies=[require_module(ModuleCode.DASHBOARD)])

If the current tenant has not licensed the module → 403 with
``{"error": "Module not enabled for tenant"}``. Routers are always mounted;
this gate makes enable/disable a pure data change (no redeploy).
"""

from __future__ import annotations

from fastapi import Depends
from fastapi.params import Depends as DependsMarker
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import context as ctx
from app.core.database.session import get_db
from app.core.licensing.constants import ModuleCode
from app.core.licensing.service import LicensingService
from app.shared.exceptions import ModuleNotEnabledError, TenantResolutionError


def require_module(code: ModuleCode) -> DependsMarker:
    async def _guard(session: AsyncSession = Depends(get_db)) -> None:
        tenant_id = ctx.current_tenant_id()
        if tenant_id is None:
            raise TenantResolutionError()
        svc = LicensingService(session)
        if not await svc.tenant_has_module(tenant_id, code):
            raise ModuleNotEnabledError()

    return Depends(_guard)
