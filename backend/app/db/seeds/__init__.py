"""Idempotent seed scripts (PLAN §11.4).

Seed data (enums, seeded lenders, the initial ACTIVE model_version) is
runtime data, not schema, so it lives here rather than in an Alembic
migration. Each seed module exposes a ``run(session)`` function that is
safe to re-run (insert-if-not-exists / upsert).
"""
