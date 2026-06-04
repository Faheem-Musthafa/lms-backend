"""Assignment endpoints — mounted at /api/v1/assignments."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.modules.assignments.schemas import (
    AssignmentFilter,
    AssignmentOut,
    GradeOut,
    GradeRequest,
    SubmissionOut,
    SubmitRequest,
)
from app.modules.assignments.service import AssignmentService
from app.modules.auth.dependencies import CurrentUser, DbSession, require_permission
from app.shared.schemas import Page, PageParams

router = APIRouter(prefix="/assignments", tags=["Assignments"])


def get_assignment_service(session: DbSession) -> AssignmentService:
    return AssignmentService(session)


AsgSvc = Annotated[AssignmentService, Depends(get_assignment_service)]


@router.get(
    "",
    response_model=Page[AssignmentOut],
    dependencies=[require_permission("assignment:read")],
)
async def list_assignments(
    filters: Annotated[AssignmentFilter, Depends()], svc: AsgSvc, _: CurrentUser
) -> Page[AssignmentOut]:
    items, total = await svc.list_assignments(filters, published_only=True)
    return Page.create([AssignmentOut.model_validate(a) for a in items], total, filters)


@router.get(
    "/{assignment_id}",
    response_model=AssignmentOut,
    dependencies=[require_permission("assignment:read")],
)
async def get_assignment(assignment_id: uuid.UUID, svc: AsgSvc, _: CurrentUser) -> AssignmentOut:
    return AssignmentOut.model_validate(await svc.get_assignment(assignment_id))


@router.post(
    "/{assignment_id}/submit",
    response_model=SubmissionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_permission("assignment:submit")],
)
async def submit(
    assignment_id: uuid.UUID, data: SubmitRequest, svc: AsgSvc, user: CurrentUser
) -> SubmissionOut:
    submission = await svc.submit(assignment_id, user.id, data)
    return SubmissionOut.model_validate(submission)


@router.post(
    "/submissions/{submission_id}/grade",
    response_model=GradeOut,
    dependencies=[require_permission("grade:write")],
)
async def grade(
    submission_id: uuid.UUID, data: GradeRequest, svc: AsgSvc, user: CurrentUser
) -> GradeOut:
    g = await svc.grade_submission(submission_id, data, user.id)
    return GradeOut.model_validate(g)


@router.get(
    "/grades/me",
    response_model=Page[GradeOut],
    dependencies=[require_permission("grade:read")],
)
async def my_grades(
    svc: AsgSvc, user: CurrentUser, params: Annotated[PageParams, Depends()]
) -> Page[GradeOut]:
    rows, total = await svc.list_grades(user.id, params)
    return Page.create([GradeOut.model_validate(g) for g in rows], total, params)
