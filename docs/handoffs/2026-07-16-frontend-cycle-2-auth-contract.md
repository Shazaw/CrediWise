# Handover: Cycle 2 Authentication Contract

## Session scope
- Workstream: FRONTEND
- Branch: `frontend/cycle-2-auth-session`
- Base commit: `a1930f5fdbddd0c1c488df699ad5b2960d2b631a`
- PLAN.md sections: FR-1, FR-2, §12, §13, §18.1-18.2, Sprint 1, T1.8

## Frontend implementation boundary

The iOS client implements authentication UI, client-side validation, Keychain-backed
session storage, session-driven routing, and generic bearer-token refresh/retry behavior.
It uses an `AuthenticationRepository` protocol and deterministic mock because no approved
`docs/api/openapi-v1.json` snapshot exists for Cycle 2.

## Contract required from backend

The backend handoff must publish the OpenAPI snapshot and identify:

1. Exact request and success-response schemas for `POST /api/v1/auth/register`,
   `/login`, `/refresh`, and `/logout`.
2. Access-token and rotating-refresh-token field names, token type, and whether registration
   starts a session or requires a subsequent login.
3. Stable error codes for duplicate email, weak password, invalid credentials, expired or
   reused refresh token, lockout, and rate limiting.
4. Exact `GET /api/v1/me` and `PATCH /api/v1/me/profile` schemas.
5. The complete bounded values for `employment_enum`; `PLAN.md` names the enum but does not
   define its cases.
6. Whether `business_type` is free text or bounded, and which profile fields are required.

## Integration action

Implement a concrete API authentication repository only after the snapshot is committed.
DTOs must decode that snapshot rather than mirroring assumptions from the mock repository.
