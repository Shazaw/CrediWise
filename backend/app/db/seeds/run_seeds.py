"""Entry point that runs every registered seed module in order.

Usage: ``python -m app.db.seeds.run_seeds``

Empty in Sprint 0 — ``SEED_MODULES`` gains entries (e.g. lenders,
model_versions) as the features that own that data are implemented.
"""

import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.core.logging import configure_logging
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

SEED_MODULES: list[Callable[[Session], None]] = []


def run_all() -> None:
    with SessionLocal() as session:
        for seed in SEED_MODULES:
            logger.info("running seed", extra={"seed": seed.__module__})
            seed(session)
        session.commit()


if __name__ == "__main__":
    configure_logging()
    run_all()
