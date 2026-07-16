"""Helper for declaring native-Postgres-backed enum columns (PLAN §11.1).

Centralizes `Enum` construction so every model column references the same
Postgres type name that the owning Alembic migration creates explicitly.
"""

from enum import StrEnum
from typing import TypeVar

from sqlalchemy import Enum as SAEnum

E = TypeVar("E", bound=StrEnum)


def sa_enum(enum_cls: type[E], pg_type_name: str) -> SAEnum:
    return SAEnum(enum_cls, name=pg_type_name, native_enum=True, validate_strings=True)
