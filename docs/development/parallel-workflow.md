# Parallel Backend and Frontend Workflow

This workflow lets one backend contributor and one frontend contributor work
at the same time without editing the same modules. After each cycle, their work
is integrated and validated before the next cycle starts.

The native app under `ios/` is the CrediWise frontend. A separate web frontend
is not part of the MVP architecture in `PLAN.md`.

## Ownership

| Contributor | Owns | Must not edit |
|-------------|------|---------------|
| Backend | `backend/**`, backend tests, migrations, backend CI, and authoritative OpenAPI snapshots | `ios/**`, Swift, Xcode files, localizations, frontend tests |
| Frontend | `ios/**`, SwiftUI, API client DTOs from an approved contract, localizations, and frontend tests | `backend/**`, database models, migrations, FastAPI routes, workers, engines |
| Integration | Explicitly authorized cross-stack fixes after both branches are complete | Unrelated feature or architecture changes |

Shared root files are changed during cycle planning or integration, not by both
contributors in parallel. `PLAN.md` remains the architecture authority.

## Phase 1: Contract Freeze

Before the contributors split:

1. Choose the cycle scope and acceptance criteria from `PLAN.md`.
2. Record the shared base commit.
3. Agree endpoint paths, methods, request and response fields, error codes, and asynchronous states.
4. Commit the approved OpenAPI snapshot under `docs/api/` when available.
5. Prepare synthetic response fixtures for frontend mocks without real financial data.
6. Identify any shared files and assign one owner for the cycle.

The frontend must not guess missing contract fields. If a contract is not ready,
frontend work is limited to independent UI, state, navigation, and mockable
protocols until the backend publishes the contract.

## Phase 2: Parallel Implementation

Create separate branches or worktrees from the recorded base commit:

```text
backend/<cycle>-<feature>
frontend/<cycle>-<feature>
```

The backend contributor:

1. Implements models, repositories, deterministic engines, services, schemas, and routes in the order required by `PLAN.md`.
2. Keeps contract changes additive within `/api/v1`.
3. Updates `docs/api/openapi-v1.json` and writes frontend impact to `docs/handoffs/` when the contract changes.
4. Runs backend tests, migration checks, and contract checks.
5. Commits and pushes only backend-owned work and assigned shared artifacts.

The frontend contributor:

1. Implements API DTOs, repository protocols, ViewModels, Views, coordinators, accessibility, and localization under `ios/**`.
2. Uses deterministic mock repositories whose payloads match the approved OpenAPI contract.
3. Does not reproduce backend scoring or financial rules.
4. Documents missing contract requirements in `docs/handoffs/` instead of editing the backend.
5. Runs frontend unit, snapshot, and UI tests.
6. Commits and pushes only frontend-owned work and assigned frontend documentation.

Neither contributor merges assumptions from the other person's uncommitted
working tree. Shared information must be committed and pushed.

## Phase 3: Integration

Create an integration branch from the original cycle base:

```text
integration/<cycle>-<feature>
```

Integrate in this order:

1. Merge the completed backend branch.
2. Verify migrations, backend tests, and the committed OpenAPI snapshot.
3. Merge the completed frontend branch.
4. Point the frontend test configuration at the integrated API.
5. Run contract tests to confirm frontend DTOs decode current backend responses.
6. Run the affected end-to-end flow with synthetic fixtures.
7. Fix only integration defects, contract adapters, and wiring on the integration branch.
8. Merge the validated integration branch to `main` through a pull request.

The integration owner may edit both workstreams only for this explicitly
authorized integration phase. Product rules, financial formulas, or database
meaning must not be changed merely to make integration pass.

## Start the Next Cycle

The merged `main` commit becomes the next shared base. Repeat contract freeze,
parallel implementation, and integration for the next vertical product slice.

Good cycle boundaries follow the roadmap:

1. Foundation and application shells.
2. Authentication, profiles, and session handling.
3. Secure upload and processing status.
4. Extraction review and Data Confidence.
5. Digital Twin, risk, and safe borrowing.
6. Shocks, offers, and the complete dashboard.

## Integration Gate

A cycle is complete only when:

- both branches are committed, pushed, and individually tested;
- the backend OpenAPI snapshot matches the running API;
- frontend DTO and error mapping tests pass against that contract;
- backend migrations pass upgrade, downgrade, and upgrade locally;
- the affected synthetic end-to-end flow passes;
- no contributor edited the other workstream outside integration;
- no secrets, real financial documents, or raw PII are committed;
- the integration branch is merged and `main` is green.
