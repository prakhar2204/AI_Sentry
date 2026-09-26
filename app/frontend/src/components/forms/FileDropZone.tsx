/**
 * AI-SENTRY -- FileDropZone Component
 * components/forms/FileDropZone.tsx
 *
 * Drag-and-drop file input with fallback browse button.
 * Shows file name after successful drop/selection.
 *
 * Props follow UI_ARCHITECTURE.md Section 6:
 *   onFile, accept, error
 *
 * Edge cases handled:
 *   - Invalid file type (checked against accept list)
 *   - Drag-drop failure (event errors caught)
 *   - Multiple files dropped (only first accepted)
 */

import React, { useState, useCallback, useRef } from "react";

interface FileDropZoneProps {
  /** Called with the selected File object */
  onFile: (file: File) => void;
  /** Comma-separated MIME types or extensions, e.g. ".json,application/json" */
  accept: string;
  /** Currently selected file name to display */
  fileName?: string;
  /** Error message to display */
  error?: string;
  /** Label text above the drop zone */
  label: string;
  /** Unique ID for the hidden file input */
  id: string;
  /** Disable interaction */
  disabled?: boolean;
}

export function FileDropZone({
  onFile,
  accept,
  fileName,
  error,
  label,
  id,
  disabled = false,
}: FileDropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = useCallback(
    (file: File): boolean => {
      if (!accept) return true;

      const acceptList = accept.split(",").map((a) => a.trim().toLowerCase());

      for (const acceptEntry of acceptList) {
        // Extension check (e.g., ".json")
        if (acceptEntry.startsWith(".")) {
          if (file.name.toLowerCase().endsWith(acceptEntry)) return true;
        }
        // MIME type check (e.g., "application/json")
        if (file.type && file.type.toLowerCase() === acceptEntry) return true;
      }

      return false;
    },
    [accept]
  );

  const handleFile = useCallback(
    (file: File) => {
      if (disabled) return;
      if (!validateFile(file)) return;
      onFile(file);
    },
    [disabled, validateFile, onFile]
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled) setIsDragOver(true);
    },
    [disabled]
  );

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);

      if (disabled) return;

      try {
        const files = e.dataTransfer?.files;
        if (files && files.length > 0) {
          handleFile(files[0]);
        }
      } catch {
        // Drag-drop failure — silently ignore
      }
    },
    [disabled, handleFile]
  );

  const handleBrowseClick = useCallback(() => {
    if (disabled) return;
    fileInputRef.current?.click();
  }, [disabled]);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        handleFile(files[0]);
      }
      // Reset input so the same file can be re-selected
      e.target.value = "";
    },
    [handleFile]
  );

  const zoneClasses = [
    "file-drop-zone",
    isDragOver ? "file-drop-zone--drag-over" : "",
    error ? "file-drop-zone--error" : "",
    disabled ? "file-drop-zone--disabled" : "",
    fileName ? "file-drop-zone--has-file" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={zoneClasses}>
      <label className="file-drop-zone__label">{label}</label>

      <div
        className="file-drop-zone__area"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label={`Drop zone for ${label}`}
        onClick={handleBrowseClick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") handleBrowseClick();
        }}
      >
        {fileName ? (
          <p className="file-drop-zone__filename">{fileName}</p>
        ) : (
          <p className="file-drop-zone__hint">
            Drag and drop a file here, or click to browse.
          </p>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        id={id}
        accept={accept}
        onChange={handleInputChange}
        className="file-drop-zone__input"
        tabIndex={-1}
        aria-hidden="true"
        disabled={disabled}
      />

      {error && (
        <p className="file-drop-zone__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
