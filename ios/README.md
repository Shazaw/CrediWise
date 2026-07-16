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

Debug builds connect to `http://127.0.0.1:8000` by default. Set the
`CREDIWISE_API_BASE_URL` scheme environment variable to an HTTPS API URL or to
the development machine's LAN address when testing on a physical device.

## Current Foundation

- `AppCoordinator` owns typed root navigation.
- `WelcomeView` renders the unauthenticated entry screen and dispatches intent.
- `Core/DesignSystem` owns approved colors, typography, spacing, radii, and base buttons.
- `Resources/id.lproj` is primary; `Resources/en.lproj` is the fallback.
- Every app build rejects prohibited positioning claims in localization files.
- XCTest covers coordinator navigation and the Welcome UI flow.
- `Features/Upload` owns supported-file validation, upload state, processing polling,
  accessible progress, and deterministic mock fixtures for Cycle 3.

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
