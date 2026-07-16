# Handover: Cycle 2 backend — Auth, Users & Consent Data Model (Sprint 1)

## Session scope
- Workstream: BACKEND
- Branch: `backend/cycle-2-auth`
- Base commit: `a1930f5` (== `origin/main` at session start)
- Latest commit: see `git log -1` on this branch
- PLAN.md sections / requirement IDs: §10, §11.3, §12.2, §18, §19.2, §25 Sprint 1, §26.2 T1.1–T1.7/T1.9; FR-1, FR-2 (profile fields only), FR-15

## User request
Start cycle 2 backend work per `PLAN.md`/`CLAUDE.md`/`docs/development/parallel-workflow.md` — the next cycle boundary after cycle-1-foundation is Sprint 1: "Auth, Users & Consent Data Model."

## Completed
- `users`, `user_profiles`, `user_identities`, `refresh_tokens`, `audit_logs`, `model_versions` ORM models + one Alembic migration (`0002_auth_identity_governance.py`), all following PLAN §11.1 conventions (UUID PK, `created_at`/`updated_at`/`deleted_at`, trigger-updated `updated_at`, native Postgres enums).
- `refresh_tokens` was not in PLAN §11.3's original table list but is required by the already-documented §18.1 decision ("refresh tokens are stored server-side (hashed) so they can be revoked"); added and documented in PLAN.md §11.3 in this same PR, doc version bumped 1.1.1 → 1.1.2.
- argon2id password hashing + RS256 JWT access tokens (15 min) + opaque refresh tokens (30 day, SHA-256-hashed at rest, rotated on every `/auth/refresh` call, revoked on `/auth/logout`).
- Routes: `POST /api/v1/auth/register|login|refresh|logout`, `GET /api/v1/me`, `PATCH /api/v1/me/profile`.
- RBAC dependency `require(role, ownership_getter)` in `app/core/deps.py` — deny-by-default, role check always runs before any ownership lookup. Consent checking is not wired yet (no lender endpoints exist in this cycle) but the guard shape is ready for it.
- Redis-backed rate limiting (`app/core/rate_limit.py`) — auth tier (10/min) applied to all `/auth/*` routes, general tier (120/min) applied to `/me*`; `fakeredis` injectable for tests via `rate_limit.set_redis_client(...)`.
- Audit logging: every register/login/refresh/logout/profile-update call writes an `audit_logs` row in the same DB transaction (`app/services/audit_service.py`).
- `model_versions` governance table + idempotent seed of one bootstrap `ACTIVE` row (`crediwise-core` / `v1`) so `assessments.model_version_id` has a stable FK target ahead of Sprint 3+ engines. Real engine weights are not implemented yet — `app/engines/config/model_config.py`'s `CONFIG` dict is intentionally empty.
- OpenAPI snapshot committed at `docs/api/openapi-v1.json` (PLAN §12.4).
- Tests: 65 tests (24 new integration tests across `tests/integration/api/test_auth.py` and `test_me.py`, plus new unit tests for `core/security.py`, the RBAC guard, and rate limiting). 91.9% coverage on `app/`, comfortably above the 70% gate.

## Current state
- What works: the full register → login → refresh (rotation) → logout flow, profile read/update, RBAC role/ownership enforcement, rate limiting, and audit trail — all verified against a real Postgres 16 instance (migration `upgrade → downgrade → upgrade` cycle passes).
- What is partially complete: nothing partial — Sprint 1's backend scope (T1.1–T1.7, T1.9) is fully implemented.
- What is not started: T1.8 (iOS auth UI) — explicitly out of scope for a BACKEND session per CLAUDE.md §2.2/§2.3.

## Validation evidence
- `ruff check app tests` — clean (required one config addition: `[tool.ruff.lint.flake8-bugbear] extend-immutable-calls` to allow FastAPI's `Depends(...)` default-argument idiom — this is the first FastAPI route code in the repo, so the gap hadn't surfaced before).
- `black --check app tests` — clean.
- `mypy app tests` — clean, no errors.
- `pytest` — **65 passed**, 91.91% coverage (gate is 70%).
- `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` — passes against a real Postgres 16.
- `python -m app.db.seeds.run_seeds` run twice — idempotent, exactly one `model_versions` row.
- **Known sandbox limitation:** this session had no Docker/system Postgres/Redis and no `sudo`. I used a rootless embedded Postgres (`pgserver`, pip-installed only into the local `.venv`, never added to `pyproject.toml`) and manually supplied the `pgcrypto`/`citext` contrib `.so`/`.control` files (downloaded directly from `apt.postgresql.org`, matching PG 16.14 exactly) into that instance's extension directory, since the minimal bundled build doesn't ship contrib modules. This was purely local scaffolding to let me run the *real* test suite and the *real* Alembic migrations end-to-end — nothing about this workaround is reflected in the committed code. CI (`.github/workflows/backend-ci.yml`) already provisions a full `postgres:16` service container, so none of this is needed there.

## Files changed
- `backend/app/models/{enums,mixins,sa_enum,user,refresh_token,audit_log,model_version,__init__}.py` — new ORM layer.
- `backend/app/db/base.py` — added `type_annotation_map` for timezone-aware `datetime`.
- `backend/alembic/env.py`, `backend/alembic/versions/0002_auth_identity_governance.py` — new migration.
- `backend/app/core/{security,rate_limit,deps}.py` — new.
- `backend/app/core/config.py` — added `SECURITY_*` settings + PEM-unescaping properties.
- `backend/app/core/errors.py` — added `RateLimitError`.
- `backend/app/repositories/{user_repository,refresh_token_repository}.py` — new.
- `backend/app/services/{audit_service,auth_service,user_service}.py` — new.
- `backend/app/schemas/{auth,user}.py` — new DTOs.
- `backend/app/api/v1/{__init__,auth,me}.py` — new routers.
- `backend/app/main.py` — mounts `/api/v1`, adds `Retry-After` header handling.
- `backend/app/engines/config/model_config.py`, `backend/app/db/seeds/model_versions.py`, `backend/app/db/seeds/run_seeds.py` — governance bootstrap.
- `backend/scripts/generate_dev_jwt_keys.py`, `Makefile` (`backend-generate-jwt-keys` target), `backend/.env.example` — local dev JWT keypair generation.
- `backend/pyproject.toml` — added `passlib[argon2]`, `pyjwt[crypto]`, `email-validator`; ruff bugbear config; mypy override for `passlib.*`.
- `backend/tests/**` — new integration/unit tests; `tests/conftest.py` gained an ephemeral test JWT keypair + autouse `fakeredis` fixture; `tests/unit/test_config.py` updated for the new required `SECURITY_JWT_*` settings.
- `docs/api/openapi-v1.json` — new snapshot.
- `PLAN.md` — documented `refresh_tokens` table (§11.3), bumped to v1.1.2, checked off T1.1–T1.7/T1.9 in §26.2.

## Remaining work (for a FRONTEND session, T1.8)
1. `SessionManager` + Keychain `TokenStore` + `AuthInterceptor` in `ios/CrediWise/Core/Auth/`.
2. Auth screens (sign up / sign in) wired to `POST /api/v1/auth/register` and `/login`.
3. Contract summary for the DTOs (see `docs/api/openapi-v1.json` for the authoritative shapes):
   - `POST /auth/register` → `{email, password}` → `201 {id, email, role, identity_status}`; `409 CONFLICT` on duplicate email; `422` on password policy violation (≥10 chars, ≥1 letter, ≥1 digit — mirror this client-side per PLAN §13.6).
   - `POST /auth/login` → `{email, password}` → `200 {access_token, refresh_token, token_type: "bearer", expires_in}`; `401 AUTH_ERROR` on bad credentials.
   - `POST /auth/refresh` → `{refresh_token}` → `200` same token-pair shape; refresh tokens are single-use (rotated) — replaying an old one is `401`.
   - `POST /auth/logout` → requires `Authorization: Bearer <access_token>` **and** `{refresh_token}` in the body → `204`.
   - `GET /me` / `PATCH /me/profile` — both require `Authorization: Bearer`; profile fields are `full_name`, `employment_type` (enum, see OpenAPI), `business_type`, `locale`.
   - Error envelope is always `{"error": {"code", "message", "details", "correlation_id"}}` (PLAN §10.3) — build `ErrorMapper` against `code`, not the HTTP status alone.
4. Do not reproduce password-policy or JWT logic client-side beyond mirroring the validation UX; the server remains the source of truth (PLAN §13.6).

## Risks and failure modes
- None known for the implemented scope. `identity_status`/`employment_type`/`document_type`/`verification_status` enum member sets were not specified in PLAN Appendix A; I chose reasonable values and documented the choice in `app/models/enums.py`'s docstring — flag if product wants different values before FRONTEND or Sprint-4-onward work depends on them.

## Commands for the next agent
```bash
git checkout backend/cycle-2-auth   # or main once merged
cd backend
uv venv --python 3.12 .venv && uv pip install -e ".[dev]" --python .venv/bin/python
make backend-generate-jwt-keys      # paste output into backend/.env
docker compose -f ../infra/docker-compose.yml up -d postgres redis minio
make backend-migrate
make backend-seed
make backend-test
```

## Do not touch
- `ios/**` — untouched this session, no conflicts expected.

## Uncommitted state
- Clean at time of writing this handoff — all changes above are committed on `backend/cycle-2-auth` (see final report for exact commit hash and push status).
