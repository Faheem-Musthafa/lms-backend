"""Dashboard endpoint — mounted at /api/v1/dashboard."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.dashboard.schemas import DashboardOut
from app.modules.dashboard.service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_dashboard_service(session: DbSession) -> DashboardService:
    return DashboardService(session)


@router.get("", response_model=DashboardOut)
@router.get("/", response_model=DashboardOut, include_in_schema=False)
async def get_dashboard(
    user: CurrentUser,
    svc: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> DashboardOut:
    return await svc.for_user(user.id)
