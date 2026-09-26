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
  // Either a dropped/browsed file or a manual path is required
  if (fileName) return null; // file was dropped/browsed — valid
  if (!filePath.trim()) {
    return "Provide a model file or enter a file path.";
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
  const handleLocalFile = useCallback((file: File) => {
    setLocalFileName(file.name);
    setLocalPath(file.name);
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
    const target = mode === "api" ? apiUrl.trim() : localPath.trim();

    // Update ScanContext
    dispatch({ type: SCAN_ACTIONS.SET_MODE, payload: mode });
    dispatch({ type: SCAN_ACTIONS.SET_TARGET, payload: target });
    dispatch({
      type: SCAN_ACTIONS.SET_MANIFEST_FILE,
      payload: manifestFilePath,
    });
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
            <FileDropZone
              label="Model File"
              id="local-model-file"
              accept=".gguf,.bin,.safetensors,.pt,.onnx"
              onFile={handleLocalFile}
              fileName={localFileName || undefined}
              error={undefined}
              disabled={false}
            />

            <div className="input-page__separator">
              <span className="input-page__separator-text">or</span>
            </div>

            <TextInput
              label="File Path"
              id="local-model-path"
              value={localPath}
              onChange={(val) => {
                setLocalPath(val);
                setLocalFileName(null); // manual path overrides file drop
                setTargetError(null);
              }}
              placeholder="/path/to/model.gguf or http://localhost:8080"
              error={targetError || undefined}
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
