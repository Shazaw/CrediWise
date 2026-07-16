"""Shared SQLAlchemy declarative base.

Every ORM entity in ``app/models/`` inherits from ``Base``. Kept in its own
module (rather than ``session.py``) so Alembic's ``env.py`` can import
metadata without pulling in a live DB engine/session.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
