# Handover: Cycle 3 backend — Upload, File Security & Storage (Sprint 2)

## Session scope
- Workstream: BACKEND
- Branch: `backend/cycle-3-upload-storage`
- Base commit: `6006b3c` (== `origin/main` at session start)
- Latest commit: see `git log -1` on this branch
- PLAN.md sections / requirement IDs: §7.2, §8.2, §10.1, §11.3, §16.1, §17.1, §17.3, §18.4, §24.10, §24.11, §25 Sprint 2, §26.3 T2.1–T2.5/T2.7; FR-3

## User request
Start cycle 3 backend work per `PLAN.md`/`CLAUDE.md`/`docs/development/parallel-workflow.md` — the next cycle boundary after cycle-2-auth is Sprint 2: "Upload, File Security & Storage."

## Completed
- `financial_accounts` + `source_documents` ORM models + one Alembic migration (`0003_upload_storage.py`), following PLAN §11.1 conventions.
- Gap-filled enum member sets not in Appendix A (PLAN §24.11, same pattern as Sprint 1's `refresh_tokens`): `ownership_enum` (`DECLARED, VERIFIED`), `conn_status_enum` (`ACTIVE, INACTIVE, ERROR`), and two `doc_status_enum` states PLAN §8.2's diagram requires but Appendix A omitted (`VALIDATION_FAILED`, `DUPLICATE_REUSED`). Documented in PLAN.md §11.3/Appendix A in this PR, doc version bumped 1.1.2 → 1.2.0.
- `StoragePort` protocol (`put_object`/`get_object`/`delete_object`/`presigned_upload_url`/`presigned_download_url`) + `S3StorageAdapter` (boto3, path-style addressing for MinIO compatibility) in `app/integrations/storage/`.
- `FileSecurityEngine` (`app/engines/file_security.py`) — pure per PLAN §10.1: size cap, declared-vs-magic-byte MIME cross-check, PDF password/decrypt via `pypdf` + suspicious-action/JS object-graph scan, image decompression-bomb/pixel cap via Pillow, CSV UTF-8 sniff. Returns a typed outcome (`PASSED`/`REJECTED_SECURITY`/`VALIDATION_FAILED`) or raises a domain error for the two same-request retry cases (`UNSUPPORTED_MEDIA_TYPE` 415, `PDF_PASSWORD_REQUIRED`/`INVALID_PDF_PASSWORD` 422).
- **ADR-013** (new): the entire file-security stage runs synchronously in `POST /documents`, not in the `documents` Celery worker as PLAN §8.2's diagram might suggest — required because (a) PDF passwords must never cross the Celery/Redis boundary (§24.10) and (b) dedup must gate the HTTP response before any row/storage write exists (FR-3 AC3, and CLAUDE.md's named measurable outcome about duplicate uploads). See the ADR for the full reasoning and alternatives considered.
- `DocumentService.upload` (dedup gate → security engine → row creation → storage write only on `PASSED` → audit log → Celery dispatch) and `DocumentService.get_status` (ownership via 404, not 403 — PLAN §18.4 BOLA/IDOR: doesn't confirm another user's document exists).
- `app/pipeline/dispatch.py` — an overridable dispatch seam (mirrors `core/rate_limit`'s `get_redis_client`/`set_redis_client`) so tests run `process_document`'s logic inline against the same DB session instead of needing a real Celery broker.
- `app/pipeline/document_tasks.py` — `process_document` Celery task, scoped to exactly the state diagram's `SECURITY_CHECK → EXTRACTING` edge (idempotent/resumable per NFR-3: a document not in `UPLOADED` is a no-op). This is the seam Sprint 3's real OCR/extraction worker extends.
- Routes: `POST /api/v1/documents` (202, multipart) and `GET /api/v1/documents/{id}/status` (200), both rate-limited (upload/general tiers) and role-guarded (`RoleEnum.USER`).
- New config: `MAX_UPLOAD_MB` (PLAN-named, default 15), `MAX_PDF_PAGES` (default 60), `MAX_IMAGE_PIXELS` (default 25,000,000) — all gap-fill knobs documented in `.env.example`.
- New dependencies: `pypdf`, `pillow`, `python-multipart` (runtime); `moto[s3]` (dev-only, mocks S3 for gate tests without real MinIO/network).
- OpenAPI snapshot regenerated at `docs/api/openapi-v1.json` — purely additive (275 insertions, 0 deletions vs. the Sprint 1 snapshot).
- Tests: 117 total (up from 92) — 17 `FileSecurityEngine` golden tests (96% engine coverage), 5 `S3StorageAdapter` tests (moto-mocked), 17 `POST /documents`/`GET status` integration tests (dedup, malicious PDF, oversized, wrong MIME, password required/wrong/correct, image upload, financial-account ownership, cross-user 404), 3 `process_document` idempotency tests. 93.86% overall coverage on `app/` (gate is 70%).

## Current state
- What works: upload → dedup/security-triage → storage write → Celery dispatch → `SECURITY_CHECK → EXTRACTING` transition → status polling, all verified end to end against a real Postgres 16 instance and a moto-mocked S3 (migration `upgrade → downgrade → upgrade` cycle passes).
- What is partially complete: nothing partial — Sprint 2's backend scope (T2.1–T2.5, T2.7) is fully implemented.
- What is not started: T2.6 (iOS upload UI) — explicitly out of scope for a BACKEND session per CLAUDE.md §2.2/§2.3. There is also no dedicated `financial_accounts` create/list route yet (not required by T2.1, which is model+migration only — `source_documents.financial_account_id` is nullable and optionally validated for ownership if supplied).

## Validation evidence
- `ruff check app tests` — clean (added `fastapi.File`/`fastapi.Form`/`app.core.deps.require` to `extend-immutable-calls`, same rationale as Sprint 1's `Depends` exception: FastAPI's DI default-argument idiom).
- `black --check app tests` — clean.
- `mypy app tests` — clean (added `boto3.*`/`botocore.*`/`moto.*` to the `ignore_missing_imports` override list, same pattern as `celery.*`/`kombu.*`/`passlib.*`).
- `pytest` — **117 passed** (2 pre-existing, unrelated `test_config.py` tests fail *only* when my ad-hoc local-verification shell's `DB_HOST`/`DB_PORT` env vars leak into the process — confirmed by running `tests/unit/test_config.py` in isolation with those two vars unset, where both pass; not a real regression, and CI's job env doesn't have this leak). 93.86% overall coverage, 96% on the new engine.
- `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` — passes against a real Postgres 16.
- **Known sandbox limitation (same class as Sprint 1's):** this session had no Docker/system Postgres/Redis/MinIO and no `sudo`. Unlike Sprint 1, this `pgserver` release (0.1.4) already bundles working `pgcrypto`/`citext` contrib modules, so no manual `.so`/`.control` patching was needed. It only listens on a Unix socket by default; I stopped it and restarted the same binary directly with `-h 127.0.0.1 -p 5433 -k ''` (TCP only, no socket) so `Settings.sqlalchemy_database_uri`'s plain `host:port` URL format works unmodified. `moto` was used for `S3StorageAdapter` tests/fixtures instead of real MinIO — it intercepts AWS-shaped endpoints, not arbitrary custom ones, so those tests/fixtures point at `https://s3.amazonaws.com` rather than the real app's `STORAGE_ENDPOINT_URL`; the adapter code under test is unchanged. CI already provisions real `postgres:16` (see `.github/workflows/backend-ci.yml`); it has no MinIO/Redis service either, which is why the general test suite must never depend on either being reachable (satisfied here: `moto` for storage, the `dispatch` override seam for Celery, `fakeredis` for rate limiting).

## Files changed
- `backend/app/models/{enums,financial_account,source_document,__init__}.py` — new/updated ORM layer.
- `backend/alembic/versions/0003_upload_storage.py` — new migration.
- `backend/app/core/config.py` — added `max_upload_mb`/`max_pdf_pages`/`max_image_pixels`.
- `backend/app/core/errors.py` — added `UnsupportedMediaTypeError`, `PdfPasswordRequiredError`, `InvalidPdfPasswordError`.
- `backend/app/engines/file_security.py` — new pure engine.
- `backend/app/integrations/storage/{port,s3_adapter,__init__}.py` — new; removed the directory's `.gitkeep`.
- `backend/app/repositories/{source_document_repository,financial_account_repository}.py` — new.
- `backend/app/services/document_service.py` — new.
- `backend/app/pipeline/{dispatch,document_tasks}.py` — new.
- `backend/app/schemas/document.py` — new DTOs.
- `backend/app/api/v1/{documents,__init__}.py` — new router + registration.
- `backend/pyproject.toml` — added `pypdf`, `pillow`, `python-multipart`, `moto[s3]`; ruff `extend-immutable-calls` + mypy `ignore_missing_imports` additions.
- `backend/.env.example` — new `MAX_UPLOAD_MB`/`MAX_PDF_PAGES`/`MAX_IMAGE_PIXELS` keys.
- `backend/tests/**` — new unit tests (`engines/test_file_security.py`, `test_storage_adapter.py`) and integration tests (`api/test_documents.py`, `pipeline/test_document_tasks.py`); `tests/integration/conftest.py` gained the `_inline_document_processing`/`_mock_storage` autouse fixtures; removed `tests/integration/pipeline/.gitkeep`.
- `docs/api/openapi-v1.json` — regenerated snapshot (additive only).
- `docs/adr/ADR-013.md` — new.
- `PLAN.md` — documented the enum gap-fills (§11.3, Appendix A), added ADR-013 to the Decision Log, bumped to v1.2.0, checked off T2.1–T2.5/T2.7 in §26.3.

## Remaining work (for a FRONTEND session, T2.6)
1. Upload picker (PDF/CSV/PNG/JPEG), per-file progress, and a "processing checklist" UI polling `GET /documents/{id}/status`.
2. Contract summary (see `docs/api/openapi-v1.json` for authoritative shapes):
   - `POST /documents` — `multipart/form-data`: `file` (binary), `source_type` (enum: `BANK_API, SIGNED_STATEMENT, ORIGINAL_PDF, EXPORTED_CSV, SCREENSHOT, PHOTO`), optional `financial_account_id` (uuid), optional `pdf_password` (string, only sent when retrying after a `PDF_PASSWORD_REQUIRED`/`INVALID_PDF_PASSWORD` error — never cache/store it client-side beyond the retry attempt). → `202 {document_id, status, poll, duplicate}`.
   - `status` values relevant to the UI now: `EXTRACTING` (success, processing continues in Sprint 3), `REJECTED_SECURITY` (non-accusatory "possible security concern" messaging per PLAN §2.3 positioning guardrails — never call the user dishonest), `VALIDATION_FAILED` (oversized/corrupt — actionable retry copy), `DUPLICATE_REUSED` (silent success reuse — reserved for a future explicit re-upload path, not currently reachable via `POST /documents` since dedup returns the *same* `EXTRACTING`/terminal status the original document already has, with `duplicate: true`).
   - `415 UNSUPPORTED_MEDIA_TYPE` — wrong file type, no document created; show the accepted-types list.
   - `422 PDF_PASSWORD_REQUIRED` / `422 INVALID_PDF_PASSWORD` — prompt for a password and resubmit the *same* file bytes + `pdf_password`; no document exists yet for either case.
   - `GET /documents/{id}/status` → `200 {document_id, status, file_name, mime_type, source_type, page_count, uploaded_at}`; `404` for another user's document (deliberately indistinguishable from "doesn't exist," PLAN §18.4).
3. Do not reproduce file-security logic client-side beyond mirroring accepted-types/size-limit UX (PLAN §13.6-equivalent for uploads); the server remains the source of truth.

## Risks and failure modes
- None known for the implemented scope. The `DUPLICATE_REUSED` status value now exists in `doc_status_enum` (added for §8.2 diagram completeness) but Sprint 2's actual dedup path never assigns it to a document row — it always returns the *existing* document's real status instead, with `duplicate: true` in the response. If a future sprint wants a document to visibly carry `DUPLICATE_REUSED` as its own terminal status (rather than just signaling duplication via the response flag), that's a small, clearly-scoped follow-up, not a bug.
- `financial_accounts` has no create/list route yet — intentional Sprint 2 scope (T2.1 is model+migration only), but flag if a later sprint's iOS work expects one to already exist.

## Commands for the next agent
```bash
git checkout backend/cycle-3-upload-storage   # or main once merged
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
- Clean at time of writing this handoff — all changes above are committed on `backend/cycle-3-upload-storage` (see final report for exact commit hash and push status).
