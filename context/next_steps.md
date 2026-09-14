# AI-SENTRY — Next Steps

**Last Updated:** 2026-09-13  
**Current Phase:** 0b COMPLETE  
**Immediately Next Phase:** Phase 1 — Project Scaffold & Environment Setup

---

## Immediate Next Actions (Phase 1)

Phase 1 goal: Create the runnable project skeleton with working directory structure, dependency management, environment auto-detection, and logging. No user-facing features. No business logic.

### Phase 1 Task List

#### 1.1 — Directory Structure
Create the full project directory structure matching the target layout from `context/project_overview.md`. All directories created; placeholder files where needed.

#### 1.2 — Dependency Management
Configure Python dependency management:
- `pyproject.toml` (preferred) or `requirements.txt`
- Engine dependencies: garak (pinned), pyrit-ai (pinned), deepeval (pinned)
- AWS SDK: boto3
- UI framework: Electron or Tauri (decision needed)
- Packaging: PyInstaller or equivalent for desktop distribution

**Decision needed before 1.2:** UI framework selection (Electron vs Tauri). See OQ note below.

#### 1.3 — Environment Health Check Tool
An internal tool that verifies:
- Python version compatibility
- All engine packages installed at correct versions
- Hardware detection (RAM, VRAM, CPU)
- llama.cpp availability (for local models)
- OS keychain accessibility

#### 1.4 — Configuration Management System
Design the configuration schema and persistence layer:
- User preferences (scan defaults, cost limits, UI settings)
- Engine configuration (version pins, probe category enables)
- Storage location: platform-appropriate app data directory

#### 1.5 — Logging Infrastructure
Structured logging system:
- Separate log channels: application, orchestration, engine-specific, security (probe content — encrypted)
- Log rotation and retention policy
- No sensitive data (API keys, probe content) in application logs

#### 1.6 — Basic CLI Skeleton
A runnable CLI that accepts model input and scan configuration flags (even if it does nothing yet). This establishes the interface that Phase 1.5 CI/CD integration will use.

---

## Phase 2 Preview (Model Adapter Layer)

After Phase 1 is complete, Phase 2 begins with the Model Adapter Layer.

**Phase 2 goal:** Implement fully working model adapters for all supported model types. By end of Phase 2, AI-SENTRY can connect to any supported model, validate connectivity, estimate cost, and send test prompts.

**Phase 2 key tasks:**
- Implement `ModelAdapter` abstract interface
- Implement `OpenAICompatibleAdapter`
- Implement `AzureOpenAIAdapter`
- Implement `LocalGGUFAdapter` (with llama.cpp management)
- Implement `HuggingFaceAdapter`
- Implement `GenericRESTAdapter` (with schema inference wizard)
- Implement `ScanManifest` data model
- Implement hardware detection and compatibility checking

---

## Pending Decisions Needed Before Phase 1

| Decision | Options | Recommendation | Urgency |
|---|---|---|---|
| Desktop UI framework | Electron (JS/HTML) vs Tauri (Rust + WebView) vs PySide6 | Tauri or Electron for cross-platform; PySide6 if Python-only preferred | Before Phase 1.2 |
| Python packaging tool | pip + venv vs conda vs uv | uv for speed; pip+venv for simplicity | Before Phase 1.2 |
| Probe payload storage default | Store always vs store on opt-in | Opt-in only (privacy-first default) | Before Phase 1.5 |

---

## Phase Roadmap (Full)

```
Phase 0a — Idea Design                    ✅ COMPLETE
Phase 0b — Documentation Foundation       ✅ COMPLETE (current)
Phase 1  — Project Scaffold               🔲 NEXT
Phase 2  — Model Adapter Layer            🔲
Phase 3  — Engine Adapters                🔲 (Garak, PyRIT, DeepTeam)
Phase 4  — Normalization Layer            🔲
Phase 5  — Intelligence Layer             🔲 (Scoring, Remediation)
Phase 6  — Report Generator              🔲
Phase 7  — Deployment Advisor + AWS       🔲
Phase 8  — Desktop Application UI         🔲
Phase 9  — Website                        🔲
Phase 10 — Integration Testing            🔲
Phase 11 — Launch Prep                   🔲
```

---

## Dependencies Between Phases

```
Phase 1 (Scaffold)
    ↓
Phase 2 (Model Adapter) ←── Must complete before Phase 3
    ↓
Phase 3 (Engine Adapters) ←── All three engines in parallel
    ↓
Phase 4 (Normalization) ←── Requires Phase 3 output schema
    ↓
Phase 5 (Intelligence) ←── Requires Phase 4 schema
    ↓
Phase 6 (Reporting) ──────┐
Phase 7 (Deployment)  ────┤ ←── Both require Phase 5 output
                          ↓
Phase 8 (Desktop UI) ←─── Requires Phases 6 + 7
    ↓
Phase 9 (Website) ←── Can run in parallel with Phase 8
    ↓
Phase 10 (Integration Testing)
    ↓
Phase 11 (Launch Prep)
```

---

## Notes for AI Tools Reading This File

- This file is updated at the start of each new phase
- "Pending Decisions" in this file should be resolved before implementation begins on the relevant phase
- The phase roadmap is the authoritative sequence — do not skip phases
- When starting any phase, read `context/current_phase.md` first to confirm phase status
- All architectural decisions are in `context/decisions.md` — do not make architecture choices without checking that file first
