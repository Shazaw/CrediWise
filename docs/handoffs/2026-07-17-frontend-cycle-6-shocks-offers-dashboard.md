# Handover: Cycle 6 Shocks, Offers, and Complete Dashboard

## Session scope
- Workstream: FRONTEND
- Branch: `frontend/cycle-6-shocks-offers-dashboard`
- Base commit: `f7d2b3f` (`origin/main` after Cycle 5 integration)
- Latest commit: this task's branch HEAD (see `git log -1`)
- PLAN.md sections / requirement IDs: FR-10, FR-11, FR-12, §5.7-5.9, §7.9-7.11, §13, §14, Sprint 5, T5.6, NFR-11, NFR-12

## User request
Start workflow Cycle 6 frontend work while following `PLAN.md`, `CLAUDE.md`, and `docs/development/parallel-workflow.md`, and continue until push tests are green.

## Completed
- Added a supplied-output Shock Resilience model with all seven default scenarios, temporal and monthly balances, buffer breaches, deficits, score contributions, reasons, and model lineage.
- Added bounded custom income-drop and emergency-expense controls without reproducing the backend Shock Engine.
- Added an accessible Swift Charts projection with a complete text equivalent and visible scenario metrics.
- Added server-order-preserving simulated offers with supplied safety bands, ranks, warnings, model lineage, and internally consistent synthetic loan schedules.
- Added offer list and detail screens that separate principal, net proceeds, instalments, interest, fees, total repayment, rate basis, amortization, schedule, penalty terms, essential coverage, and refinancing dependency.
- Added typed guided-flow routes from the complete four-card dashboard to shocks, offers, and dangerous-offer explanations.
- Added deterministic mock and unavailable repositories. Synthetic financial output is enabled only by `--ui-testing --cycle-6-flow`.
- Added Indonesian and English localization, VoiceOver labels, Dynamic Type layouts, semantic status labels, and positioning disclaimers.
- Added ViewModel, coordinator, loan-invariant, and synthetic golden-flow tests.

## Current state
- What is implemented: the isolated Cycle 6 UI-test flow covers financing need through upload/review/dashboard, shock simulation, safety-ranked simulated offers, and unsafe-offer detail.
- What is partially complete: frontend UI, state, navigation, and deterministic presentation fixtures are complete without a production shock/offer wire adapter.
- What is not started: Cycle 6 API DTOs, mappers, authenticated repositories, and contract tests because the authoritative OpenAPI snapshot has no shock or offer endpoints.

## Contract required from backend
1. Freeze `POST /api/v1/assessments/{id}/simulate` and `GET /api/v1/assessments/{id}/shocks`, including synchronous versus asynchronous behavior and error codes.
2. Define bounded scenario identifiers, custom income-drop and emergency-expense request fields, score precision, resilience band, score contribution, monthly projected balance, minimum temporal balance, buffer breach, deficit, status, chart timeline points, reason codes, and model version.
3. Freeze `POST/GET /api/v1/assessments/{id}/offers` and `GET /api/v1/offers/{id}/safety`, including authoritative ordering and supplied rank.
4. Define provider simulation/verification status, Safe Offer score/band, safest marker, principal, net proceeds, nominal rate and basis, effective annual cost, amortization, payment frequency/schedule, due timing, interest, upfront/financed fees, total repayment, penalty terms, remaining essential coverage, warnings, refinancing dependency, reasons, and model version.
5. Guarantee every MVP provider is labelled `SIMULATED_REGULATED_PROVIDER`, every score has at least three reason codes, and `REFINANCING_DEPENDENCY_RISK` remains a bounded warning code.
6. Keep changes additive within `/api/v1`; commit regenerated `docs/api/openapi-v1.json` and synthetic response fixtures before frontend API wiring.

## Validation evidence
- `ios/scripts/lint-positioning-copy.sh` passed locally.
- `git diff --check` passed locally.
- Localization key parity and duplicate-key validation passed for 450 keys per locale.
- Xcode project membership validation found all 24 new app files and 3 new unit-test files in the correct source phases.
- Strict SwiftLint, Xcode build-for-testing, unit tests, and UI tests are pending the first branch push to GitHub `frontend-ci`.
- Local Xcode execution is unavailable on this Linux host.

## Files changed
- `ios/CrediWise/Features/Shocks/**`: supplied-output models, repository boundary, mocks, ViewModel, sliders, card, scenario detail, and accessible chart.
- `ios/CrediWise/Features/Offers/**`: complete simulated-offer model, repository boundary, mocks, ViewModels, safety-ranked list, and cost/warning detail.
- `ios/CrediWise/Features/Dashboard/Views/AssessmentDashboardView.swift`: fourth headline card and offers action.
- `ios/CrediWise/App/**`: typed Cycle 6 routes and dependency composition.
- `ios/CrediWise/Resources/**`: Indonesian and English Cycle 6 copy.
- `ios/CrediWiseTests/**`, `ios/CrediWiseUITests/**`: regression, invariant, and synthetic-flow coverage.
- `ios/CrediWise.xcodeproj/project.pbxproj`: app and unit-test target membership.
- `ios/README.md`: Cycle 6 mock/production boundary.

## Remaining work
1. Backend publishes and tests the approved additive shock/offer contract and OpenAPI snapshot.
2. Frontend adds DTO decoding, mapper/error tests, and authenticated API repositories against that snapshot.
3. Integration runs the full synthetic end-to-end flow against the real API and validates VoiceOver on a simulator or device.

## Risks and failure modes
- Production intentionally leaves shocks/offers unavailable until the contract is frozen; it never substitutes synthetic scores or offers.
- The complete flow depends on backend-supplied ordering, bands, reason codes, warning codes, and financial values; the client must not derive them during integration.
- No raw financial document or real PII is present; all fixtures are synthetic.

## Commands for the next agent
```bash
git switch frontend/cycle-6-shocks-offers-dashboard
ios/scripts/lint-positioning-copy.sh
swiftlint lint --strict --config ios/.swiftlint.yml ios/CrediWise ios/CrediWiseTests ios/CrediWiseUITests
xcodebuild -project ios/CrediWise.xcodeproj -scheme CrediWise -destination 'platform=iOS Simulator,name=iPhone 15' CODE_SIGNING_ALLOWED=NO build-for-testing
xcodebuild -project ios/CrediWise.xcodeproj -scheme CrediWise -destination 'platform=iOS Simulator,name=iPhone 15' CODE_SIGNING_ALLOWED=NO test-without-building
```

## Do not touch
- `backend/**`; the missing contract belongs to the BACKEND workstream.
- Shared financial formulas or model thresholds merely to make frontend integration pass.

## Uncommitted state
- Expected clean after this task's commit; verify with `git status --short --branch`.
