# Handover: Cycle 5 backend — Digital Twin, Risk & Safe Borrowing (Sprint 4)

## Session scope
- Workstream: BACKEND
- Branch: `backend/cycle-5-twin-risk-safe-borrowing`
- Base commit: tip of `integration/cycle-4-extraction-confidence` at session start (`0aa76fd`) — `main` was 16 commits stale (cycle 4 not yet merged there), so this branched off the integration branch, not `main`, per `parallel-workflow.md`'s "merged main commit becomes the next shared base" once that merge actually lands.
- Latest commit: see `git log -1` on this branch
- PLAN.md sections / requirement IDs: §5.1, §5.3–§5.7, §6.4, §7.5–§7.9, §8.2, §8.3, §10.1, §11.3, §12.2, §15.1, §19.2, §24.11, §25 Sprint 4, §26.5 T4.1–T4.6/T4.8; FR-6, FR-7, FR-8, FR-9, FR-12, FR-18; CLAUDE.md §4, §7.4

## User request
Start cycle 5 backend work per `PLAN.md`/`CLAUDE.md`/`docs/development/parallel-workflow.md` — the next cycle boundary after cycle-4-extraction-confidence is Sprint 4: "Normalization, Cash-Flow Twin, Risk & Safe Borrowing."

## Completed
- **Schema (migration `0007`):** `financing_needs`, `assessments`, `assessment_documents`, `assessment_transactions`, `assessment_input_snapshots`, `financial_profiles`, `monthly_cash_flow_snapshots`, `income_sources`, `recurring_series`, `cash_flow_events`, `assessment_reason_codes`; `pipeline_stage_runs.assessment_id` (expand pattern); `pipeline_stage_enum` gains `NORMALIZATION`/`ANALYSIS` (`ALTER TYPE ... ADD VALUE`, same pattern as migration `0005`'s `doc_status_enum.REVIEW_PENDING`). Gap-filled enums (§24.11): `urgency_enum`, `income_source_enum`, `recurring_type_enum`, `cash_event_enum`, `coverage_enum`, `inclusion_enum`, `severity_enum`.
- **Four pure engines** (`app/engines/`), each with typed `Input`/`Config`/`Result` dataclasses, `default_config()` reading `model_config.CONFIG`, and reason codes:
  - `normalization.py`: keyword-rule categorization (direction-sensitive), cross-account internal-transfer pairing (date-window + equal-amount), recurring-series detection (occurrence count + amount-variance + interval-regularity thresholds), merchant normalization (regex strip).
  - `cash_flow_twin.py`: `FinancialProfileResult` (avg/median income, volatility, essential/discretionary/business expenses, existing debt, free cash flow, weakest month, coverage flag) + monthly snapshots + income sources + cash-flow events. Reconstructs the first covered month's opening balance from the earliest dated row (`Previous = balance_after - signed(amount)`) rather than defaulting to `0`, since the statement's zero-amount anchor row never becomes a `transactions` row (Sprint 3).
  - `risk.py`: composite band (income stability 30% / cash-flow health 30% / obligation load 25% / behaviour 15%, §5.3 weights/DSTI/cash-flow-ratio thresholds) + model confidence computed separately (FR-8 AC2: thin data never reports HIGH confidence) + forced `INSUFFICIENT_DATA` on LOW data confidence or <2 months coverage.
  - `safe_borrowing.py`: `RequiredLiquidityBuffer`/`BaseCapacity`/`DSTICapacity`/`WeakestMonthCapacity`/`TemporalLiquidityCapacity` (§5.6), tenor selection from `{6,9,12}` at the 24%/year flat reference rate (§5.7), due-date window from the dominant income source. **`ShockCapacity` intentionally omitted** — see ADR-015.
  - `model_config.py` gains `normalization`/`cash_flow_twin`/`risk`/`safe_borrowing` config sections under the same `MODEL_VERSION = "v1"` (net-new keys, not a change to any number `trust_layer` already shipped — verified the seed script and test fixtures compute `config_hash()` fresh each time, no hardcoded historical hash anywhere).
- **Services / pipeline wiring:**
  - `normalization_service.run_normalization` (new `NORMALIZATION` stage): re-derives categorization over *every* active transaction the user owns (not just the triggering document's rows) so cross-account internal-transfer detection works; upserts `recurring_series` by `(user_id, financial_account_id, series_type, normalized_counterparty)` identity.
  - `assessment_service.py`: `AssessmentService` (class — `create`/`get`/`get_twin`/`get_reason_codes`/`get_lineage`) + module-level `run_assessment_analysis` (new `ANALYSIS` stage — runs Twin → Risk → SafeBorrowing, persists results, flips assessment to `COMPLETE` and included documents `ANALYZING -> COMPLETE`).
  - `financing_need_service.py`: straightforward create/list.
  - `pipeline/assessment_tasks.py` (new Celery task) + `pipeline/dispatch.py` gained `dispatch_document_normalization`/`dispatch_assessment_analysis` overridable seams (same pattern as the existing `dispatch_document_processing`). `DocumentService.confirm()` now dispatches normalization after flipping to `NORMALIZING`.
  - `tests/integration/conftest.py` gained `_inline_normalization_and_analysis` (mirrors `_inline_document_processing`) so both new stages run synchronously in gate tests — **this changes `test_confirm_transitions_to_normalizing`'s expected final status from `NORMALIZING` to `ANALYZING`** (renamed, documented inline; the confirm() call itself still returns `NORMALIZING` from the DB write, but the dispatched stage completes within the same request in tests).
- **API/schemas:** `POST/GET /financing-needs`, `POST /assessments`, `GET /assessments/{id}[/twin|/recommendation|/dashboard|/lineage]`. Dashboard reuses `assessment_reason_codes` (grouped by `POSITIVE`/`RISK`/`DATA_QUALITY`) for the "reasons" lists rather than re-deriving them from per-document Trust Layer detail — a documented simplification (§24.11 style), not a bug: per-document detail is still available via the existing `GET /documents/{id}/verification`.
- **ADR-015** (new): the `ShockCapacity` omission and the `NORMALIZATION`/`ANALYSIS` stage split.
- **OpenAPI snapshot** regenerated (`docs/api/openapi-v1.json`) — additive only, verified programmatically (`app.openapi()` output diffed against the committed file).
- **PLAN.md**: Appendix A enums, §11.3 notes (`pipeline_stage_runs`, new Sprint 4 tables), §12.2 additive-contract note, §23 Decision Log (ADR-015), §26.5 checklist (T4.1–T4.6/T4.8 checked, T4.7 correctly left for FRONTEND), doc version `1.3.1 -> 1.4.0`.
- **Tests:** 230 total in the suite (up from ~162 at the end of cycle 4), 229 passing. Golden tests: `normalization.py` 14 tests, `cash_flow_twin.py` 12, `risk.py` 13, `safe_borrowing.py` 16 — covering boundary/rounding/insufficient-data/zero-cash-flow cases per CLAUDE.md §7.4. Integration: `test_financing_needs.py` (4 tests), `test_assessments.py` (7 tests — full pipeline happy path asserting exact Twin/Risk/SafeBorrowing numbers on a hand-traced 2-month fixture, zero-free-cash-flow → `Rp0` safe amount, ownership/validation 404/422 cases). **95.46% overall coverage** (gate 70%); all four new engines ≥96% (gate 90% on engines).

## Current state
- What works: confirm → normalize (categorize/internal-transfer/recurring) → create assessment (freeze snapshot) → analyze (Twin → Risk → SafeBorrowing) → dashboard/twin/recommendation/lineage reads, fully wired end to end and exercised via real HTTP requests against a real Postgres 16 instance in this session (see "Validation evidence" for how). `alembic upgrade head -> downgrade -1 -> upgrade head` passes for the full `0001`-`0007` chain.
- What is partially complete: `SafeBorrowingEngine`'s `MaximumSafeInstalment` omits `ShockCapacity` (ADR-015) — the four implemented terms are a documented conservative upper bound; Sprint 5 adding the fifth term can only tighten the number further, never loosen it. `assessments.shock_resilience_score` stays `NULL`; no offers exist yet.
- What is not started: T4.7 (iOS financing-need form + dashboard/twin summary + improvement plan) — FRONTEND workstream, correctly out of scope for this session per CLAUDE.md §2.2/§2.3.

## Validation evidence
- `ruff check .` — clean (whole repo tree).
- `mypy app/` — clean, 113 source files, no `type: ignore` beyond one justified `Protocol`+`cast` pair for combining three structurally-identical-but-distinct engine `ReasonCode` dataclasses (see `assessment_service.py`'s `_ReasonCodeLike`).
- `pytest` — **229 passed**, 1 pre-existing failure (`test_config.py::test_settings_fails_fast_on_missing_required_field`) confirmed unrelated to this session's changes via `git stash` before starting (same failure reproduces on the unmodified base commit) — caused by a leftover local `backend/.env` file in this sandbox that `pydantic-settings` loads directly regardless of `monkeypatch.delenv`, not present in CI. **95.46%** overall coverage; `normalization.py` 97%, `cash_flow_twin.py` 99%, `risk.py` 96%, `safe_borrowing.py` 100%.
- `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` — passes against a real Postgres 16.
- **Sandbox limitation (same class as prior sprints' handoffs):** no Docker, no system Postgres, no `sudo` (interactive auth required, unavailable non-interactively) in this session's environment. Used the `pgserver` PyPI package's bundled `postgres`/`pg_ctl` binaries directly — `pgserver.get_server()` itself hardcodes `-h ""` (Unix-socket-only, no TCP) on Linux, so this session stopped that instance and re-started the same already-`initdb`'d data directory manually via `pg_ctl ... -o "-h 127.0.0.1 -p 5432" start` to get a real TCP listener for the standard `postgresql+psycopg://` connection string `app/core/config.py` builds. `psycopg2-binary`/`pgserver` were already present in `.venv` (evidently provisioned for exactly this purpose in earlier sessions) — only needed to create the `crediwise`/`crediwise_test` role and database once.

## Files changed
- `backend/app/models/{enums,pipeline_stage_run,__init__}.py` — enum additions, `assessment_id` column.
- `backend/app/models/{financing_need,assessment,assessment_document,assessment_transaction,assessment_input_snapshot,financial_profile,monthly_cash_flow_snapshot,income_source,recurring_series,cash_flow_event,assessment_reason_code}.py` — new ORM layer.
- `backend/alembic/versions/0007_twin_risk_safe_borrowing.py` — new migration.
- `backend/app/repositories/{financing_need_repository,assessment_repository,financial_profile_repository,recurring_series_repository,assessment_reason_code_repository,transaction_repository,document_verification_result_repository,pipeline_stage_run_repository}.py` — new/updated.
- `backend/app/engines/{normalization,cash_flow_twin,risk,safe_borrowing}.py`, `backend/app/engines/config/model_config.py` — new engines + populated config.
- `backend/app/services/{normalization_service,assessment_service,financing_need_service,document_service,pipeline_stage_tracking}.py` — new/updated.
- `backend/app/pipeline/{assessment_tasks,document_tasks,dispatch}.py` — new task + overridable dispatch seams.
- `backend/app/schemas/{financing_need,assessment}.py`, `backend/app/api/v1/{financing_needs,assessments,__init__}.py` — new DTOs/routes.
- `backend/tests/unit/engines/{test_normalization,test_cash_flow_twin,test_risk,test_safe_borrowing}.py` — new golden tests.
- `backend/tests/integration/api/{test_financing_needs,test_assessments,test_documents_review}.py`, `backend/tests/integration/conftest.py` — new/updated integration tests + fixtures.
- `docs/adr/ADR-015.md` — new.
- `docs/api/openapi-v1.json` — regenerated (additive).
- `PLAN.md` — Appendix A, §11.3, §12.2, §23, §26.5, doc version 1.3.1 → 1.4.0.

## Remaining work (for a FRONTEND session, T4.7)
1. Financing-need form (amount/purpose/tenor/urgency/notes → `POST /financing-needs`).
2. Dashboard screen consuming `GET /assessments/{id}/dashboard`: 4 cards (Data Confidence, Risk Band, Safe Borrowing — Shock card is Sprint 5) + Twin summary section (`GET /assessments/{id}/twin` for the drill-down).
3. Financial Health Improvement Plan surfaced from `GET /assessments/{id}/recommendation`'s `reason_codes` (currently only `SAFE_BORROWING_*` codes; broader recommendation copy is a later-sprint concern per §17's Financial Health rules).
4. Contract summary (see `docs/api/openapi-v1.json` for authoritative shapes): `POST /assessments` returns `202 {assessment_id, status, poll}`; poll `GET /assessments/{id}` until `status == "COMPLETE"` (mirrors the existing document-status polling pattern, §13.4). `twin` in the dashboard payload is `null` until analysis completes — render a loading state, not an error, when it's `null` but `status` is `PENDING`/`ANALYZING`.
5. Every screen showing risk/safe-borrowing output must keep the positioning disclaimer (§2.3, `positioning_notice` field on the dashboard response) — never phrase a low band as a guarantee or an official score.
6. Do not reproduce Twin/Risk/SafeBorrowing calculations client-side — server remains the source of truth.

## Risks and failure modes
- **`ShockCapacity` gap** (ADR-015): `maximum_safe_instalment`/`safe_loan_amount` will only get smaller once Sprint 5 wires `ShockEngine` into the same formula — do not treat Sprint 4's numbers as final in any UI copy that implies permanence.
- **Assessment-level Data Confidence aggregation** is a simple mean across included documents' latest verification results — reasonable for the single-document golden path, not deeply validated for multi-document assessments with divergent confidence levels (same class of gap as Sprint 3's cross-document-consistency note).
- **`_classify_reason` heuristic** (`assessment_service.py`) maps each engine's own reason-code naming convention to `reason_type`/`severity` via substring matching (documented inline) — reasonable now, but any future engine reason-code renaming should double-check this mapping doesn't silently miscategorize.
- **Local `main` branch drift** (same as prior handoffs): `main` was 16 commits behind `origin/main`/this integration branch at session start (cycle 4's PR not yet merged to `main`). Branched off `integration/cycle-4-extraction-confidence` instead — future sessions should confirm which branch is actually the intended base before assuming `main` is current.

## Commands for the next agent
```bash
git checkout backend/cycle-5-twin-risk-safe-borrowing   # or main once merged
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
- Clean at time of writing this handoff — all changes above are committed on `backend/cycle-5-twin-risk-safe-borrowing` (see final report for exact commit hash and push status).
