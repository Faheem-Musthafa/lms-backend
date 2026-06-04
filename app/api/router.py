"""API gateway — single ``/api/v1`` surface consumed by all MFEs.

Every module router is **always mounted**. Non-core modules carry a
``require_module(...)`` dependency, so a tenant that hasn't licensed a module
gets 403 at request time — enabling/disabling is a data change, not a deploy.
The route → MFE mapping:

    /api/v1/auth/*         → Authentication MFE   (core, always on)
    /api/v1/courses/*      → Course Catalog MFE    (COURSES)
    /api/v1/learning/*     → Learning MFE          (LEARNING)
    /api/v1/assignments/*  → Assignment MFE        (ASSIGNMENTS)
    /api/v1/dashboard/*    → Dashboard MFE         (DASHBOARD)
    /api/v1/admin/*        → Admin MFE             (ADMIN)
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.core.licensing import ModuleCode, require_module
from app.modules.admin.router import router as admin_router
from app.modules.assignments.router import router as assignments_router
from app.modules.auth.router import router as auth_router
from app.modules.courses.router import router as courses_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.learning.router import router as learning_router

api_router = APIRouter(prefix=settings.api_v1_prefix)

# AUTH is core — no module guard
api_router.include_router(auth_router)

api_router.include_router(courses_router, dependencies=[require_module(ModuleCode.COURSES)])
api_router.include_router(learning_router, dependencies=[require_module(ModuleCode.LEARNING)])
api_router.include_router(assignments_router, dependencies=[require_module(ModuleCode.ASSIGNMENTS)])
api_router.include_router(dashboard_router, dependencies=[require_module(ModuleCode.DASHBOARD)])
api_router.include_router(admin_router, dependencies=[require_module(ModuleCode.ADMIN)])
