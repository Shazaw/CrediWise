# Local Kimi anomaly-assistance adapter

Implements CrediWise's local/self-hosted document-fraud-assistance boundary
(CLAUDE.md §5, PLAN §15.6/§16.3). This is the **only** module allowed to
call the local Kimi-compatible runtime — no service or engine may reach it
directly (CLAUDE.md §5.2).

## Files

- `client.py` — `DocumentAnomalyPort` protocol + `LocalKimiClient`, an
  OpenAI-compatible chat-completions caller with a bounded timeout, one
  retry, and strict response-schema validation.
- `schemas.py` — the typed request/response contract. Every response field
  is bounded (enums for indicator code/severity, length/range caps) so a
  malformed or adversarial model reply is rejected by Pydantic, never
  silently trusted.
- `prompts.py` — the strict system prompt ("explain evidence, never decide")
  and `PROMPT_VERSION`, stamped on every stored result for reproducibility
  (PLAN §15.4/§19.2).
- `redaction.py` — deterministic redaction for any free-text forensic
  feature values before they leave this process (defense-in-depth; the
  primary input, rendered page-region images plus a bounded feature dict,
  never includes raw transaction text or account numbers by construction).
- `health.py` — reachability probe (`/v1/models`) used before attempting a
  real call, and by any future ops/readiness surface.
- `__init__.py` — process-wide `get_document_anomaly_port()` /
  `set_document_anomaly_port()` singleton, mirroring
  `app.integrations.storage`'s override seam so tests inject a fake adapter
  instead of requiring a real local runtime (CLAUDE.md §5.5).

## Forbidden outputs (enforced by `schemas.py` + `prompts.py`)

Kimi may never: declare a document fraudulent or genuine, output a Data
Confidence Score or any other final score, change a Risk Band, receive
banking/PDF passwords, or produce free-form/untraceable text. It may only
return bounded anomaly indicators, a bounded severity, an affected page, and
a short evidence string — see PLAN §15.6.

## Scoring boundary

`TrustLayerEngine` (`app/engines/trust_layer.py`) treats a Kimi result as
optional evidence. It only affects `visual_score` when
`trust_layer.kimi_anomaly_scoring_enabled` is `true` in the active
`model_config.py` version (PLAN §15.6) — disabled by default in MVP. When
the port is unavailable, misconfigured, or fails after retry, the engine
receives no Kimi result and proceeds deterministically with an
`AI_SIGNAL_UNAVAILABLE` flag — the assessment is never blocked on Kimi.

## Configuration

`KIMI_BASE_URL` (unset by default — the port is `None`/unavailable until
configured), `KIMI_MODEL`, `KIMI_TIMEOUT_SECONDS` (see `.env.example`).
Never a public-cloud endpoint (CLAUDE.md §15.1) — this must be a private,
self-hosted, OpenAI-compatible URL under CrediWise's own infrastructure.

## Rendering page-region images

Sprint 3 does not yet implement statement-page-to-image rendering (would
require an additional rendering dependency and pipeline stage). Until that
lands, `DocumentAnomalyRequest.page_images_base64` is only ever populated by
a caller that has already rendered pages some other way; the verification
service does not call this adapter in Sprint 3's default configuration
(`kimi_anomaly_scoring_enabled=False`). This is a tracked follow-up, not a
silent gap — see the Sprint 3 handoff doc.
