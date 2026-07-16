# CI Workflow Source

GitHub Actions only executes workflow files under `.github/workflows/` at the
repository root — that is a GitHub platform requirement, not a project
choice, so the actual workflow definitions live there instead of in this
directory:

- [`../../.github/workflows/backend-ci.yml`](../../.github/workflows/backend-ci.yml)
  — lint, test + coverage gate, migration up/down/up check, dependency
  audit, secret scan, and Docker image build (PLAN §20.2).

This directory is kept as the documented location (PLAN §8.4 repo layout)
for CI-related notes and any future composite/reusable actions that are not
themselves entry-point workflows.
