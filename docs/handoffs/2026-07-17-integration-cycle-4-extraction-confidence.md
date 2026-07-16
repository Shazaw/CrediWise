# Handover: Cycle 4 Extraction Review Integration

## Session scope
- Workstream: INTEGRATION (explicitly authorized backend and frontend contract wiring)
- Branch: `integration/cycle-4-extraction-confidence`
- Base commit: `eba25db9f09feb61e227dc57c7a8be210cf44ecd`
- Integrated code commit: `3436fa1a028f5861abbe375b0b29b7cfbad99145`
- PLAN.md sections / requirements: FR-5, FR-14, sections 6.4, 12.2, 15.3

## User request
Complete Cycle 4 integration by wiring the iOS extraction-review and Data Confidence flow to the backend contract and validate merge readiness.

## Completed
- Added additive document status, transaction, review-correction, and verification fields to the versioned backend contract and OpenAPI snapshot.
- Persisted the deterministic duplicate-row signal with migration `0006`; duplicate detection uses the same pure identity rule as the Trust Layer.
- Preserved structured raw/system/user-proposed correction lineage and rejected transaction IDs belonging to another document.
- Added an authenticated iOS repository that loads all transaction pages, submits corrections before confirmation, and maps server-supplied Trust Layer scores without recalculation.
- Replaced the production unavailable repository with the API implementation while retaining deterministic UI-test fixtures.
- Added backend integration/unit coverage and iOS HTTP contract tests.

## Current state
- Cycle 4 production API wiring is complete.
- Backend and frontend CI pass on the integrated code commit.
- The integration branch is ready for normal review and merge into `main`.

## Validation evidence
- Backend local: Ruff, Black, and mypy passed.
- Backend local: `166 passed`, 95.41% coverage, including migration `0006`.
- Backend authorization regression: `7 passed` for `test_documents_review.py`.
- Frontend local: strict SwiftLint passed with zero violations; positioning-copy and localization-key parity checks passed.
- Backend CI: [run 29542552567](https://github.com/Shazaw/CrediWise/actions/runs/29542552567), success.
- Frontend CI: [run 29542552601](https://github.com/Shazaw/CrediWise/actions/runs/29542552601), success, including Xcode build, unit tests, and UI tests.

## Files changed
- `backend/app/schemas/document.py`: additive Cycle 4 request/response fields.
- `backend/app/services/document_service.py`: correction lineage persistence and document/transaction ownership validation.
- `backend/app/engines/extraction/schema.py`: shared pure duplicate-row rule.
- `backend/alembic/versions/0006_transaction_duplicate_signal.py`: persisted duplicate signal.
- `docs/api/openapi-v1.json`: authoritative additive HTTP contract.
- `ios/CrediWise/Features/Upload/Repositories/APIDocumentVerificationRepository.swift`: authenticated review/confirm/confidence API flow.
- `ios/CrediWise/Features/Upload/Repositories/DocumentVerificationDTOs.swift`: exact wire DTOs.
- `ios/CrediWise/Features/Upload/Repositories/DocumentVerificationMapper.swift`: deterministic wire-to-domain mapping.
- `ios/CrediWise/App/AppContainer.swift`: production repository wiring.

## Remaining work
1. Review and merge `integration/cycle-4-extraction-confidence` into `main` using the normal protected-branch process.
2. Run `alembic upgrade head` during the next backend deployment before serving the new transaction response.

## Risks and failure modes
- Account-owner source text remains optional in iOS because the committed status contract does not expose it; the UI states that it is unavailable instead of fabricating a value.
- The adapter fails closed if confirmation is attempted without its loaded review snapshot.
- Local AI remains optional and separately attributed; unavailable inference does not block deterministic verification.

## Commands for the next agent
```bash
git switch integration/cycle-4-extraction-confidence
git pull --ff-only
cd backend && .venv/bin/alembic upgrade head
```

## Do not touch
- Do not edit either Cycle 4 source branch after integration; continue from the integration branch or its eventual merge commit.

## Uncommitted state
- Clean.
