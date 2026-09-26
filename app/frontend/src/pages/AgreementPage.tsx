/**
 * AI-SENTRY -- Agreement Page (Screen 1)
 * pages/AgreementPage.tsx
 *
 * Entry point of the application. Displays:
 *   - Terms of Use (structured sections)
 *   - Privacy Notice
 *   - Disclaimer (scanning responsibility)
 *   - Required consent checkbox
 *   - "Agree & Continue" button (disabled until checked)
 *
 * On acceptance:
 *   - Dispatches ACCEPT_CONSENT to ScanContext
 *   - Consent persisted to localStorage by the reducer
 *   - Navigates to Input Screen (Step 2)
 *
 * Bypass protection:
 *   - If consent_given is already true (from localStorage),
 *     the parent router should skip this page entirely.
 *   - The checkbox is required; button is disabled until checked.
 *
 * Follows UI_ARCHITECTURE.md:
 *   - Section 2: Screen 1 definition
 *   - Section 3: ScanContext consent_given
 *   - Section 7: UX rules (single column, no animations, no clutter)
 *   - Section 8: Edge cases (prevent bypass, handle reload)
 */

import React, { useState, useCallback } from "react";
import { useScanContext } from "../store/ScanContext";
import { SCAN_ACTIONS } from "../store/actions";
import { PageHeader } from "../components/layout/PageHeader";

// ─────────────────────────────────────────────
//  Props
// ─────────────────────────────────────────────

interface AgreementPageProps {
  /** Called after consent is accepted; parent handles navigation */
  onAccept: () => void;
}

// ─────────────────────────────────────────────
//  Component
// ─────────────────────────────────────────────

export function AgreementPage({ onAccept }: AgreementPageProps) {
  const { dispatch } = useScanContext();
  const [agreed, setAgreed] = useState(false);

  const handleCheckboxChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setAgreed(e.target.checked);
    },
    []
  );

  const handleAccept = useCallback(() => {
    if (!agreed) return;
    dispatch({ type: SCAN_ACTIONS.ACCEPT_CONSENT });
    onAccept();
  }, [agreed, dispatch, onAccept]);

  return (
    <div className="agreement-page">
      <PageHeader
        title="Agreement & Consent"
        subtitle="Please review and accept before proceeding."
      />

      <div className="agreement-page__content">

        {/* ── Terms of Use ── */}
        <section className="agreement-page__section">
          <h2 className="agreement-page__section-title">Terms of Use</h2>
          <div className="agreement-page__section-body">
            <p>
              By using AI Sentry, you agree to the following terms:
            </p>
            <ol className="agreement-page__list">
              <li>
                <strong>Authorized Use Only.</strong> You must have explicit
                authorization to perform security scans on the target system.
                Unauthorized scanning may violate applicable laws.
              </li>
              <li>
                <strong>Accuracy Disclaimer.</strong> AI Sentry provides
                automated security assessments. Results are advisory and do
                not constitute a guarantee of security or compliance.
              </li>
              <li>
                <strong>No Warranty.</strong> This tool is provided "as is"
                without warranty of any kind. The developers are not liable
                for any damages resulting from its use.
              </li>
              <li>
                <strong>Usage Limits.</strong> You agree not to use this tool
                for denial-of-service attacks, unauthorized data extraction,
                or any activity that violates applicable laws.
              </li>
            </ol>
          </div>
        </section>

        {/* ── Privacy Notice ── */}
        <section className="agreement-page__section">
          <h2 className="agreement-page__section-title">Privacy Notice</h2>
          <div className="agreement-page__section-body">
            <ol className="agreement-page__list">
              <li>
                <strong>Local Processing.</strong> All scan data is processed
                locally on your machine. No scan results, target information,
                or findings are transmitted to external servers.
              </li>
              <li>
                <strong>No Data Collection.</strong> AI Sentry does not collect
                personal information, usage analytics, or telemetry data.
              </li>
              <li>
                <strong>Report Storage.</strong> Scan reports are stored locally
                in the directory you specify. You are responsible for securing
                exported reports.
              </li>
            </ol>
          </div>
        </section>

        {/* ── Disclaimer ── */}
        <section className="agreement-page__section">
          <h2 className="agreement-page__section-title">Disclaimer</h2>
          <div className="agreement-page__section-body">
            <ol className="agreement-page__list">
              <li>
                <strong>Security Scanning Tool.</strong> AI Sentry performs
                automated security probes against AI and LLM systems to
                identify vulnerabilities such as prompt injection, jailbreak
                susceptibility, data leakage, and harmful output generation.
              </li>
              <li>
                <strong>User Responsibility.</strong> You are solely responsible
                for how you use this tool and the actions you take based on its
                findings. Ensure you have proper authorization before scanning
                any system.
              </li>
              <li>
                <strong>Impact Awareness.</strong> Security probes may trigger
                rate limits, logging alerts, or other responses from the target
                system. You acknowledge this risk.
              </li>
            </ol>
          </div>
        </section>

        {/* ── Consent Checkbox ── */}
        <div className="agreement-page__consent">
          <label className="agreement-page__checkbox-label">
            <input
              type="checkbox"
              checked={agreed}
              onChange={handleCheckboxChange}
              className="agreement-page__checkbox"
              id="consent-checkbox"
            />
            <span>
              I have read and agree to the Terms of Use, Privacy Notice, and
              Disclaimer. I understand the risks associated with security
              scanning and accept full responsibility for my use of this tool.
            </span>
          </label>
        </div>

        {/* ── Primary Action ── */}
        <div className="agreement-page__actions">
          <button
            type="button"
            className="button button--primary"
            disabled={!agreed}
            onClick={handleAccept}
            id="agree-continue-button"
          >
            Agree &amp; Continue
          </button>
        </div>

      </div>
    </div>
  );
}
