"""Admin schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field

from app.core.licensing.constants import ModuleCode
from app.modules.learning.models import LessonType

class AdminLessonCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    content_type: LessonType = Field(default=LessonType.text)
    content: str | None = None
    is_preview: bool = False
    order_index: int = 0


class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=200)
    role_codes: list[str] = Field(default_factory=list)
    is_active: bool = True


class AdminUserUpdate(BaseModel):
    full_name: str | None = Field(None, max_length=200)
    is_active: bool | None = None
    role_codes: list[str] | None = None


class TenantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=80)
    modules: list[ModuleCode] = Field(default_factory=list)
    admin_email: EmailStr
    admin_password: str = Field(min_length=8, max_length=128)


class TenantOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    is_active: bool


class ModuleToggle(BaseModel):
    code: ModuleCode
    enabled: bool


class TenantModuleOut(BaseModel):
    code: str
    name: str
    enabled: bool


class ReportOut(BaseModel):
    users: int
    courses: int
    enrollments: int
    submissions: int
    active_modules: list[str]
