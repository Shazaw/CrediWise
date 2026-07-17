"""Seeds the three simulated lenders `POST /assessments/{id}/offers` seeds
offers against (PLAN §7.10/FR-11, §16.4, `model_config.OFFER_TEMPLATES`).

Idempotent: re-running does nothing once a lender with a given name exists
(PLAN §11.4 — seed data must be safe to re-run). Names are the seed's
stable identity key (no natural business key exists for a simulated
lender).
"""

from sqlalchemy.orm import Session

from app.models.enums import RegStatusEnum
from app.models.lender import Lender
from app.repositories.lender_repository import LenderRepository

#: Order matches `model_config.OFFER_TEMPLATES` -- `OfferService` zips
#: active lenders (in seed order) against templates (in list order).
SEEDED_LENDERS: list[dict[str, object]] = [
    {
        "name": "Bank Amanah Digital (Simulated)",
        "regulatory_status": RegStatusEnum.SIMULATED_REGULATED_PROVIDER,
        "logo_url": None,
    },
    {
        "name": "KilatDana Fintech (Simulated)",
        "regulatory_status": RegStatusEnum.SIMULATED_REGULATED_PROVIDER,
        "logo_url": None,
    },
    {
        "name": "Cepat Cair Lending (Simulated)",
        "regulatory_status": RegStatusEnum.SIMULATED_REGULATED_PROVIDER,
        "logo_url": None,
    },
]


def run(session: Session) -> None:
    repo = LenderRepository(session)
    for entry in SEEDED_LENDERS:
        name = entry["name"]
        assert isinstance(name, str)  # noqa: S101 - internal invariant, not user input
        existing = repo.get_by_name(name)
        if existing is not None:
            existing.regulatory_status = RegStatusEnum.SIMULATED_REGULATED_PROVIDER
            existing.is_active = True
            continue
        repo.add(
            Lender(
                name=name,
                regulatory_status=entry["regulatory_status"],
                logo_url=entry["logo_url"],
                is_active=True,
            )
        )
