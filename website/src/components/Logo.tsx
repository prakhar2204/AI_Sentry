import React from 'react';

interface LogoProps {
  size?: number;
  className?: string;
}

/**
 * AI-SENTRY Shield Logo
 * A geometric shield with integrated scan-line motif.
 * Used in both the website navbar and the desktop app.
 */
export function Logo({ size = 28, className }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="AI Sentry"
    >
      {/* Outer shield */}
      <path
        d="M16 2 L28 8 L28 18 C28 24 22 29 16 30 C10 29 4 24 4 18 L4 8 Z"
        stroke="var(--accent, #3D7EFF)"
        strokeWidth="1.8"
        fill="none"
        strokeLinejoin="round"
      />
      {/* Inner shield */}
      <path
        d="M16 6 L24 10 L24 17 C24 21.5 20 25.5 16 26.5 C12 25.5 8 21.5 8 17 L8 10 Z"
        stroke="var(--accent, #3D7EFF)"
        strokeWidth="1.2"
        fill="none"
        strokeLinejoin="round"
        opacity="0.6"
      />
      {/* Scan lines inside inner shield */}
      <line x1="10" y1="13" x2="22" y2="13" stroke="var(--accent, #3D7EFF)" strokeWidth="0.8" opacity="0.4" />
      <line x1="10.5" y1="15.5" x2="21.5" y2="15.5" stroke="var(--accent, #3D7EFF)" strokeWidth="0.8" opacity="0.5" />
      <line x1="11" y1="18" x2="21" y2="18" stroke="var(--accent, #3D7EFF)" strokeWidth="0.8" opacity="0.6" />
      <line x1="12" y1="20.5" x2="20" y2="20.5" stroke="var(--accent, #3D7EFF)" strokeWidth="0.8" opacity="0.4" />
      {/* Active scan line (animated in CSS) */}
      <line
        x1="10" y1="16" x2="22" y2="16"
        stroke="var(--accent, #3D7EFF)"
        strokeWidth="1.5"
        opacity="0.9"
        className="logo-scan-line"
      />
    </svg>
  );
}

/**
 * Logo with wordmark for nav / footer.
 */
export function LogoFull({ size = 28, className }: LogoProps) {
  return (
    <span style={{ display: 'flex', alignItems: 'center', gap: '10px' }} className={className}>
      <Logo size={size} />
      <span style={{
        fontWeight: 600,
        fontSize: '16px',
        letterSpacing: '-0.3px',
        color: 'var(--text-primary, #F0F2F8)',
      }}>
        AI Sentry
      </span>
    </span>
  );
}
