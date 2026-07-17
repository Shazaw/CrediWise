# CrediWise iOS

The native CrediWise frontend targets iOS 16+ and follows MVVM with lightweight
coordinators. `PLAN.md` sections 13 and 14 define the frontend architecture and
design system.

## Open the Project

On macOS with Xcode 15 or newer:

```bash
open ios/CrediWise.xcodeproj
```

The shared `CrediWise` scheme includes the application, unit-test target, and
UI-test target. Indonesian is the primary product localization and English is
the fallback localization.

## Command-Line Validation

```bash
xcodebuild \
  -project ios/CrediWise.xcodeproj \
  -scheme CrediWise \
  -destination 'platform=iOS Simulator,name=iPhone 15' \
  build test
```

```bash
swiftlint --config ios/.swiftlint.yml ios/CrediWise ios/CrediWiseTests ios/CrediWiseUITests
```

```bash
ios/scripts/lint-positioning-copy.sh
```

Select any locally installed iOS simulator if `iPhone 15` is unavailable.

Debug builds connect to `http://127.0.0.1:8000` by default. A scheme environment
variable named `CREDIWISE_API_BASE_URL` overrides the generated Info.plist value.
Debug accepts HTTP only for `localhost`, `127.0.0.1`, or `::1`; Release requires
an absolute HTTPS URL.

Release archives must set the user-defined `CREDIWISE_API_BASE_URL` build setting;
the project generates the same-named Info.plist key from it. Do not commit a
deployment URL. CI or an archive command can provide it explicitly:

```bash
xcodebuild \
  -project ios/CrediWise.xcodeproj \
  -scheme CrediWise \
  -configuration Release \
  CREDIWISE_API_BASE_URL=https://api.example.invalid \
  archive
```

## Current Foundation

- `AppCoordinator` owns typed root navigation.
- `WelcomeView` renders the unauthenticated entry screen and dispatches intent.
- `Core/DesignSystem` owns approved colors, typography, spacing, radii, and base buttons.
- `Resources/id.lproj` is primary; `Resources/en.lproj` is the fallback.
- Every app build rejects prohibited positioning claims in localization files.
- XCTest covers coordinator navigation and the Welcome UI flow.
- `Features/Upload` owns supported-file validation, upload state, processing polling,
  accessible progress, and deterministic mock fixtures for Cycle 3.
- Cycle 4 adds extraction review with immutable source/normalized values, separate
  proposed corrections, explicit ownership confirmation or concern reporting, and
  a Data Confidence card with seven supplied dimensions and attributable reasons.

Authentication uses the versioned `/api/v1/auth` backend contract and stores
session tokens in Keychain. The current bundle identifier is
`com.crediwise.app`; replace it with the registered identifier before code
signing or TestFlight distribution. An app icon must also be supplied before
archiving.

Normal builds use the authenticated `POST /api/v1/documents` and
`GET /api/v1/documents/{id}/status` contract in `docs/api/openapi-v1.json`.
Protected-PDF passwords exist only for the active retry call, and image uploads
require the user to declare screenshot or camera-photo lineage. UI tests launch
with deterministic synthetic upload data and never treat mocks as source truth.

Normal builds also use the authenticated transaction, review, confirmation, and
verification endpoints committed in the additive Cycle 4 OpenAPI contract. The
adapter submits structured raw/system/proposed correction lineage and renders
server-supplied Trust Layer scores without recalculation. `--ui-testing
--review-flow` continues to use deterministic fixtures for isolated UI coverage.

Cycle 5 adds the financing-need form and assessment dashboard for Risk, Safe
Borrowing, the Cash-Flow Digital Twin, and the Financial Health plan. Production
uses the authenticated financing-need and assessment contracts, creates an
assessment from the confirmed document, polls until analysis completes, and
renders only server-supplied financial outputs. Run the deterministic isolated
flow with `--ui-testing --cycle-5-flow`.

Cycle 6 adds the fourth Shock Resilience headline card, authenticated shock
simulation and offer repositories, interactive stress-test controls, real
ordered projection points with an accessible Swift Charts summary, and
server-ordered offer list/detail screens. Production uses the finalized
`GET /assessments/{id}/shocks`, `POST /assessments/{id}/simulate`, assessment
offer list/seed, and top-level offer safety contracts. The client preserves
backend scores, bands, ranks, schedules, fees, reasons, and model lineage without
client-side scoring or ranking. The isolated deterministic UI flow remains
available with `--ui-testing --cycle-6-flow`.
