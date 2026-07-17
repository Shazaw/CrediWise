"""`/api/v1/financing-needs` routes (PLAN §12.2; FR-2). Thin: parse/validate,
call one service method, map to response DTO — no business logic (PLAN §10.1).
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import require
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.enums import RoleEnum
from app.models.financing_need import FinancingNeed
from app.models.user import User
from app.schemas.financing_need import (
    CreateFinancingNeedRequest,
    FinancingNeedListResponse,
    FinancingNeedResponse,
)
from app.services.financing_need_service import FinancingNeedService

router = APIRouter(prefix="/financing-needs", tags=["financing-needs"])


def _to_response(need: FinancingNeed) -> FinancingNeedResponse:
    return FinancingNeedResponse(
        financing_need_id=need.id,
        requested_amount=need.requested_amount,
        purpose=need.purpose,
        preferred_tenor_months=need.preferred_tenor_months,
        urgency=need.urgency,
        notes=need.notes,
        created_at=need.created_at,
    )


@router.post(
    "",
    response_model=FinancingNeedResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("general"))],
)
def create_financing_need(
    body: CreateFinancingNeedRequest,
    current_user: User = Depends(require(RoleEnum.USER)),
    db: Session = Depends(get_db),
) -> FinancingNeedResponse:
    need = FinancingNeedService(db).create(
        user=current_user,
        requested_amount=body.requested_amount,
        purpose=body.purpose,
        preferred_tenor_months=body.preferred_tenor_months,
        urgency=body.urgency,
        notes=body.notes,
    )
    return _to_response(need)


@router.get(
    "",
    response_model=FinancingNeedListResponse,
    dependencies=[Depends(rate_limit("general"))],
)
def list_financing_needs(
    current_user: User = Depends(require(RoleEnum.USER)),
    db: Session = Depends(get_db),
) -> FinancingNeedListResponse:
    needs = FinancingNeedService(db).list_for_user(current_user)
    return FinancingNeedListResponse(items=[_to_response(n) for n in needs])
