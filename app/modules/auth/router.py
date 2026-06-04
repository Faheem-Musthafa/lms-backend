"""Auth endpoints — mounted at /api/v1/auth."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.core.config import settings
from app.core.middleware.rate_limit import RateLimiter
from app.modules.auth.dependencies import CurrentUser, DbSession
from app.modules.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MeOut,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
)
from app.modules.auth.service import AuthService
from app.shared.schemas import Message

router = APIRouter(prefix="/auth", tags=["Authentication"])

_auth_limit = Depends(RateLimiter(settings.rate_limit_auth))


def get_auth_service(session: DbSession) -> AuthService:
    return AuthService(session)


AuthSvc = Annotated[AuthService, Depends(get_auth_service)]


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_auth_limit],
)
async def register(data: RegisterRequest, svc: AuthSvc) -> UserOut:
    user = await svc.register(data)
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenResponse, dependencies=[_auth_limit])
async def login(data: LoginRequest, request: Request, svc: AuthSvc) -> TokenResponse:
    return await svc.login(
        data,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, svc: AuthSvc) -> TokenResponse:
    return await svc.refresh(data.refresh_token)


@router.post("/logout", response_model=Message)
async def logout(data: LogoutRequest, svc: AuthSvc) -> Message:
    await svc.logout(data.refresh_token)
    return Message(message="Logged out")


@router.post("/forgot-password", response_model=Message, dependencies=[_auth_limit])
async def forgot_password(data: ForgotPasswordRequest, svc: AuthSvc) -> Message:
    token = await svc.forgot_password(data.email)
    # In production the token is emailed, never returned. Exposed in non-prod for testing.
    if token and not settings.is_production:
        return Message(message=f"Reset token (dev only): {token}")
    return Message(message="If the email exists, a reset link has been sent")


@router.post("/reset-password", response_model=Message)
async def reset_password(data: ResetPasswordRequest, svc: AuthSvc) -> Message:
    await svc.reset_password(data.token, data.new_password)
    return Message(message="Password reset successful")


@router.get("/me", response_model=MeOut)
async def me(user: CurrentUser) -> MeOut:
    out = MeOut.model_validate(user)
    out.permissions = sorted(user.permission_codes)
    return out
