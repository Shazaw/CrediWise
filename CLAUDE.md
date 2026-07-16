# CLAUDE.md — Krediwise Terminal Agent Operating Manual

> This file governs every terminal-agent session in the Krediwise repository.
> `PLAN.md` is the product and technical source of truth. This file defines how agents execute that plan safely, consistently, and without creating cross-agent conflicts.

- **Project:** Krediwise — Two-Way Credit Safety Engine
- **Primary specification:** `PLAN.md`
- **Applies to:** Claude Code and any equivalent terminal coding agent
- **Owner:** Krediwise founding engineering team
- **Default locale:** `id-ID`
- **Default timezone:** `Asia/Jakarta`

---

## 1. Read This Before Doing Anything

At the start of every session:

1. Read `PLAN.md`.
2. Read this `CLAUDE.md`.
3. Inspect `git status`, the current branch, recent commits, and relevant open work.
4. Determine the session workstream: **BACKEND** or **FRONTEND**.
5. State the selected workstream in the session notes before editing files.
6. Inspect only the files and contracts needed for the assigned task.
7. Do not begin implementation until the scope and measurable outcome are clear.

`PLAN.md` defines what Krediwise is, what the system must do, its approved architecture, schemas, scoring rules, security constraints, and roadmap. Never silently contradict it.

If implementation reveals that `PLAN.md` is incomplete or wrong, do not silently invent a replacement architecture. Follow the Confusion Protocol and update the relevant ADR or decision log after the decision is made.

---

## 2. Session Workstream Isolation — Non-Negotiable

Every session must operate in exactly one primary workstream unless the user explicitly authorizes cross-stack work.

### 2.1 Workstream selection

At the beginning of the session:

- If the user says the session is for backend work, the workstream is **BACKEND**.
- If the user says the session is for frontend or iOS work, the workstream is **FRONTEND**.
- If the task itself clearly belongs to one side, select that side.
- If the workstream is genuinely ambiguous and the choice would affect files on both sides, ask once before editing.

### 2.2 BACKEND session boundaries

A BACKEND session may edit:

- `backend/**`
- backend-specific tests and fixtures
- backend migrations
- backend Docker configuration
- backend CI jobs
- server-side API/OpenAPI definitions
- backend-owned documentation
- infrastructure required exclusively for backend execution

A BACKEND session must not edit:

- `ios/**`
- Swift source files
- SwiftUI views or view models
- Xcode project files
- iOS localization files
- frontend design-system files
- frontend snapshots or UI tests

### 2.3 FRONTEND session boundaries

A FRONTEND session may edit:

- `ios/**`
- Swift and SwiftUI code
- iOS tests, snapshots, fixtures, localization, and accessibility metadata
- frontend-owned API client code generated from an already-approved contract
- frontend-specific CI jobs
- frontend-owned documentation

A FRONTEND session must not edit:

- `backend/**`
- database models or migrations
- FastAPI routes or services
- Celery tasks
- backend scoring engines
- backend Dockerfiles or backend deployment configuration

### 2.4 Contract changes

A contract change is not permission to edit both sides.

If a BACKEND session needs an API contract change:

1. Update the backend contract or OpenAPI source.
2. Document the exact frontend impact in `docs/handoffs/`.
3. Commit and push the backend change.
4. Leave the iOS implementation to a FRONTEND session.

If a FRONTEND session discovers that the backend contract is insufficient:

1. Do not patch the backend.
2. Document the required contract change precisely.
3. Add a handover note or issue.
4. Continue only with work that does not depend on the missing change.

Cross-stack edits are allowed only when the user explicitly says the current session owns both sides or requests an end-to-end contract migration. Such work must be done in clearly separated commits.

### 2.5 Conflict prevention

- Do not reformat, rename, or “clean up” files outside the selected workstream.
- Do not modify shared root files unless the task requires it.
- Do not regenerate project-wide files that create unrelated diffs.
- Never overwrite another agent’s uncommitted work.
- Before editing a shared file, inspect `git status` and recent commits.
- Use a dedicated branch or worktree for parallel agent work.

---

## 3. How to Work

The marginal cost of completeness is low. Finish the requested work properly, with tests, documentation, and evidence.

Search before building. Understand before editing. Test before committing. Commit before handing over.

Do not present a plan as the final result when the requested implementation is feasible in the current session.

You may outsource typing to tools or sub-agents. You may not outsource understanding. Before marking work DONE, be able to explain:

- why the implementation is correct;
- which invariant it preserves;
- which requirement or acceptance criterion it satisfies;
- how it fails;
- how the failure is detected;
- how the test suite proves the intended behavior.

Passing tests without understanding the code is not completion.

---

## 4. Deterministic Work vs AI Work

Krediwise handles financial data. Deterministic logic must remain deterministic.

### 4.1 Deterministic space

Use ordinary code for:

- arithmetic and financial calculations;
- score aggregation;
- risk-band thresholds;
- safe-instalment calculations;
- shock scenarios;
- balance reconstruction;
- metadata validation;
- transaction normalization;
- data lineage;
- hashes and deduplication;
- date and timezone calculations;
- API validation;
- authorization;
- schema transformations;
- retention logic;
- model-version selection.

These must produce reproducible outputs for identical versioned inputs.

### 4.2 AI-assisted space

AI may assist with:

- document anomaly interpretation;
- visual manipulation indicators;
- ambiguous transaction categorization suggestions;
- merchant normalization suggestions;
- explanation phrasing;
- user-facing summaries;
- recommendation wording.

AI output must never silently become source truth.

### 4.3 Hard decision boundary

AI must not independently:

- create or modify a numerical credit-risk score;
- determine the final Data Confidence Score;
- approve or reject a user;
- declare a document fake;
- determine a safe loan amount;
- determine a Safe Offer Score;
- override deterministic rules;
- alter immutable raw evidence.

AI produces evidence, suggestions, labels, or prose. Deterministic, versioned engines produce financial outputs.

---

## 5. Local Kimi AI Requirement

Krediwise uses a local or self-hosted Kimi-compatible model for AI-assisted document fraud and anomaly analysis.

### 5.1 Privacy requirement

Financial documents, extracted transactions, account identifiers, and user PII must not be sent to public hosted LLM endpoints unless the user and project owner explicitly approve a specific integration.

The default fraud-analysis path is local inference.

### 5.2 Architecture requirement

All Kimi access must go through a dedicated backend adapter, for example:

```text
backend/app/integrations/local_ai/
├── client.py
├── schemas.py
├── prompts.py
├── redaction.py
├── health.py
└── README.md
```

No service may shell out to Kimi or call its runtime directly outside this adapter.

The adapter must expose typed inputs and outputs. A suggested response contract is:

```json
{
  "model_name": "kimi-local",
  "model_version": "...",
  "prompt_version": "...",
  "analysis_status": "COMPLETE",
  "anomaly_probability": 0.42,
  "indicators": [
    {
      "code": "FONT_STYLE_INCONSISTENCY",
      "severity": "MEDIUM",
      "page": 2,
      "evidence": "..."
    }
  ],
  "limitations": ["..."],
  "latency_ms": 1200
}
```

### 5.3 Model-output controls

- Validate every response against a strict schema.
- Reject malformed or incomplete output.
- Store model name, model version, prompt version, and inference configuration.
- Use bounded enums for indicator codes and severity.
- Store evidence references, not unsupported accusations.
- Do not store unnecessary prompt copies containing raw PII.
- Apply deterministic redaction where raw identifiers are not needed.
- Set hard timeouts and memory limits.
- Provide a deterministic fallback when local AI is unavailable.
- Mark AI evidence as unavailable rather than blocking the entire assessment.

### 5.4 Scoring boundary

Local Kimi output may contribute only through an explicitly versioned configuration in the Trust Layer. It must never be the sole basis for a fraud or authenticity result.

The default MVP behavior is:

1. deterministic PDF structural forensics run first;
2. local Kimi analyzes selected visual or structural evidence;
3. Kimi returns bounded anomaly indicators;
4. the Trust Layer combines evidence according to a versioned deterministic rule;
5. the user sees non-accusatory wording such as “possible visual inconsistency detected.”

### 5.5 AI tests and evals

Every prompt or local-model behavior change requires:

- schema-validation tests;
- timeout and unavailable-model tests;
- prompt-injection resistance fixtures;
- PII-redaction tests;
- known-clean and known-anomalous document eval fixtures;
- false-positive review;
- versioned eval results.

Never make the general test suite depend on a local model being available. Gate tests use deterministic fixtures or a fake adapter. Local-model evals run in a separate marked lane.

---

## 6. Krediwise Architecture Rules

Follow the repository structure and dependency directions defined in `PLAN.md`.

### 6.1 Backend layering

```text
API controllers
    ↓
Application services / use cases
    ↓
Repositories and integrations
    ↓
Database / external adapters

Application services
    ↓
Pure deterministic engines
```

Rules:

- API controllers contain no scoring logic and no direct SQL.
- Services orchestrate work and transaction boundaries.
- Repositories own persistence queries.
- Engines are pure functions with no database, network, clock, or random access unless injected.
- Integrations isolate side effects such as object storage and local Kimi inference.
- Celery tasks call services; they do not duplicate business rules.
- Every stored score references a model version.
- Every assessment references immutable input lineage.

### 6.2 iOS architecture

Follow the architecture selected in `PLAN.md`.

Rules:

- SwiftUI views render state and dispatch user intent.
- View models coordinate presentation logic and call typed services.
- API clients own networking and DTO decoding.
- Domain models must not depend on SwiftUI.
- User-facing strings live in localization catalogs.
- Financial formatting uses the approved IDR formatter.
- Accessibility labels, Dynamic Type, contrast, and VoiceOver are part of completion.
- The iOS client does not reproduce backend scoring logic.

### 6.3 Shared contracts

The backend OpenAPI definition is the authoritative HTTP contract unless `PLAN.md` says otherwise.

- Do not hand-maintain contradictory DTO definitions.
- Contract changes require versioning or additive compatibility.
- Generated code must be reproducible.
- Do not commit generated output unless the repository policy requires it.
- Breaking changes require an ADR and migration plan.

### 6.4 Data lineage

Never overwrite evidence needed to reproduce an assessment.

Keep separate:

- raw uploaded document;
- raw extracted values;
- normalized values;
- user-proposed corrections;
- approved correction state;
- processing run;
- parser and prompt versions;
- assessment input snapshot;
- engine configuration hash;
- score output and reason codes.

Historical assessments must not silently change when parsers, category rules, prompts, or models change.

---

## 7. Tests and Evals

No feature is complete without tests appropriate to its behavior.

### 7.1 Deterministic gate tests

Gate tests must be:

- local;
- reproducible;
- isolated;
- non-flaky;
- fast enough for regular execution;
- free of public network dependencies.

Examples:

- unit tests for engines;
- schema tests;
- repository tests;
- API authorization tests;
- migration tests;
- Swift unit tests;
- view-model tests;
- snapshot or UI tests where valuable;
- known PDF extraction fixtures;
- balance reconstruction fixtures;
- safe-loan and shock-simulation golden cases.

### 7.2 AI eval lane

AI-assisted functionality requires an eval suite in addition to ordinary tests.

The eval lane may be slower and machine-dependent. It must define:

- fixture set;
- expected indicator classes;
- acceptable false-positive and false-negative thresholds;
- model version;
- prompt version;
- runtime configuration;
- pass criteria.

### 7.3 Bug fixes

Every bug fix includes a regression test that fails before the fix and passes after it.

### 7.4 Financial-engine requirements

For every scoring-engine change:

- state the affected model version;
- add boundary-value tests;
- add rounding tests;
- add insufficient-data tests;
- add negative and zero cash-flow tests;
- verify identical inputs produce identical outputs;
- update golden fixtures where behavior intentionally changes;
- do not edit historical model configuration in place.

---

## 8. Measurable Outcomes

Before implementation, identify the concrete outcome.

Examples:

- “BCA fixture extraction field accuracy rises from 91% to at least 95%.”
- “Duplicate uploads reuse the existing document and create no second object-storage write.”
- “A revoked consent returns `403 CONSENT_REVOKED` immediately.”
- “The shock engine detects a temporary deficit when an income event moves past the repayment due date.”
- “VoiceOver announces each dashboard metric, value, status, and explanation action.”

Every meaningful change must leave evidence through one or more of:

- test result;
- eval result;
- structured log;
- metric;
- audit event;
- fixture comparison;
- screenshot or UI-test artifact.

---

## 9. Search Before Building

Use this order:

1. Existing project implementation or utility.
2. Standard library or established pattern.
3. Approved dependency already in the stack.
4. Well-maintained external library.
5. Custom implementation only when the above do not fit.

Do not add dependencies casually. Evaluate:

- maintenance activity;
- license;
- security history;
- compatibility with the approved platform;
- transitive dependency cost;
- deterministic behavior;
- ability to test locally.

Any architecture-changing dependency requires an ADR.

---

## 10. Git and Parallel-Agent Workflow

### 10.1 Before editing

Run:

```bash
git status --short --branch
git log --oneline -5
```

Confirm:

- current branch;
- worktree ownership;
- whether uncommitted changes already exist;
- whether those changes belong to another agent.

Do not discard or overwrite work you did not create.

### 10.2 Branches and worktrees

Use a focused branch or worktree per task or agent, for example:

```text
backend/auth-refresh-rotation
backend/trust-layer-parser-versioning
frontend/dashboard-accessibility
frontend/upload-review-flow
```

Avoid multiple agents editing the same branch.

### 10.3 Commit discipline

Commits must be:

- focused;
- buildable;
- tested;
- free of secrets;
- descriptive;
- limited to the selected workstream unless cross-stack work was authorized.

Recommended commit messages:

```text
feat(backend): add versioned document processing runs
fix(backend): preserve assessment transaction lineage
feat(ios): add transaction review and correction flow
test(backend): add delayed-income liquidity scenarios
docs: add local Kimi anomaly-analysis contract
```

### 10.4 Commit and push after every completed task

When the task is complete:

1. Review the diff.
2. Run the required tests and evals.
3. Verify no secret or generated junk is staged.
4. Stage only files belonging to the task.
5. Commit with a clear message.
6. Push the branch to GitHub.
7. Report the branch and commit hash.

Do not use `--no-verify`.

If push is impossible because credentials, remote access, or network access is unavailable:

- still create the local commit;
- report the exact commit hash;
- report the exact push command required;
- mark the final status `DONE_WITH_CONCERNS` rather than claiming it was pushed.

### 10.5 Current-progress commits

Do not leave substantial valid progress only in the working tree.

When a logical checkpoint is reached, create a checkpoint commit if:

- the implementation is coherent;
- affected tests pass;
- the commit does not knowingly break the branch;
- the message clearly describes the checkpoint.

Do not create misleading “WIP” commits containing broken or untested code solely to clear the working tree. If incomplete work must be handed over, use the Context-Limit Handover Protocol below.

---

## 11. Context-Limit Handover Protocol — Non-Negotiable

A terminal agent must not run out of context and leave undocumented work.

### 11.1 Trigger

Start handover preparation as soon as the agent detects that the context window, session budget, or tool budget is becoming constrained enough that completing and validating the task may be unsafe.

Do not wait until the final message is forced or truncated.

### 11.2 Stabilize the repository

Before handover:

1. Stop starting new sub-tasks.
2. Finish the smallest coherent unit currently in progress.
3. Run the tests relevant to that unit.
4. Review `git diff` and `git status`.
5. Remove accidental or unrelated changes.
6. Commit all coherent, tested progress.
7. Push the commit to GitHub.

If a coherent commit is impossible without including broken code:

- do not create a deceptive completion commit;
- preserve the diff safely in the current branch/worktree;
- create a patch file if useful;
- document every uncommitted file and why it remains uncommitted.

### 11.3 Write the handover

Create or update:

```text
docs/handoffs/<YYYY-MM-DD>-<workstream>-<task-slug>.md
```

The handover must contain:

```markdown
# Handover: <task>

## Session scope
- Workstream: BACKEND or FRONTEND
- Branch:
- Base commit:
- Latest commit:
- PLAN.md sections / requirement IDs:

## User request
<Exact concise request>

## Completed
- File-level list of completed changes
- Important implementation decisions
- Tests/evals added

## Current state
- What works
- What is partially complete
- What is not started

## Validation evidence
- Commands run
- Tests passed/failed
- Eval results
- Known warnings

## Files changed
- `path`: what changed and why

## Remaining work
1. Exact next step
2. Exact next step

## Risks and failure modes
- Known bug or uncertainty
- Security/privacy concern
- Migration or compatibility concern

## Commands for the next agent
```bash
<checkout, setup, test, and run commands>
```

## Do not touch
- Files or workstreams owned by another active agent

## Uncommitted state
- Clean, or exact list of uncommitted files and reason
```

### 11.4 Final context-limit response

Before ending the session, report:

- completion status;
- branch;
- latest commit hash;
- whether it was pushed;
- handover file path;
- tests/evals run;
- exact first action for the next terminal agent.

The purpose is that another terminal agent can continue without rereading the entire conversation or reverse-engineering the working tree.

---

## 12. Completion Status Protocol

Every task ends with exactly one status:

- **DONE** — Requested scope is complete, validated, committed, and pushed.
- **DONE_WITH_CONCERNS** — Requested scope is complete enough to use, but a named concern remains, or GitHub push was not possible.
- **BLOCKED** — Work cannot safely continue. State the blocker and evidence.
- **NEEDS_CONTEXT** — A material decision or input is missing.
- **HANDOVER_READY** — Session limit is near; coherent progress is committed and pushed, and the handover document is complete.

Do not call a task DONE when:

- tests are missing;
- required evals are missing;
- the implementation conflicts with `PLAN.md`;
- code is uncommitted;
- push was required and not attempted;
- the other workstream was modified without authorization;
- security or privacy controls are knowingly incomplete.

---

## 13. Reporting at the End of a Task

Report:

1. Status.
2. Files changed.
3. User-visible or measurable outcome.
4. Tests and evals run, including results.
5. Branch and commit hash.
6. Push result.
7. Required restart or migration commands.
8. Exact next action.

If nothing needs restarting, say so explicitly.

Never expose internal IDs, secrets, tokens, or raw financial data in the report.

---

## 14. Background Jobs, Migrations, and Backfills

### 14.1 Monitoring

Do not fire and forget long-running work.

Track progress from real state, not estimates invented by the model. Use a script to calculate percent, rate, and ETA where possible.

Write progress to:

```text
/tmp/krediwise-<job-name>/progress.log
```

Print the command:

```bash
tail -f /tmp/krediwise-<job-name>/progress.log
```

### 14.2 Data safety

For modifying backfills:

- snapshot affected rows before modification;
- stop for approval if the snapshot exceeds 100,000 rows or 100 MB;
- include a rollback strategy;
- do not run against production without explicit confirmation;
- preserve assessment and audit lineage.

### 14.3 Completion report

Produce:

- verdict;
- rows examined and changed;
- errors;
- before/after examples;
- full CSV or structured diff path under `/tmp/`;
- validation queries;
- rollback status.

---

## 15. Security and Privacy

Krediwise processes highly sensitive financial information.

### 15.1 Absolute rules

- Never commit secrets.
- Never commit real user financial documents.
- Never log bank passwords, PDF passwords, tokens, raw account numbers, full identity numbers, or unredacted transaction payloads.
- Never send financial documents to public AI endpoints by default.
- Never store PDF passwords in Redis, Celery payloads, database rows, analytics, or crash reports.
- Never bypass authorization for demo convenience.
- Never weaken consent checks silently.
- Never remove audit events to make tests easier.
- Never label a user dishonest solely because data confidence is low.
- Never call Krediwise output an official credit score.

### 15.2 Destructive commands

Do not run the following without explicit confirmation:

- `rm -rf`
- `git reset --hard`
- `git push --force`
- destructive SQL such as `DROP TABLE` or unscoped `DELETE`
- production migrations
- production object deletion
- key rotation
- disabling security checks

### 15.3 Production operations

Before touching production:

1. state exactly what will change;
2. state the rollback path;
3. wait for confirmation;
4. execute the smallest safe operation;
5. verify outcome;
6. record the action in the audit or deployment log.

---

## 16. Krediwise Product Guardrails

Every implementation must preserve these rules:

- Krediwise produces an **estimated financial-risk, affordability, and credit-readiness assessment**, not an official credit score.
- Data Confidence is separate from user behavior.
- Low Data Confidence means the evidence is incomplete or difficult to verify, not that the user is dishonest.
- The lender remains responsible for the final credit decision.
- Offers are ranked by user safety and suitability, never commission.
- Simulated hackathon offers must be visibly labelled simulated.
- Raw evidence and historical assessments are immutable.
- The same input snapshot and model version must produce the same deterministic scores.
- Business activity must not be misrepresented as personal discretionary spending.
- Financial recommendations must be selected by deterministic reason-code rules; AI may phrase them but may not invent unsupported advice.

Add tests for guardrail language wherever user-facing copy or lender-facing payloads change.

---

## 17. Confusion Protocol

Stop and ask for a decision when:

- two plausible architectures materially affect future work;
- the request conflicts with `PLAN.md`;
- a destructive operation has unclear scope;
- a change would require touching both frontend and backend despite workstream isolation;
- a financial formula or regulatory claim is ambiguous;
- a data migration could alter historical assessment meaning;
- public AI processing of user data is being proposed;
- another agent owns or has uncommitted changes in the required files.

State:

1. the ambiguity in one sentence;
2. two or three real options;
3. trade-offs;
4. your recommended option.

Do not invoke the protocol for routine implementation details already settled by `PLAN.md`.

---

## 18. Communication Style

Communicate with Ahsan directly and concretely.

- Use exact file paths, symbols, commands, and test names.
- Keep progress updates short.
- Say plainly when something is broken.
- Do not use vague claims such as “everything looks good.”
- Do not claim a commit was pushed unless the push succeeded.
- Do not claim tests passed unless they were run.
- End with the exact next action.

Avoid generic filler and unnecessary preambles.

---

## 19. Task Start Checklist

```text
[ ] Read PLAN.md
[ ] Read CLAUDE.md
[ ] Inspect git status and recent commits
[ ] Select BACKEND or FRONTEND workstream
[ ] Confirm task does not require unauthorized cross-stack edits
[ ] Identify requirement IDs / acceptance criteria
[ ] Identify measurable outcome
[ ] Identify affected files and tests
[ ] Check for existing utilities and patterns
[ ] Confirm no other agent owns the same files
```

---

## 20. Task Completion Checklist

```text
[ ] Requested behavior is implemented
[ ] No unauthorized files from the other workstream changed
[ ] PLAN.md constraints remain satisfied
[ ] Deterministic logic is not delegated to AI
[ ] Local Kimi boundary and privacy rules are preserved
[ ] Tests added or updated
[ ] Required AI evals added or updated
[ ] Relevant tests pass
[ ] Security and privacy review completed
[ ] User-facing copy uses approved positioning
[ ] Migrations and generated artifacts reviewed
[ ] Documentation updated
[ ] Git diff reviewed
[ ] No secrets or real financial data staged
[ ] Progress committed
[ ] Branch pushed to GitHub
[ ] Restart/migration commands reported
[ ] Handover prepared if context is nearing its limit
```

---

## 21. Final Rule

When Ahsan asks for implementation, deliver working, tested, documented, committed, and pushed code within the authorized workstream.

Do not leave the next terminal agent an unexplained working tree.
