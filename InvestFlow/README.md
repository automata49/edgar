# Invest Flow

Invest Flow is a minimal iPhone SwiftUI app focused on three workflows:

- Money: monthly cash-flow tracking, investable amount calculation, and recurring allocation planning.
- Routine: morning, intraday, and evening investing checklists with contrarian prompts and daily review notes.
- Post-it: stock and crypto idea capture with text or mock voice notes, AI summaries, allocation proposals, and explicit user approval before proposals enter the investment plan.

## Architecture

- SwiftUI views live in `InvestFlow/Views`.
- MVVM view models live in `InvestFlow/ViewModels`.
- SwiftData models live in `InvestFlow/Models`.
- Protocol-based services and mock implementations live in `InvestFlow/Services`.

The app currently uses mock market, AI, and voice-note services so external APIs can be connected later without changing the UI.

## Run

Open `InvestFlow.xcodeproj` in Xcode 15 or later, select an iPhone simulator, and run the `InvestFlow` scheme.

## iOS Chrome Web Version

The companion mobile web/PWA version lives in `../InvestFlowWeb`.

From the repository root:

```bash
python3 -m http.server 8080 --directory InvestFlowWeb
```

Open `http://localhost:8080` on a device or simulator browser. For a physical iPhone, serve it from a host address reachable on the same network.
