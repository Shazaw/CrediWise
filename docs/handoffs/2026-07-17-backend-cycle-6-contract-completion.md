# Handover: Cycle 6 Backend Contract Completion

## Session Scope
- Workstream: BACKEND
- Branch: `integration/cycle-6-shocks-offers-dashboard`
- Requirements: FR-10, FR-11, FR-12, FR-15, FR-18, T5.1-T5.5

## Contract Changes
- Shock responses include proposed instalment, required buffer, per-scenario buffer breach, ordered temporal projection points, at least three structured reasons, explanation prose, and model/config lineage.
- Offer responses include strict penalty terms, annual nominal-rate basis, essential-expense coverage amount/ratio, refinancing dependency, at least three structured reasons, lineage, and explicit simulated/no-endorsement copy.
- `POST /assessments/{id}/offers` is idempotent for the canonical three-offer set.
- Decimal rates/scores remain JSON decimal strings; monetary amounts remain whole-IDR integers.

## Persistence
- Migration `0010_cycle6_contract_completion.py` adds nullable shock/offer evidence fields and nullable `canonical_template_key`; it does not backfill invented evidence.
- New canonical rows are unique by `(assessment_id, canonical_template_key)` only when simulated, active, and keyed. Duplicate/keyless 0009 history remains valid and preserved.
- Existing sets are reused only when their exact key set and count match current v2 templates. Partial sets and historical model/hash offer creation return `409 REASSESSMENT_REQUIRED`.
- Model seeding activates exact `crediwise-core` v2/hash and retires older ACTIVE rows without mutating historical version/hash values.

## Loan Mathematics
- Unfinanced upfront/service/admin fees reduce net proceeds; financed fees increase the amortized balance and repayment schedule.
- Effective annual cost is Decimal IRR over actual proceeds and complete monthly payments; late penalties remain excluded.
- Safe Offer total-cost scoring combines effective annual cost with net-proceeds/principal ratio.
- Actual safe principal is solved against each offer's own rounded schedule, tenor, rate, amortization, and fee terms.
- Effective annual cost is compared with a like-for-like effective reference for the same tenor.

## Frontend Impact
- Render `projection_points` in ascending `sequence`; do not infer temporal minimum from monthly `projected_cash_flow`.
- Treat `resilience_score_scope = CANONICAL_BATTERY` as explicit: custom outcomes are standalone and receive no invented aggregate weight.
- Treat `late_penalty_terms` as the strict typed object. `simulation_notice` retains the exact existing text for simulated responses and is nullable for future non-simulated sources.
- Repeated offer creation is safe and returns existing offer IDs.

## Validation
- Full backend suite: 318 passed, 96.21% coverage (70% gate passed).
- Unit suite: 222 passed (the earlier 221-test run measured 76.46% coverage before the final source-aware reason regression was added).
- Ruff, Black check, and mypy passed across `app` and `tests`; Python compileall passed.
- OpenAPI regenerated and exactly matches `app.openapi()`; every operation documents the standard error envelope.
- Live PostgreSQL migration `0008 -> 0009 -> 0010` passed. A populated 0009 fixture with two duplicate historical offers upgraded with both rows preserved, zero fabricated template keys, and all new legacy evidence fields null.
- Migration `0009:0010` upgrade and `0010:0009` downgrade SQL generation passed offline.
- Docker daemon was unavailable; validation used the repository's isolated PostgreSQL 16 binaries/data under `/tmp/opencode`.

## Do Not Touch
- `ios/**` was not modified.

## Git State
- Per user instruction, changes were not committed or pushed.
