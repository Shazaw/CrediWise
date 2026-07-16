# Krediwise

Krediwise is a two-way credit safety engine for underserved, thin-file,
informal-income, freelance, gig-worker, and microbusiness users in Indonesia.
It turns verified financial records into an explainable view of financial
behaviour, repayment capacity, shock resilience, and safe borrowing capacity.

> We do not only determine whether a user is creditworthy. We determine
> whether the credit is worthy of the user.

## Project Status

Krediwise is currently in **Sprint 0: repository and environment foundation**.
The architecture and product requirements are approved, but application
development has not started. The directories in this repository establish
module ownership and dependency boundaries for upcoming work.

The complete product and technical specification is [`PLAN.md`](PLAN.md).
Terminal coding agents must also follow [`CLAUDE.md`](CLAUDE.md).

## What Krediwise Produces

- **Data Confidence:** how reliably the submitted financial data can be verified.
- **Cash-Flow Digital Twin:** an explainable financial profile that separates
  personal and business activity.
- **Indicative Credit Risk:** deterministic repayment-risk and model-confidence
  bands with reason codes.
- **Shock Resilience:** the effect of income drops, delays, emergencies, and
  weakest-month conditions.
- **Safe Borrowing Capacity:** a sustainable instalment, illustrative amount,
  tenor, repayment timing, and liquidity buffer.
- **Safe Offer Score:** a safety-first comparison of simulated loan offers,
  ranked by user suitability rather than commission.

Krediwise provides an estimated financial-risk, affordability, and
credit-readiness assessment based on the data provided, not an official credit
score. Lenders remain responsible for final credit decisions.

## Architecture

Krediwise is a monorepo with two primary workstreams:

- `backend/`: Python 3.12, FastAPI, SQLAlchemy, Alembic, Celery, PostgreSQL,
  Redis, and S3-compatible object storage.
- `ios/`: native SwiftUI for iOS 16+, using MVVM, a lightweight coordinator,
  Swift Concurrency, and Swift Charts.

The backend follows this dependency direction:

```text
API controllers
    -> application services
    -> repositories and integrations
    -> database and external adapters

Application services
    -> pure deterministic engines
```

Document anomaly assistance uses a local or self-hosted Kimi-compatible model
behind a dedicated adapter. AI can provide bounded evidence or phrase existing
reason codes, but it cannot calculate scores, approve users, or replace the
deterministic engines.

## Repository Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/v1/             # Versioned HTTP controllers
│   │   ├── core/               # Configuration, security, logging, dependencies
│   │   ├── db/seeds/           # Database bootstrap and idempotent seed data
│   │   ├── engines/config/     # Pure engines and versioned model configuration
│   │   ├── integrations/       # Storage, local AI, and mock provider adapters
│   │   ├── models/             # SQLAlchemy entities
│   │   ├── pipeline/           # Celery tasks and stage orchestration
│   │   ├── repositories/       # Persistence queries
│   │   ├── schemas/            # Pydantic request and response DTOs
│   │   └── services/           # Application use cases
│   ├── alembic/versions/       # Database migrations
│   └── tests/                  # Unit, integration, and end-to-end tests
├── docs/
│   ├── adr/                    # Architecture Decision Records
│   ├── api/                    # OpenAPI snapshots
│   ├── fixtures/               # Synthetic financial fixtures and expected output
│   └── handoffs/               # Workstream handover notes
├── infra/
│   └── github-actions/         # CI workflow sources
├── ios/Krediwise/
│   ├── App/                    # App entry point, coordinator, dependency container
│   ├── Core/                   # Networking, auth, persistence, design system, utilities
│   ├── Features/               # Feature-scoped views and view models
│   ├── Models/                 # Codable API DTOs and domain models
│   └── Resources/              # Localizations and asset catalogs
├── CLAUDE.md                   # Terminal-agent operating manual
├── PLAN.md                     # Product and technical source of truth
└── README.md
```

Empty directories contain `.gitkeep` markers so Git preserves the approved
layout. These markers are removed as implementation files are added.

## Core Engineering Rules

- Financial calculations and score aggregation are deterministic and versioned.
- Engines are pure and perform no database, network, filesystem, clock, or
  random access.
- Raw documents, extracted values, corrections, snapshots, and historical
  assessment lineage remain separate and reproducible.
- Financial documents and PII are not sent to public hosted AI endpoints by
  default.
- Offers are simulated during the MVP and ranked by user safety, never commission.
- All development uses synthetic fixtures; real financial records must never be
  committed.
- Backend and iOS work remain isolated unless a task explicitly authorizes
  cross-stack changes.

## Planned Development Order

1. Repository, local environment, application shells, and CI.
2. Authentication, user profiles, authorization, and audit foundations.
3. Secure document upload, object storage, and asynchronous processing.
4. Extraction, structural forensics, Trust Layer, and Data Confidence.
5. Cash-Flow Digital Twin, risk, and safe-borrowing engines.
6. Shock simulations, simulated offers, Safe Offer Score, and full dashboard.

See [`PLAN.md`](PLAN.md) for acceptance criteria, schemas, scoring rules,
security requirements, testing gates, and the complete roadmap.
