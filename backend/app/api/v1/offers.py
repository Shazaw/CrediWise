"""`/api/v1/offers` routes (PLAN §12.2 `GET /offers/{id}/safety`; FR-11).

A top-level resource (unlike `/assessments/{id}/offers`) because a single
offer's safety detail is addressed by its own ID, not by its parent
assessment (PLAN §12.2's endpoint catalogue lists it separately for exactly
this reason).
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.assessments import offer_to_response
from app.core.deps import require
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.enums import RoleEnum
from app.models.user import User
from app.schemas.error import STANDARD_ERROR_RESPONSES
from app.schemas.offer import OfferResponse
from app.services.offer_service import OfferService

router = APIRouter(prefix="/offers", tags=["offers"])


@router.get(
    "/{offer_id}/safety",
    response_model=OfferResponse,
    dependencies=[Depends(rate_limit("general"))],
    responses=STANDARD_ERROR_RESPONSES,
)
def get_offer_safety(
    offer_id: uuid.UUID,
    current_user: User = Depends(require(RoleEnum.USER)),
    db: Session = Depends(get_db),
) -> OfferResponse:
    view = OfferService(db).get_offer_safety(current_user, offer_id)
    return offer_to_response(view)
