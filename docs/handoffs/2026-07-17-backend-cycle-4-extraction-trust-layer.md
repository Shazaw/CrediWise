# Handover: Cycle 4 backend — OCR/Extraction & Trust Layer / Data Confidence (Sprint 3)

## Session scope
- Workstream: BACKEND
- Branch: `backend/cycle-4-extraction-trust-layer`
- Base commit: `8c3b3f4` (== `origin/main` at session start; local `main` was 17 commits stale and was fast-forwarded to `origin/main` before branching — see "Risks" below)
- Latest commit: see `git log -1` on this branch (`cc763bc` at time of writing)
- PLAN.md sections / requirement IDs: §5.2, §7.3, §7.4, §8.2, §10.1, §11.3, §12.2, §15.1-15.3, §15.6, §16.1, §16.3, §19.2, §24.11, §25 Sprint 3, §26.4 T3.1-T3.6/T3.8; FR-4, FR-5, FR-14; CLAUDE.md §5

## User request
Start cycle 4 backend work per `PLAN.md`/`CLAUDE.md`/`docs/development/parallel-workflow.md` — the next cycle boundary after cycle-3-upload-storage is Sprint 3: "OCR, Extraction & Trust Layer (Data Confidence)."

## Completed
- **Schema (migrations `0004`, `0005`):** `document_processing_runs`, `transactions`, `document_verification_results`, `pipeline_stage_runs`, and `corrections` (brought forward from PLAN §7.13's POST-MVP tag — FR-14/T3.6's MVP review flow needs it now, documented in `app/models/correction.py` and PLAN.md). Gap-filled enums (§24.11): `processing_status_enum`, `pipeline_stage_enum` (`EXTRACTION, VERIFICATION` only — scoped to this sprint's stages), `stage_status_enum`, `dir_enum`, plus `doc_status_enum.REVIEW_PENDING` (migration `0005` — `0003` already created that type and can't be edited per §24.6, so this is `ALTER TYPE ... ADD VALUE` with a full recreate-based downgrade).
- **Extraction engine** (`app/engines/extraction/`): `pdf_parser.py` (pdfplumber text + pypdf metadata forensics — see below for the PyMuPDF substitution), `csv_parser.py`, `image_parser.py` (pure — takes already-OCR'd text, never calls Tesseract itself), `delimited_text.py` (shared `|`-delimited row grammar for the one Sprint 3 MVP fixture format), `schema.py`. Dispatcher `extract()` routes by MIME type.
- **OCR integration** (`app/integrations/ocr/`): `OcrPort` protocol + `TesseractOcrAdapter`, same override-seam pattern as `storage`. The actual `tesseract` subprocess call lives here, not in `engines/`, per PLAN §10.1 Golden Rule 3 ("engines never do I/O").
- **Local Kimi adapter scaffold** (`app/integrations/local_ai/`): `client.py`/`schemas.py`/`prompts.py`/`redaction.py`/`health.py`/`README.md` per CLAUDE.md §5's exact required layout. Strict bounded-enum schema validation, deterministic redaction, timeout+one retry, `AI_SIGNAL_UNAVAILABLE` fallback. `KIMI_BASE_URL` unset by default (port is `None`); `trust_layer.kimi_anomaly_scoring_enabled=False` in `model_config.py` by default (PLAN §15.6).
- **`TrustLayerEngine`** (`app/engines/trust_layer.py`, PLAN §5.2/§15.3): pure, 7 weighted sub-scores → `data_confidence_score` + `HIGH/MEDIUM/LOW` band + reason codes + non-accusatory recommendation (Appendix B copy). `model_config.py`'s `CONFIG` is populated for the first time (still `model_version = "v1"` — an empty bootstrap placeholder becoming real, not a released-version mutation). **Known gap:** cross-document/multi-statement consistency (§15.3 item 5) is not implemented — the engine scores one document's rows per run; flagged in PLAN.md §26.4, not silently skipped.
- **Services:** `extraction_service.py` (`EXTRACTING -> VERIFYING`/`UNSUPPORTED_FORMAT`, auto-provisions a `financial_accounts` row per ADR-014 when a document has none, filters the zero-amount opening-balance row out of `transactions` while still using it unfiltered for balance reconstruction), `verification_service.py` (`VERIFYING -> REVIEW_PENDING`, re-derives the extraction result from the same immutable raw bytes rather than persisting `PdfForensics` as a new column — see that module's docstring), `pipeline_stage_tracking.py` (shared `pipeline_stage_runs` instrumentation, both services wrapped in it). `document_service.py` gained `get_verification`, `list_transactions`, `review`, `confirm`.
- **Pipeline wiring:** `process_document` (Celery task, `app/pipeline/document_tasks.py`) now sequences `SECURITY_CHECK -> EXTRACTING -> VERIFYING -> REVIEW_PENDING` in one invocation via `run_document_pipeline`; each stage function is still its own idempotency guard (NFR-3). `tests/integration/conftest.py`'s inline-dispatch fixture updated to match.
- **Routes/schemas:** `GET /documents/{id}/verification`, `GET /documents/{id}/transactions` (cursor-paginated), `POST /documents/{id}/review` (bounded `CorrectionTypeEnum`), `POST /documents/{id}/confirm`.
- **ADR-014** (new): financial-account auto-provisioning decision (why, alternatives, consequences).
- **OpenAPI snapshot** regenerated (`docs/api/openapi-v1.json`) — additive only, diff verified by hand.
- **PLAN.md**: Appendix A enums, §11.3 table notes (including the T3.3 cross-doc gap and the `pypdf`-not-PyMuPDF substitution), §23 Decision Log (ADR-014), §26.4 checklist (T3.1-T3.6/T3.8 checked, T3.7 correctly left for FRONTEND), doc version `1.2.0 -> 1.3.0`.
- **Sprint 2 test updates:** `tests/integration/api/test_documents.py`'s blank-PDF fixtures now correctly assert `UNSUPPORTED_FORMAT` (the pipeline runs synchronously through to completion in tests now, not just to `EXTRACTING`) — documented in that file's module docstring as an intentional behavior change, not a regression.
- **Tests:** 162 passing (up from 101 at session start) — golden tests for every extraction parser (PDF/CSV/OCR-text/dispatch), `TrustLayerEngine` (12 tests: clean-HIGH, tampered-lower-with-non-accusatory-language, screenshot-no-forensics, no-balance-data, ownership match/partial/mismatch, completeness, Kimi included/unavailable/disabled, determinism, empty-rows), local-Kimi adapter (schema validation, redaction, prompt-injection-resistance assertion, override seam, `IntegrationError` on unreachable host), OCR port seam, pipeline idempotency (`run_extraction`, `run_verification`, `track_stage`), and API-level integration tests (clean-fixture happy path incl. review/confirm, single-month/no-profile MEDIUM band, cross-user 404s, bounded-correction-type 422). 95.41% overall coverage (gate 70%); `trust_layer.py` 96%, all `extraction/*` modules 92-100% (gate 90% on engines).

## Current state
- What works: upload → security → extraction (PDF/CSV/OCR-text) → Trust Layer verification → review/confirm, fully wired end to end and exercised via real HTTP requests in tests against a real Postgres 16 instance. Migration `upgrade → downgrade base → upgrade` cycle passes for the full chain (`0001`-`0005`).
- What is partially complete: `TrustLayerEngine`'s cross-document consistency (§15.3 item 5) — single-document scoring only, explicitly flagged in PLAN.md rather than silently omitted. Local Kimi page-region-image rendering is not implemented (documented in `app/integrations/local_ai/README.md`); the adapter/contract exists and is tested, but nothing renders a PDF page to an image yet, so Kimi stays practically unreachable even if `KIMI_BASE_URL` were configured — not a blocker since `kimi_anomaly_scoring_enabled=False` by default.
- What is not started: T3.7 (iOS extraction-review UI + Data Confidence card) — FRONTEND workstream, correctly out of scope for this session per CLAUDE.md §2.2/§2.3.

## Validation evidence
- `ruff check app tests` — clean.
- `black --check app tests` — clean.
- `mypy app tests` — clean (added `pytesseract.*`/`pdfplumber.*` to `ignore_missing_imports`; `app.engines.*`'s `disallow_any_explicit` override honored throughout the new engine code).
- `pytest` — **162 passed**, 3 pre-existing `test_config.py` failures (same class as documented in the Sprint 2/3 handoffs: `DB_HOST`/`DB_PORT` env leaking from this session's manual local-Postgres setup into that specific test file when run standalone in certain shells; passes in isolation with those vars unset; CI's job env doesn't have this leak). 95.41% overall coverage, 96%/92-100% on the new engines.
- `alembic upgrade head && alembic downgrade base && alembic upgrade head` — passes against a real Postgres 16 (full `0001`-`0005` chain, not just the newest migration).
- **Known sandbox limitation (same class as Sprint 2/3's):** no Docker/system Postgres/Redis/MinIO/Tesseract binary, no `sudo`, in this session's environment. Used the same `pgserver`-bundled `postgres` binary directly in TCP-only mode (`-h 127.0.0.1 -p 5433 -k ''`) as prior sprints. **New this sprint:** the integration test suite's session-scoped `db_engine` fixture (`tests/integration/conftest.py`) calls `Base.metadata.drop_all(engine)` at teardown, which also drops the native Postgres enum types SQLAlchemy manages — running `pytest` therefore leaves the manually-migrated schema in a state where `alembic_version` still says "head" but the actual tables/types are gone. Always re-run `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` + `alembic upgrade head` before manual DB inspection after a `pytest` run; this doesn't affect CI (which provisions a fresh `postgres:16` container per job). **No Tesseract binary is installed** in this repo's CI image either (`.github/workflows/backend-ci.yml` has no `apt-get install tesseract-ocr` step) — the OCR path is entirely gated behind `OcrPort`/`get_ocr_port`/`set_ocr_port`, so the gate test suite never invokes the real binary (`app/integrations/ocr/tesseract_adapter.py` is exercised only via error-path tests on bytes guaranteed to fail before any subprocess call). If a future sprint wants real OCR gate coverage, CI needs a `tesseract-ocr` apt step first.
- `tests/integration/conftest.py`'s `db_engine` fixture now also runs `app.db.seeds.model_versions.run()` after `create_all` — verification requires an ACTIVE `model_versions` row (§19.2) that the fixture previously never seeded (no prior Sprint's tests needed one).

## Files changed
- `backend/app/models/{enums,document_processing_run,transaction,document_verification_result,pipeline_stage_run,correction,__init__}.py` — new/updated ORM layer.
- `backend/alembic/versions/{0004_extraction_trust_layer,0005_review_pending_status}.py` — new migrations.
- `backend/app/repositories/{document_processing_run_repository,transaction_repository,document_verification_result_repository,pipeline_stage_run_repository,correction_repository,model_version_repository,financial_account_repository}.py` — new/updated.
- `backend/app/engines/extraction/{__init__,schema,delimited_text,pdf_parser,csv_parser,image_parser}.py` — new.
- `backend/app/engines/trust_layer.py`, `backend/app/engines/config/model_config.py` — new engine + populated config.
- `backend/app/integrations/ocr/{__init__,port,tesseract_adapter}.py` — new.
- `backend/app/integrations/local_ai/{__init__,client,schemas,prompts,redaction,health,README.md}` — new.
- `backend/app/services/{extraction_service,verification_service,pipeline_stage_tracking,document_service}.py` — new/updated.
- `backend/app/pipeline/document_tasks.py` — sequences the full stage chain.
- `backend/app/schemas/document.py`, `backend/app/api/v1/documents.py` — new DTOs/routes.
- `backend/app/core/config.py`, `backend/.env.example` — `KIMI_*` settings.
- `backend/pyproject.toml` — added `pdfplumber`, `pytesseract`, `httpx`; mypy `ignore_missing_imports` additions.
- `backend/tests/support/{__init__,pdf_builder}.py` — new shared in-process PDF fixture builder.
- `backend/tests/unit/engines/{test_trust_layer,extraction/*}.py`, `backend/tests/unit/{test_ocr_port,test_local_ai}.py` — new unit/golden tests.
- `backend/tests/integration/api/{test_documents,test_documents_review}.py`, `backend/tests/integration/pipeline/{test_extraction_service,test_verification_service,test_pipeline_stage_tracking}.py`, `backend/tests/integration/conftest.py` — new/updated integration tests.
- `docs/adr/ADR-014.md` — new.
- `docs/api/openapi-v1.json` — regenerated (additive).
- `PLAN.md` — Appendix A, §11.3, §23, §26.4, doc version 1.2.0 → 1.3.0.

## Remaining work (for a FRONTEND session, T3.7)
1. Extraction review/correction/confirmation screen + Data Confidence subdimension card/drill-down.
2. Contract summary (see `docs/api/openapi-v1.json` for authoritative shapes):
   - `GET /documents/{id}/verification` → `200 {document_id, data_confidence_score, band, provenance_score, consistency_score, metadata_score, ocr_score, visual_score, completeness_score, ownership_score, reason_codes: [{code, description}], recommendation, verified_at}`. `404` before verification completes.
   - `GET /documents/{id}/transactions?limit=&cursor=` → `200 {items: [{transaction_id, transaction_date, transaction_time, amount, direction, balance_after, raw_description, category, transaction_context, is_internal_transfer, is_recurring, extraction_confidence}], next_cursor}`. `category`/`transaction_context` are `UNKNOWN` until Sprint 4's `NormalizationEngine` ships — render accordingly, not as an error state.
   - `POST /documents/{id}/review` — body `{corrections: [{transaction_id, correction_type, note}]}`, `correction_type` one of `INCORRECT_AMOUNT, WRONG_CATEGORY, INTERNAL_TRANSFER, DUPLICATE, MISSING_ROW, OWNERSHIP_CONCERN, OTHER`. Only valid while status is `REVIEW_PENDING` (`422 VALIDATION_ERROR` otherwise). Response `{document_id, corrections_recorded}`.
   - `POST /documents/{id}/confirm` — transitions `REVIEW_PENDING -> NORMALIZING`. Response `{document_id, status}`. Same `422` guard.
   - `status` values relevant now: `VERIFYING` (processing, poll), `REVIEW_PENDING` (verification done, show Data Confidence + review/confirm UI), `UNSUPPORTED_FORMAT` (non-accusatory "we couldn't read this layout" messaging, §2.3), `NORMALIZING` (confirmed, Sprint 4 continues from here — no UI action yet).
3. Every screen showing `data_confidence_score`/`band`/`recommendation` must keep the positioning disclaimer (§2.3, Appendix B) — never phrase LOW/MEDIUM as "fake" or "dishonest."
4. Do not reproduce Trust Layer scoring client-side — the server remains the source of truth (PLAN §13.6-equivalent).

## Risks and failure modes
- **Cross-document consistency gap** (see above): if a user uploads multiple overlapping-period statements, the current engine won't detect closing↔opening mismatches or duplicate coverage across documents. Each document is still individually scored correctly; this is a missing *additional* signal, not an incorrect one.
- **Local `main` branch drift:** at session start, local `main` was 17 commits behind `origin/main` (origin already had cycle-3's integration merged via PR #7; local `main` had never been fast-forwarded). Fast-forwarded it before branching — no conflicts, `git merge --ff-only` succeeded cleanly. Future sessions should `git fetch && git status --short --branch` on `main` before assuming it's current.
- Local financial-account auto-provisioning (ADR-014) collapses multiple real-world accounts of the same declared `source_type` into one `financial_accounts` row per user — documented limitation, not a Sprint 3 blocker (see ADR-014's Consequences section).
- `document_service.py::get_verification` returns `404 NOT_FOUND` (not a distinct "pending" status) when called before verification completes — a reasonable, simple choice, but worth a second look if the iOS polling UX wants to distinguish "still processing" from "truly not found."

## Commands for the next agent
```bash
git checkout backend/cycle-4-extraction-trust-layer   # or main once merged
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
- Clean at time of writing this handoff — all changes above are committed on `backend/cycle-4-extraction-trust-layer` (see final report for exact commit hash and push status).
