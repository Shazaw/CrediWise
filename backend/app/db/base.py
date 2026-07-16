"""Shared SQLAlchemy declarative base.

Every ORM entity in ``app/models/`` inherits from ``Base``. Kept in its own
module (rather than ``session.py``) so Alembic's ``env.py`` can import
metadata without pulling in a live DB engine/session.
"""

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    # Every timestamp is TIMESTAMPTZ (PLAN §11.1) — models declare `Mapped[datetime]`
    # without repeating `DateTime(timezone=True)` at every column.
    type_annotation_map = {datetime: DateTime(timezone=True)}
