"""Canonical module codes. The source of truth for the licensing catalog."""

from __future__ import annotations

import enum


class ModuleCode(str, enum.Enum):
    AUTH = "AUTH"
    COURSES = "COURSES"
    LEARNING = "LEARNING"
    ASSIGNMENTS = "ASSIGNMENTS"
    DASHBOARD = "DASHBOARD"
    ADMIN = "ADMIN"


# AUTH is mandatory — every tenant has it; it cannot be disabled.
CORE_MODULE_CODES = frozenset({ModuleCode.AUTH})

ALL_MODULE_CODES = tuple(ModuleCode)

MODULE_CATALOG: dict[ModuleCode, str] = {
    ModuleCode.AUTH: "Authentication & identity",
    ModuleCode.COURSES: "Course catalog & enrollment",
    ModuleCode.LEARNING: "Lessons, content & progress",
    ModuleCode.ASSIGNMENTS: "Assignments, quizzes & grading",
    ModuleCode.DASHBOARD: "Learner & instructor dashboards",
    ModuleCode.ADMIN: "Administration, reports & analytics",
}
