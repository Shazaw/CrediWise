# Handover: Cycle 6 backend — Shocks, Offers & Full Dashboard (Sprint 5)

## Session scope
- Workstream: BACKEND
- Branch: `backend/cycle-6-shocks-offers-dashboard`
- Base commit: tip of `origin/main` at session start (`f7d2b3f`, already includes cycle 5's merged Twin/Risk/Safe Borrowing work)
- Latest commit: see `git log -1` on this branch
- PLAN.md sections / requirement IDs: §5.6 (ShockCapacity), §5.7, §5.8, §5.9, §6.4, §7.10, §8.1, §10.1, §11.3, §12.2, §15.1, §19.2, §23 (ADR-016), §24.11, §25 Sprint 5, §26.6 T5.1–T5.4/T5.7–T5.8, Appendix A corrections; FR-10, FR-11, FR-12, FR-18; CLAUDE.md §4, §7.4

## User request
Start cycle 6 backend work per `PLAN.md`/`CLAUDE.md`/`docs/development/parallel-workflow.md` — the next cycle boundary after cycle-5-twin-risk-safe-borrowing is Sprint 5: "Shock Engine, Offers, Safe Offer Score & Full Dashboard."

## Completed
- **Schema (migration `0009`):** `shock_scenarios`, `lenders`, `lender_offers`, `offer_assessments`. New enums: `shock_type_enum`, `afford_enum` (shared by shock/offer affordability columns), `offer_source_enum`, `amortization_enum`, `offer_rating_enum`; `reg_status_enum` extended with `SIMULATED_REGULATED_PROVIDER` (FR-11 AC5). `band_enum`/`freq_enum` reused as-is for `offer_assessments.shock_resilience_status`/`lender_offers.frequency`.
- **Two pure engines + one pure math module** (`app/engines/`):
  - `loan_math.py` — FLAT + REDUCING_BALANCE amortisation schedules, net disbursed amount, effective annual rate (whole-rupiah rounding remainder pushed to the final period so schedules sum exactly).
  - `shock.py` — 7-scenario battery (3 income-drop tiers + delayed income + emergency expense + income-source loss + weakest-month replay) + resilience score (0–100) + STRONG/MODERATE/FRAGILE band. `moderate_shock_capacity()` is a standalone closed-form helper exercising the same formula `safe_borrowing.py` duplicates internally (ADR-016) — golden-tested to confirm the two never disagree.
  - `offer.py` — 8 weighted PLAN §5.9 factors → Safe Offer Score, SAFE/CAUTION/UNSAFE band (computed on read, not stored), warning flags including the PLAN-mandated literal `REFINANCING_DEPENDENCY_RISK` code.
  - `safe_borrowing.py` gains a fifth `min(...)` term, `ShockCapacity`, computed in closed form from its own inputs (new `savings_buffer` field + `moderate_shock_income_drop_pct` config) — **no** `ShockEngine` dependency (PLAN §10.1). This fully closes ADR-015's Sprint 4 gap.
- **ADR-016** (new): documents the ShockCapacity closed-form derivation, the Twin→Risk→Shock(capacity)→SafeBorrowing→Shock(full battery)→Offer service-layer composition order, the `RegStatusEnum` extension, and the non-idempotent offer re-seeding simplification.
- **Services:**
  - `assessment_service.run_assessment_analysis` extended: after `SafeBorrowingEngine` produces the final `maximum_safe_instalment`, `ShockEngine` runs once more with that instalment to populate `shock_scenarios` rows and `assessments.shock_resilience_score`. New `AssessmentService.get_shock_scenarios`/`simulate_shock` methods back `GET /shocks` and `POST /simulate`.
  - New `offer_service.py` (`OfferService`): seeds 3 deterministic offers from `model_config.OFFER_TEMPLATES` against the 3 seeded `lenders`, computes each via `loan_math`, reruns `shock.run()` per offer substituting that offer's own instalment, scores via `offer.run()`, ranks by score desc / effective cost asc (§5.9), persists `lender_offers`/`offer_assessments`.
- **API/schemas:** `POST /assessments/{id}/simulate` (200, ad-hoc, never persisted), `GET /assessments/{id}/shocks` (persisted battery), `POST /assessments/{id}/offers` (201, seed/simulate), `GET /assessments/{id}/offers`, `GET /offers/{id}/safety` (new top-level `app/api/v1/offers.py` router). Dashboard's `shock_resilience` card is now populated — all 4 headline cards complete (FR-12 AC1). Shock reason codes (`SHOCK_*`) get their own card, filtered out of the Risk Band card's positive/risk lists.
- **Seed data:** `app/db/seeds/lenders.py` (3 lenders: 2 `SIMULATED_REGULATED_PROVIDER`, 1 `UNLISTED`, idempotent by name), registered in `run_seeds.py` and the integration test `db_engine` fixture.
- **PLAN.md updates:** §11.3 new-tables note, §12.2 additive-contract note, §23 Decision Log (ADR-016), §26.6 checklist (T5.1–T5.4/T5.7/T5.8 checked; T5.5 `ExplainerPort` and T5.6 iOS correctly left unchecked — see Remaining work), Appendix A corrections (see Risks below — two pre-existing PLAN.md inconsistencies found and fixed in this PR), doc version `1.4.1 -> 1.5.0`.
- **OpenAPI snapshot** regenerated (`docs/api/openapi-v1.json`) — additive only, verified programmatically (path count 21→25, no existing schema removed, `app.openapi()` output diffed against the committed file).
- **Tests:** 283 passing (up from 229 at the end of cycle 5), 1 pre-existing unrelated failure (see Validation evidence). New golden tests: `test_shock.py` (13), `test_offer.py` (19), `test_loan_math.py` (9), plus 3 new `test_safe_borrowing.py` cases for `shock_capacity` and one existing test updated (`test_high_dsti_binds_the_capacity` — the new `ShockCapacity` term changed which capacity binds for its original fixture; fixed by raising `savings_buffer`, not by weakening the assertion). New integration suite `test_shocks_offers.py` (10 tests): full pipeline through shocks/simulate/offers/safety, ranking, dangerous-offer warning flags, ownership 404s, 422 validation. All new engines at 100% line coverage; overall suite 96.09%.

## Current state
- What works: confirm → normalize → assessment (Twin → Risk → SafeBorrowing-with-ShockCapacity → full ShockEngine battery) → `COMPLETE`, fully wired end to end and exercised via real HTTP requests against a real Postgres 16 instance. `POST /assessments/{id}/offers` seeds 3 ranked offers (SAFE/CAUTION/UNSAFE spread by design — see `model_config.OFFER_TEMPLATES`); `GET /offers/{id}/safety` and dashboard's shock card both verified via integration tests. `alembic upgrade head -> downgrade -1 -> upgrade head` passes for the full `0001`–`0009` chain.
- What is partially complete: `ShockEngine`'s temporal model is monthly-aggregate scenario adjustments, not a full day-by-day dated-liquidity-timeline simulation against `cash_flow_events` (documented gap, `shock.py` module docstring + PLAN §26.6 T5.1 note). `OfferAssessment.explanation` is a minimal deterministic template string, not the full `ExplainerPort`/`ai_explanations`-flag architecture PLAN §15.5/T5.5 describes.
- What is not started: T5.5 (`ExplainerPort` provider-neutral adapter + flag) and T5.6 (iOS Shock card, Offers list, dangerous-offer detail) — T5.6 is correctly FRONTEND workstream, out of scope per CLAUDE.md §2.2/§2.3; T5.5 is a genuine backend gap for a future session, not claimed done.

## Validation evidence
- `ruff check app tests` — clean.
- `black --check app tests` — clean.
- `mypy app tests` — clean, 169 source files, no new `type: ignore` beyond the same class of justified `assert isinstance(...)` narrowing pattern already used throughout the codebase for `dict[str, object]` config reads.
- `pytest` — **283 passed**, 1 pre-existing failure (`test_config.py::test_settings_fails_fast_on_missing_required_field`), confirmed unrelated: same failure documented in the cycle-5 handoff, caused by a leftover local `backend/.env` file in this sandbox that `pydantic-settings` loads directly regardless of `monkeypatch.delenv` — not present in CI. **96.09%** overall coverage (gate 70%); `shock.py`/`offer.py`/`loan_math.py`/`safe_borrowing.py` all 100%.
- `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` — passes against a real Postgres 16.
- **Sandbox limitation (same class as cycle 5's handoff):** no Docker, no system Postgres, no `sudo` in this session's environment. Used `pgserver`'s bundled `postgres`/`pg_ctl` binaries directly, restarted with `-h 127.0.0.1 -p 5432` for a real TCP listener, and created the `crediwise`/`crediwise_test` role/databases once via `psql`.

## Files changed
- `backend/app/models/enums.py` — `ShockTypeEnum`, `AffordEnum`, `ShockResilienceBandEnum`, `OfferSourceEnum`, `AmortizationEnum`, `RegStatusEnum`, `OfferRatingEnum`, `OfferSafetyBandEnum`.
- `backend/app/models/{shock_scenario,lender,lender_offer,offer_assessment,__init__}.py` — new ORM layer.
- `backend/alembic/versions/0009_shocks_offers.py` — new migration.
- `backend/app/repositories/{shock_scenario_repository,lender_repository,lender_offer_repository,offer_assessment_repository}.py` — new.
- `backend/app/engines/{shock,offer,loan_math}.py`, `backend/app/engines/safe_borrowing.py` (ShockCapacity), `backend/app/engines/config/model_config.py` (SHOCK/OFFER config sections) — new engines + config.
- `backend/app/services/{assessment_service,offer_service}.py` — Shock stage wiring, new `OfferService`.
- `backend/app/db/seeds/{lenders,run_seeds}.py` — new seed + registration.
- `backend/app/schemas/{shock,offer}.py`, `backend/app/schemas/assessment.py` (dashboard `shock_resilience`), `backend/app/api/v1/{assessments,offers,__init__}.py` — new DTOs/routes.
- `backend/tests/unit/engines/{test_shock,test_offer,test_loan_math}.py` — new golden tests; `test_safe_borrowing.py` — updated + new `shock_capacity` cases.
- `backend/tests/integration/api/test_shocks_offers.py`, `backend/tests/integration/conftest.py` (lender seeding) — new/updated integration tests.
- `docs/adr/ADR-016.md` — new.
- `docs/api/openapi-v1.json` — regenerated (additive).
- `PLAN.md` — §11.3, §12.2, §23, §26.6, Appendix A (two pre-existing inconsistencies corrected — see Risks), doc version `1.4.1 -> 1.5.0`.

## Remaining work (mixed BACKEND follow-up + FRONTEND)
1. **T5.5 (BACKEND, next session):** build the real `ExplainerPort` (provider-neutral/local adapter + deterministic template fallback + `ai_explanations` flag, PLAN §15.5) and route `OfferAssessment.explanation`/dashboard reason-code prose through it instead of the current minimal template string.
2. **T5.6 (FRONTEND):** Shock card + interactive sliders (Swift Charts) consuming `GET /assessments/{id}/shocks` and `POST /assessments/{id}/simulate`; Offers list (colour-coded by `safety_band`) consuming `GET /assessments/{id}/offers`; dangerous-offer detail view consuming `warning_flags`/`explanation`; DisclaimerFooter on every new screen (§2.3 positioning guardrail — `positioning_notice` already on the dashboard response, not yet on offer/shock responses individually, so the client should keep showing the dashboard's notice alongside these cards).
3. **Contract summary** (see `docs/api/openapi-v1.json` for authoritative shapes): `POST /assessments/{id}/simulate` is synchronous (200) and never persisted — safe to call repeatedly for slider interactions. `POST /assessments/{id}/offers` is **not idempotent** (ADR-016) — call it once per assessment; a second call adds a second batch rather than replacing the first, so the client should only call it once (e.g. gate the button after first success) until a future session adds re-seeding semantics.
4. Every screen showing shock/offer output must keep the positioning disclaimer (§2.3) — never phrase a FRAGILE/UNSAFE result as a guarantee, and never phrase a SIMULATED offer as a real lender endorsement (`lender.regulatory_status` is explicitly `SIMULATED_REGULATED_PROVIDER`/`UNLISTED` for all three seeded lenders — none is `REGULATED`).
5. Do not reproduce Shock/Offer scoring client-side — server remains the source of truth.

## Risks and failure modes
- **Two pre-existing PLAN.md Appendix A inconsistencies found and corrected in this PR** (not introduced by this session — present in the document since before Sprint 5 began): (1) `afford_enum` was defined twice with contradictory member sets (`SURVIVABLE, STRAINED, DEFICIT` vs `SAFE, TIGHT, DEFICIT`) — the second, contradictory definition was removed; §5.8's own prose uses the first set verbatim, and this session's implementation matches it. (2) `shock_type_enum`'s placeholder (`INCOME_DROP, DELAYED_INCOME, EMERGENCY_EXPENSE, INCOME_SOURCE_LOSS, WEAKEST_MONTH, HOUSEHOLD_COST_INCREASE`) predated §5.8's fully-specified, separately-weighted scenario table and named a scenario (`HOUSEHOLD_COST_INCREASE`) that appears nowhere in §5.8's weight table — corrected to match §5.8 exactly. A future reviewer should sanity-check these corrections against the original source-of-truth intent if that's recoverable, though the fix direction (trust the detailed, weighted, cross-referenced §5.8 table over an orphaned appendix placeholder) is the only internally-consistent reading available.
- **`ShockEngine`'s per-scenario cash-flow formulas are a documented MVP modelling simplification** (ADR-016, `shock.py` module docstring), not a literal day-by-day dated-liquidity-timeline simulation — flagged inline, not silently claimed complete, same class of gap as prior sprints' documented simplifications (e.g. Sprint 3's cross-document-consistency deferral).
- **Offer re-seeding is non-idempotent** (ADR-016 Decision 5) — repeatedly calling `POST /assessments/{id}/offers` for the same assessment accumulates offer batches rather than replacing them. Low risk for the MVP demo golden path (called once) but a real gap if a future client retries this call.
- **`OfferAssessment.explanation` is not the full `ExplainerPort` architecture** — see Remaining work item 1.

## Commands for the next agent
```bash
git checkout backend/cycle-6-shocks-offers-dashboard   # or main once merged
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
- Clean at time of writing this handoff — all changes above are committed on `backend/cycle-6-shocks-offers-dashboard` (see final report for exact commit hash and push status).
