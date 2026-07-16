# Handover: Cycle 4 Extraction Review and Data Confidence

## Session scope
- Workstream: FRONTEND
- Branch: `frontend/cycle-4-extraction-confidence`
- Base commit: `8c3b3f4` (`origin/main` after Cycle 3 integration)
- Latest commit: this task's branch HEAD (see `git log -1`)
- PLAN.md sections / requirement IDs: FR-5, FR-14, §7.4, §13, §14, Sprint 3, T3.7, NFR-11, NFR-12

## User request
Start Cycle 4 frontend work while following `PLAN.md`, `CLAUDE.md`, and the parallel workflow.

## Completed
- Added a contract-independent extraction-review domain model and repository protocol.
- Added review UI for source versus normalized evidence, proposed date/description/amount/category/internal-transfer/duplicate corrections, missing-row reporting, and ownership confirmation or concern reporting.
- Kept raw and normalized evidence immutable; only the proposal layer changes.
- Added conflict-safe confirmation states: invalid visible fields block submission, changed reviews reload, and already-confirmed responses continue idempotently.
- Added a Data Confidence card and drill-down that render a supplied score, band, seven generic dimensions, at least three reasons, deterministic/local-AI attribution, recommendation, and model version without recalculating scores.
- Added Indonesian-primary and English-fallback localization, Dynamic Type-compatible layouts, VoiceOver labels/focus, and approved positioning disclaimers.
- Added deterministic mock and unavailable repositories. Production uses the unavailable adapter until an approved contract exists.
- Added ViewModel, formatter, coordinator, and synthetic UI-flow tests.

## Current state
- What works: `REVIEW_PENDING` can route the synthetic UI-test flow through review, confirmation, Data Confidence, and the explanation drill-down.
- What is partially complete: frontend UI/state/navigation is complete against deterministic presentation fixtures.
- What is not started: API DTOs and `APIDocumentVerificationRepository`, because the Cycle 4 OpenAPI contract has not been published.

## Contract required from backend
1. Add the exact `REVIEW_PENDING` asynchronous state to the authoritative status schema, or publish the approved replacement transition.
2. Define transaction-review reads: path, ordering/pagination, row ID, raw and normalized date/description/amount/category, internal-transfer and duplicate flags, field/row confidence, owner values, period, and processing-run/version identifiers.
3. Define correction writes with bounded editable-field enums, whole-IDR validation, missing-row reporting, ownership-confirmed versus ownership-concern semantics, and immutable raw-evidence guarantees.
4. Define confirmation idempotency, optimistic concurrency/version precondition, `REVIEW_CHANGED`, `ALREADY_CONFIRMED`, ownership/authorization behavior, audit result, and the next processing state.
5. Define Data Confidence reads: score precision, band, generic dimension IDs/titles/scores, at least three reason codes, recommendation, model version, and deterministic versus local-AI evidence attribution.
6. Keep changes additive within `/api/v1`; commit the regenerated `docs/api/openapi-v1.json` and synthetic response fixtures before frontend API wiring.

## Validation evidence
- `sh ios/scripts/lint-positioning-copy.sh` passed.
- Strict SwiftLint passed with 0 violations across 84 Swift files.
- `git diff --check` passed.
- Static code review found no remaining code issue after correction-integrity, conflict-reload, ownership-concern, date-correction, and accessibility-focus fixes.
- GitHub `frontend-ci` run `29538765589` passed on macOS: simulator selection/boot, Xcode build-for-testing, unit tests, and UI tests.
- Local Xcode execution remains unavailable on this Linux host; CI provides the required macOS validation evidence.

## Files changed
- `ios/CrediWise/Features/Upload/**`: extraction review model, repository boundary, mocks, ViewModel, and views.
- `ios/CrediWise/Features/Dashboard/**`: Data Confidence presentation model, ViewModel, card, and detail view.
- `ios/CrediWise/App/**`: typed review/confidence routes and dependency wiring.
- `ios/CrediWise/Core/Utils/IDRFormatter.swift`: deterministic whole-rupiah display.
- `ios/CrediWise/Resources/**`: Indonesian and English review/confidence copy.
- `ios/CrediWiseTests/**`, `ios/CrediWiseUITests/**`: regression and synthetic flow coverage.
- `ios/CrediWise.xcodeproj/project.pbxproj`: app/test target membership.
- `ios/README.md`: Cycle 4 boundary and mock launch mode.

## Remaining work
1. Backend publishes and tests the approved additive contract and OpenAPI snapshot.
2. Frontend adds DTO decoding/error mapping tests and an authenticated API repository against that snapshot.
3. Integration runs the synthetic end-to-end flow against the real API and validates VoiceOver on a simulator/device.

## Risks and failure modes
- The committed OpenAPI snapshot currently has no review, correction, confirmation, or Data Confidence surface and omits `REVIEW_PENDING`; production therefore intentionally stops at the unavailable adapter.
- Swift compilation and simulator tests require macOS/Xcode evidence before this branch can pass the full integration gate.
- No raw financial document or real PII is present; all mock values are synthetic.

## Commands for the next agent
```bash
git switch frontend/cycle-4-extraction-confidence
sh ios/scripts/lint-positioning-copy.sh
swiftlint lint --strict --config ios/.swiftlint.yml ios/CrediWise ios/CrediWiseTests ios/CrediWiseUITests
xcodebuild -project ios/CrediWise.xcodeproj -scheme CrediWise -destination 'platform=iOS Simulator,name=iPhone 15' CODE_SIGNING_ALLOWED=NO build-for-testing
xcodebuild -project ios/CrediWise.xcodeproj -scheme CrediWise -destination 'platform=iOS Simulator,name=iPhone 15' CODE_SIGNING_ALLOWED=NO test-without-building
```

## Do not touch
- `backend/**`; the missing contract belongs to the BACKEND workstream.
- Unrelated Cycle 5 dashboard, financial-engine, shock, and offer files.

## Uncommitted state
- Expected clean after the Cycle 4 task commit; verify with `git status --short --branch`.
