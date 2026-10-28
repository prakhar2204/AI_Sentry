/**
 * Sentryɸ -- Agreement Page (Screen 1)
 * pages/AgreementPage.tsx
 *
 * Entry gate of the application. Compact, centered layout.
 * Displays Terms, Privacy, Disclaimer in collapsible sections,
 * a consent checkbox, and the primary CTA.
 *
 * On acceptance:
 *   - Dispatches ACCEPT_CONSENT to ScanContext
 *   - Consent persisted to localStorage by the reducer
 *   - Navigates to Input Screen (Step 2)
 */

import React, { useState, useCallback } from "react";
import { useScanContext } from "../store/ScanContext";
import { SCAN_ACTIONS } from "../store/actions";
import { Logo } from "../components/Logo";

interface AgreementPageProps {
  onAccept: () => void;
}

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
      <div className="agreement-page__content">

        {/* ── Brand Header ── */}
        <div className="agreement-page__header">
          <div className="agreement-page__logo">
            <Logo size={32} animate={false} />
          </div>
          <div className="agreement-page__brand">Sentryɸ</div>
          <div className="agreement-page__tagline">AI Security Scanner</div>
        </div>

        {/* ── Terms of Use ── */}
        <section className="agreement-page__section">
          <h2 className="agreement-page__section-title">Terms of Use</h2>
          <div className="agreement-page__section-body">
            <ol className="agreement-page__list">
              <li>
                <strong>Authorized Use Only.</strong> You must have explicit
                authorization to scan the target. Unauthorized scanning may
                violate applicable laws.
              </li>
              <li>
                <strong>Accuracy Disclaimer.</strong> Results are advisory and
                do not constitute a guarantee of security or compliance.
              </li>
              <li>
                <strong>No Warranty.</strong> Provided "as is" without warranty
                of any kind.
              </li>
              <li>
                <strong>Usage Limits.</strong> You agree not to use this tool
                for denial-of-service attacks or unauthorized data extraction.
              </li>
            </ol>
          </div>
        </section>

        {/* ── Privacy Notice ── */}
        <section className="agreement-page__section">
          <h2 className="agreement-page__section-title">Privacy</h2>
          <div className="agreement-page__section-body">
            <ol className="agreement-page__list">
              <li>
                <strong>Local Processing.</strong> All scan data is processed
                on your machine. Nothing is transmitted to external servers.
              </li>
              <li>
                <strong>No Data Collection.</strong> No personal information,
                usage analytics, or telemetry is collected.
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
              I have read and agree to the Terms of Use and Privacy Notice. I
              understand the risks of security scanning and accept full
              responsibility for my use of this tool.
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

        <p className="agreement-page__version">v1.0.0 · Local Only</p>

      </div>
    </div>
  );
}
