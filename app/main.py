"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.registry  # noqa: F401  — populates metadata + registers event handlers
from app.core.cache import close_redis, get_redis
from app.core.config import settings
from app.core.database.session import engine
from app.core.middleware import RequestContextMiddleware
from app.shared.exceptions import register_exception_handlers

logging.basicConfig(level=settings.log_level)

OPENAPI_TAGS = [
    {"name": "Authentication", "description": "Login, registration, tokens, sessions."},
    {"name": "Course Catalog", "description": "Browse, search and enroll in courses."},
    {"name": "Learning", "description": "Lessons, content and progress tracking."},
    {"name": "Assignments", "description": "Assignments, quizzes, auto/manual grading."},
    {"name": "Dashboard", "description": "Aggregated learner/instructor metrics."},
    {"name": "Admin", "description": "User, course, tenant & module administration."},
]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await close_redis()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Modular multi-tenant LMS backend (modular monolith, DDD, API-first).",
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Pure-ASGI context middleware must wrap the app so the contextvar is set
    # in the same task as the endpoint.
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    from app.api.router import api_router

    app.include_router(api_router)

    @app.get("/health", tags=["Health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["Health"])
    async def ready() -> dict[str, str]:
        from sqlalchemy import text

        from app.core.database.session import session_factory

        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        await get_redis().ping()
        return {"status": "ready"}

    return app


app = create_app()
