/**
 * AI-SENTRY -- Input Page (Screen 2)
 * pages/InputPage.tsx
 *
 * User provides the LLM target source. Two modes:
 *
 *   LOCAL:  Model file via drag-drop, browse, or manual path
 *   API:    Endpoint URL (must start with http:// or https://)
 *
 * Optional: Manifest JSON file (drag-drop or browse)
 *
 * On "Continue":
 *   - Validates inputs (inline errors)
 *   - Updates ScanContext: target, mode, manifest_file
 *   - Dispatches START_CONFIGURING
 *   - Navigates to Config screen (Step 3)
 *
 * Follows UI_ARCHITECTURE.md:
 *   - Section 2: Screen 2 definition
 *   - Section 3: ScanContext fields (target, mode, manifest_file)
 *   - Section 7: UX rules (single column, disable don't hide, inline errors)
 *   - Section 8: Edge cases (invalid URL, empty submission, mode switch)
 */

import React, { useState, useCallback, useMemo } from "react";
import { useScanContext, type ScanMode } from "../store/ScanContext";
import { SCAN_ACTIONS } from "../store/actions";
import { PageHeader } from "../components/layout/PageHeader";
import { RadioGroup } from "../components/forms/RadioGroup";
import { TextInput } from "../components/forms/TextInput";
import { FileDropZone } from "../components/forms/FileDropZone";

// ─────────────────────────────────────────────
//  Constants
// ─────────────────────────────────────────────

const MODE_OPTIONS = [
  { value: "local", label: "Local Model" },
  { value: "api", label: "API Endpoint" },
];

// ─────────────────────────────────────────────
//  Validation
// ─────────────────────────────────────────────

function validateUrl(url: string): string | null {
  if (!url.trim()) {
    return "URL is required.";
  }
  const trimmed = url.trim();
  if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) {
    return "Invalid URL. Must start with http:// or https://";
  }
  try {
    new URL(trimmed);
  } catch {
    return "Invalid URL format.";
  }
  return null;
}

function validateLocalTarget(
  filePath: string,
  fileName: string | null
): string | null {
  // Allow either:
  //   a) A URL (http://localhost:11434/...) — the inference server endpoint
  //   b) A file path / filename (displayed info only; actual target will be the server URL)
  if (fileName) return null; // file was dropped/browsed — show friendly name
  if (!filePath.trim()) {
    return "Provide a model file path or enter a local server URL (e.g. http://localhost:11434).";
  }
  return null;
}

// ─────────────────────────────────────────────
//  Props
// ─────────────────────────────────────────────

interface InputPageProps {
  onContinue: () => void;
  onBack: () => void;
}

// ─────────────────────────────────────────────
//  Component
// ─────────────────────────────────────────────

export function InputPage({ onContinue, onBack }: InputPageProps) {
  const { state, dispatch } = useScanContext();

  // ── Local state ──
  const [mode, setMode] = useState<ScanMode>(state.mode || "local");
  const [apiUrl, setApiUrl] = useState(
    state.mode === "api" && state.target ? state.target : ""
  );
  const [localPath, setLocalPath] = useState(
    state.mode === "local" && state.target ? state.target : ""
  );
  const [localFileName, setLocalFileName] = useState<string | null>(null);
  const [manifestFileName, setManifestFileName] = useState<string | null>(
    null
  );
  const [manifestFilePath, setManifestFilePath] = useState<string | null>(
    state.manifest_file
  );

  // ── Validation errors ──
  const [targetError, setTargetError] = useState<string | null>(null);
  const [manifestError, setManifestError] = useState<string | null>(null);

  // ── Mode switch handler ──
  const handleModeChange = useCallback((value: string) => {
    const newMode = value as ScanMode;
    setMode(newMode);

    // Reset irrelevant inputs on mode switch
    if (newMode === "api") {
      setLocalPath("");
      setLocalFileName(null);
    } else {
      setApiUrl("");
    }

    // Clear validation errors
    setTargetError(null);
  }, []);

  // ── File handlers ──

  /**
   * Native Electron file picker — gets the REAL full disk path.
   * The browser File API only gives filename, not the path Python needs.
   */
  const handleNativeFilePicker = useCallback(async () => {
    const api = (window as any).electronAPI;
    if (api?.openModelFilePicker) {
      const result = await api.openModelFilePicker();
      if (result) {
        setLocalFileName(result.fileName);
        setLocalPath(result.filePath);   // REAL full path, e.g. D:\models\model.gguf
        setTargetError(null);
      }
    } else {
      // Browser fallback: trigger the hidden file input
      document.getElementById("local-model-file-input")?.click();
    }
  }, []);

  /**
   * Browser drag-and-drop / file input fallback (browser mode only).
   * In Electron, the full path is NOT available via File API — use native picker instead.
   */
  const handleLocalFile = useCallback((file: File) => {
    setLocalFileName(file.name);
    // In Electron, file.path is available via the File API (Chromium extension)
    const electronPath = (file as any).path;
    if (electronPath) {
      setLocalPath(electronPath);  // Real path via Electron's File.path extension
    } else {
      setLocalPath(file.name);     // Browser fallback — filename only
    }
    setTargetError(null);
  }, []);

  const handleManifestFile = useCallback((file: File) => {
    // Validate it's a JSON file
    if (!file.name.toLowerCase().endsWith(".json")) {
      setManifestError("Invalid file type. Expected a .json file.");
      return;
    }
    setManifestFileName(file.name);
    setManifestFilePath(file.name);
    setManifestError(null);
  }, []);

  // ── Determine if form is submittable ──
  const hasTarget = useMemo(() => {
    if (mode === "api") return apiUrl.trim().length > 0;
    return localPath.trim().length > 0 || localFileName !== null;
  }, [mode, apiUrl, localPath, localFileName]);

  // ── Submit handler ──
  const handleContinue = useCallback(() => {
    // Validate target
    if (mode === "api") {
      const err = validateUrl(apiUrl);
      if (err) {
        setTargetError(err);
        return;
      }
    } else {
      const err = validateLocalTarget(localPath, localFileName);
      if (err) {
        setTargetError(err);
        return;
      }
    }

    // Determine target value
    // For local mode: localPath holds the full disk path (from native picker)
    // or HTTP URL if manually typed. ScanPage will route accordingly.
    const target = mode === "api" ? apiUrl.trim() : localPath.trim();

    // Update ScanContext
    dispatch({ type: SCAN_ACTIONS.SET_MODE, payload: mode });
    dispatch({ type: SCAN_ACTIONS.SET_TARGET, payload: target });
    dispatch({
      type: SCAN_ACTIONS.SET_MANIFEST_FILE,
      payload: manifestFilePath,
    });
    // Store full disk path separately so Python backend can auto-load the model
    if (mode === "local" && localPath && !localPath.startsWith("http")) {
      dispatch({
        type: SCAN_ACTIONS.SET_LOCAL_MODEL_PATH as any,
        payload: localPath,
      });
    } else {
      dispatch({
        type: SCAN_ACTIONS.SET_LOCAL_MODEL_PATH as any,
        payload: null,
      });
    }
    dispatch({ type: SCAN_ACTIONS.START_CONFIGURING });

    onContinue();
  }, [
    mode,
    apiUrl,
    localPath,
    localFileName,
    manifestFilePath,
    dispatch,
    onContinue,
  ]);

  return (
    <div className="input-page">
      <PageHeader
        title="Select Target"
        subtitle="Choose a model source to scan."
        onBack={onBack}
      />

      <div className="input-page__content">

        {/* ── Mode Selection ── */}
        <section className="input-page__section">
          <RadioGroup
            legend="Scan Mode"
            options={MODE_OPTIONS}
            selected={mode}
            onChange={handleModeChange}
            name="scan-mode"
          />
        </section>

        {/* ── Local Model Input ── */}
        {mode === "local" && (
          <section className="input-page__section" id="local-input-section">

            {/* Primary: native file picker button (Electron) or drag-drop (browser) */}
            {(window as any).electronAPI?.openModelFilePicker ? (
              <div className="input-page__native-picker">
                <div className="input-page__native-picker-label">Model File (.gguf)</div>
                {localFileName ? (
                  <div className="input-page__native-picker-selected" id="selected-model-display">
                    <span className="input-page__file-icon">&#x1F916;</span>
                    <span className="input-page__file-name">{localFileName}</span>
                    <button
                      type="button"
                      className="input-page__file-clear"
                      onClick={() => { setLocalFileName(null); setLocalPath(""); }}
                      aria-label="Remove model"
                    >&#x2715;</button>
                  </div>
                ) : (
                  <button
                    type="button"
                    className="input-page__native-picker-btn"
                    onClick={handleNativeFilePicker}
                    id="browse-model-button"
                  >
                    <span className="input-page__file-icon">&#x1F4C2;</span>
                    Browse for Model File&#8230;
                  </button>
                )}
                {targetError && (
                  <p className="input-page__field-error" role="alert">{targetError}</p>
                )}
                <p className="input-page__native-picker-hint">
                  Supports .gguf format. GPU acceleration applied automatically.
                </p>
              </div>
            ) : (
              /* Browser fallback: drag-and-drop */
              <FileDropZone
                label="Model File"
                id="local-model-file"
                accept=".gguf,.bin,.safetensors"
                onFile={handleLocalFile}
                fileName={localFileName || undefined}
                error={targetError || undefined}
                disabled={false}
              />
            )}

            <div className="input-page__separator">
              <span className="input-page__separator-text">or enter server URL</span>
            </div>

            <TextInput
              label="Local Server URL (if already running)"
              id="local-model-path"
              value={localPath.startsWith("http") ? localPath : ""}
              onChange={(val) => {
                if (val.trim()) {
                  setLocalPath(val);
                  setLocalFileName(null);
                  setTargetError(null);
                }
              }}
              placeholder="http://localhost:11434/v1/chat/completions"
              error={!localFileName && !localPath.startsWith("http") ? targetError || undefined : undefined}
            />
          </section>
        )}

        {/* ── API Endpoint Input ── */}
        {mode === "api" && (
          <section className="input-page__section" id="api-input-section">
            <TextInput
              label="API Endpoint URL"
              id="api-endpoint-url"
              type="url"
              value={apiUrl}
              onChange={(val) => {
                setApiUrl(val);
                setTargetError(null);
              }}
              placeholder="https://api.openai.com/v1"
              error={targetError || undefined}
            />
          </section>
        )}

        {/* ── Optional Manifest ── */}
        <section className="input-page__section">
          <FileDropZone
            label="Manifest File (optional)"
            id="manifest-file"
            accept=".json,application/json"
            onFile={handleManifestFile}
            fileName={manifestFileName || undefined}
            error={manifestError || undefined}
            disabled={false}
          />
          {manifestFileName && (
            <button
              type="button"
              className="button button--ghost"
              onClick={() => {
                setManifestFileName(null);
                setManifestFilePath(null);
                setManifestError(null);
              }}
              id="clear-manifest-button"
            >
              Clear manifest
            </button>
          )}
        </section>

        {/* ── Primary Action ── */}
        <div className="input-page__actions">
          <button
            type="button"
            className="button button--primary"
            disabled={!hasTarget}
            onClick={handleContinue}
            id="input-continue-button"
          >
            Continue
          </button>
        </div>

      </div>
    </div>
  );
}
