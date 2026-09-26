# AI-SENTRY -- Current Phase

**Last Updated:** 2026-09-26
**Current Phase:** Screen 2 -- Input Page (COMPLETE)
**Previous Phase:** Screen 1 -- Agreement Page (COMPLETE)
**Next Phase:** Screen 3 -- Configuration Page

---

## Phase Status

| Phase | Name | Status |
|---|---|---|
| 0a-0e | Design & Documentation Foundation | COMPLETE |
| 1a-1d | Input Layer (consent, validation, probe) | COMPLETE |
| 2a-2d | Manifest System | COMPLETE |
| 3a-3c | Orchestration Layer (estimation, guard, engine) | COMPLETE |
| 5a | Scoring Engine | COMPLETE |
| 5b | Recommendation Engine | COMPLETE |
| 6a | Report Generation + Integration | COMPLETE |
| 6b | UI Architecture Document | COMPLETE |
| S1 | Agreement Screen (Screen 1) | COMPLETE |
| S2 | Input Screen (Screen 2) | COMPLETE |
| S3 | Configuration Screen (Screen 3) | NOT STARTED -- READY |
| S4+ | Remaining Screens (4-11) | NOT STARTED |

---

## Screen 1 -- Agreement Page

### Files Created

| File | Purpose |
|---|---|
| `frontend/src/store/actions.ts` | Action type constants for all 3 contexts |
| `frontend/src/store/ScanContext.tsx` | Scan lifecycle state, consent persistence |
| `frontend/src/hooks/useScan.ts` | ScanContext consumer hook |
| `frontend/src/hooks/useNavigation.ts` | Step-based wizard navigation |
| `frontend/src/components/layout/PageHeader.tsx` | Consistent page header |
| `frontend/src/pages/AgreementPage.tsx` | Screen 1: consent gate |
| `frontend/src/App.tsx` | Root component + screen router |
| `frontend/src/main.tsx` | React 18 entry point |

### Architecture Decisions

- **No external UI library**: All components are vanilla React + TypeScript
- **BEM class naming**: `agreement-page__section-title`, `button--primary`
- **No styling code**: Only structural class names; styling deferred to design phase
- **Consent in localStorage**: Key `aisentry_consent_given`, corruption-safe reads
- **onAccept callback**: Page does not own navigation; parent router decides where to go
- **In-memory router**: No URL-based routing; ScreenRouter uses switch/case on ScreenId

### Navigation Logic

```
App Launch
  |
  v
ScanContext initializes:
  - reads localStorage("aisentry_consent_given")
  - if "true" → phase = "consented", skip to Input (Step 2)
  - if missing/false → phase = "idle", show Agreement (Step 1)

User checks checkbox → local state (agreed = true)
User clicks "Agree & Continue":
  - dispatch(ACCEPT_CONSENT) → consent_given = true, phase = "consented"
  - reducer writes to localStorage
  - onAccept() → navigateTo("input")

On reload:
  - localStorage read → consent_given = true → auto-skip to Input
```

### Bypass Protection

1. useNavigation refuses to navigate anywhere except "agree" when consent_given is false
2. Button is disabled until checkbox is checked
3. Corrupted localStorage (non-"true" values) default to false

---

## Full CLI Pipeline (unchanged -- 13 steps)

```
Step 1:  Consent gate          core/consent.py
Step 2:  Manifest load+merge   core/manifest.py
Step 3:  Manifest validation   core/manifest_validator.py
Step 4:  Estimate              core/estimator.py
Step 5:  Safety guard          core/scan_guard.py
Step 6:  Display + confirm     core/manifest_display.py
Step 7:  Connection validate   core/validator.py
Step 8:  Endpoint probe        core/input_handler.py or core/local_handler.py
Step 9:  Scan engine           core/engine_runner.py
Step 10: Risk scoring          core/scorer.py
Step 11: Recommendations       core/recommender.py
Step 12: Report generation     core/report_generator.py + services/report_service.py
Step 13: File export           core/report_generator.py :: export_report()
```

## Current Test Count: 799 (backend only -- frontend tests pending)

---

## Frontend File Structure (current)

```
app/frontend/
+-- src/
|   +-- main.tsx                       # React 18 entry
|   +-- App.tsx                        # Root + ScreenRouter
|   +-- pages/
|   |   +-- AgreementPage.tsx          # Screen 1 (DONE)
|   +-- store/
|   |   +-- actions.ts                 # Action type constants
|   |   +-- ScanContext.tsx            # Scan state + reducer
|   +-- hooks/
|   |   +-- useScan.ts                 # ScanContext consumer
|   |   +-- useNavigation.ts           # Wizard navigation
|   +-- components/
|       +-- layout/
|           +-- PageHeader.tsx         # Page header component
```

---

## Context Notes for AI Tools

- Frontend uses TypeScript + React (no external state libs, no UI frameworks)
- Class names follow BEM convention for future styling
- AgreementPage has unique IDs: `consent-checkbox`, `agree-continue-button` (for testing)
- ScanContext initializer reads localStorage once at mount
- Navigation is in-memory (useState), not URL-based
- Placeholder pages exist for Steps 2-11 in App.tsx
- Do NOT commit or push to GitHub -- user handles commits manually
