# Handover: Cycle 3 Secure Upload Contract

## Session scope
- Workstream: FRONTEND
- Branch: `frontend/cycle-3-upload-status`
- Base commit: `6006b3cd928419ac43305d9d9b251690707ae9b1`
- PLAN.md sections: FR-3, §7.2, §8.2, §12, §13.4-13.7, Sprint 2, T2.6

## Frontend implementation boundary

The iOS client implements a document picker for PDF, CSV, PNG, and JPEG, a
15 MB client-side size check, typed upload/status states, exponential polling,
per-file progress, an accessible processing checklist, constructive failures,
duplicate-reuse messaging, and deterministic synthetic mocks. Normal builds
use `UnavailableDocumentUploadRepository` so a selected financial file is not
sent through an unapproved or guessed endpoint.

No raw document bytes are cached to disk by the feature. A security-scoped URL
is retained only for the active selection and is accessed during validation and
upload. The backend remains authoritative for magic-byte validation, hashing,
deduplication, script scanning, quarantine, and immutable evidence storage.

## Contract required from backend

The backend handoff must publish the OpenAPI snapshot and identify:

1. The exact multipart field names, accepted request headers, idempotency-key
   behavior, and `202` response for `POST /api/v1/documents`.
2. The exact response for `GET /api/v1/documents/{id}/status`, including the
   document ID, bounded status enum, optional progress, polling URL, and any
   `Retry-After` guidance.
3. Stable error codes and HTTP statuses for unsupported MIME/magic bytes,
   zero-byte and oversized files, corrupt files, suspicious PDF actions,
   unsupported layouts, ownership failures, rate limits, and missing records.
4. How duplicate reuse is represented. It must return the existing document
   and a notice, and must not use a security-rejection error.
5. The complete transient password-protected PDF handshake: detection response,
   retry endpoint/request field, TLS requirement, and proof that the password is
   never persisted, logged, or placed in Redis/Celery payloads.
6. Whether upload progress is observable through direct multipart transfer,
   presigned storage, status polling, or a combination of those mechanisms.
7. Ownership and authorization behavior for status reads, including the stable
   response for another user's document ID.

## Integration action

Implement `APIDocumentUploadRepository` only after the snapshot is committed.
Map the approved DTOs into `DocumentUploadReceipt` and
`DocumentStatusSnapshot`, preserve authenticated ownership checks, and add
contract-decoding tests. Add the transient PDF-password UI only after item 5 is
defined; never store the password in `SelectedUploadFile` or persistent state.
