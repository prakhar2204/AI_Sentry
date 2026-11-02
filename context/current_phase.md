# Sentryɸ — Current Phase Status

**Last Updated:** 2026-11-02
**Current Phase:** P8 — Installer + Distribution (COMPLETE)

---

## Completed Phases

| Phase | Name | Status | Tests |
|-------|------|--------|-------|
| P1    | 11-Screen Frontend UI | ✅ COMPLETE | — |
| P2a   | Electron Shell + IPC Bridge | ✅ COMPLETE | — |
| P2b   | Backend IPC Server (JSON Lines) | ✅ COMPLETE | 23 tests |
| P2c   | Frontend IPC Integration | ✅ COMPLETE | — |
| P3    | Real File Export (PDF/JSON/CSV) | ✅ COMPLETE | 46 tests |
| P4    | Garak Engine Adapter | ✅ COMPLETE | 30 tests |
| P5    | PyRIT Engine Adapter | ✅ COMPLETE | 30 tests |
| P6    | Normalization + Deduplication Pipeline | ✅ COMPLETE | 50 tests |
| P8    | Installer + Distribution | ✅ COMPLETE | — |

**Total backend tests: 1105 passed, 5 skipped**

---

## P6 — Normalization + Deduplication (COMPLETE)

**Files created/modified:**
- `app/backend/core/normalizer.py` — SchemaMapper, Deduplicator, OWASP coverage map
- `app/backend/ipc_server.py` — normalizer wired at step 4.5 in pipeline
- `app/backend/tests/test_normalizer.py` — 50 tests

**Key features:**
- OWASP LLM Top 10 (2025) classification for all findings
- Jaccard-based cross-engine deduplication (5-gram shingles, threshold 0.30)
- Confidence boosting: +0.10 per corroborating engine (cap 1.0)
- Severity = max across all corroborating engines
- OWASP coverage map: tested / with_findings / not_covered counts
- `normalization` key added to `complete` event payload

---

## P8 — Installer + Distribution (COMPLETE)

**Files created/modified:**
- `app/frontend/scripts/build-python.py` — PyInstaller build script
- `app/frontend/package.json` — build:python / build:all / dist scripts; NSIS config
- `app/frontend/resources/backend/` — output dir for PyInstaller bundle
- `app/frontend/electron/main.cjs` — smart spawn (bundled exe vs dev python)
- `app/frontend/vite.config.ts` — port corrected to 5173
- `docs/BUILD.md` — full build documentation

**Build commands:**
```bash
cd app/frontend
npm run build:python    # PyInstaller bundle
npm run build:electron  # Electron + NSIS installer
npm run build:all       # Both
npm run dev:electron    # Dev mode (Vite + Electron)
```

**Engine bundling:**
- garak 0.16.0 — ✅ installed, will be bundled
- pyrit 1.1.0 — ✅ installed, will be bundled
- MockEngine — ✅ always bundled (zero deps)

---

## Remaining Phases

| Phase | Name | Status |
|-------|------|--------|
| P7    | AWS Deployment Engine | 🔜 Optional v1 |
| P9    | Frontend Test Suite | 🔜 Next |
| —     | AgentGuardian adapter | 🔜 After garak+pyrit stable |

---

## Known Limitations

- PyInstaller bundle not yet tested end-to-end (run `npm run build:python` to test)
- App icon (`.ico`, `.icns`) not yet created — electron-builder will warn but build succeeds
- P7 (AWS deployment) is optional and not started

---

*All 1105 backend tests pass as of 2026-11-02.*
