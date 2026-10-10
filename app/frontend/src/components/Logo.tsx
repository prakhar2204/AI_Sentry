'use client';

import React from 'react';

interface LogoProps {
  size?: number;
  className?: string;
  animate?: boolean;
}

/**
 * Sentryɸ Phi Logo
 * An animated shield-phi monogram. The phi symbol (ɸ) is built from
 * geometric strokes inside a shield silhouette, with a rotating
 * scan-ring and pulsing glow. Used in navbar, footer, and app header.
 */
export function Logo({ size = 28, className, animate = true }: LogoProps) {
  const id = React.useId();
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Sentryɸ"
    >
      <defs>
        {/* Accent gradient for the shield */}
        <linearGradient id={`${id}-grad`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#5A93FF" />
          <stop offset="50%" stopColor="#3D7EFF" />
          <stop offset="100%" stopColor="#2B6BF0" />
        </linearGradient>
        {/* Glow filter */}
        <filter id={`${id}-glow`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="1.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Shield outline */}
      <path
        d="M20 2 L34 9 L34 20 C34 28 27 34 20 36 C13 34 6 28 6 20 L6 9 Z"
        stroke={`url(#${id}-grad)`}
        strokeWidth="1.6"
        fill="none"
        strokeLinejoin="round"
        opacity="0.85"
      />

      {/* Inner shield fill (very subtle) */}
      <path
        d="M20 5 L31 10.5 L31 19.5 C31 26 25.5 31 20 32.5 C14.5 31 9 26 9 19.5 L9 10.5 Z"
        fill="rgba(61, 126, 255, 0.04)"
        stroke={`url(#${id}-grad)`}
        strokeWidth="0.6"
        strokeLinejoin="round"
        opacity="0.5"
      />

      {/* PHI SYMBOL — the vertical stroke */}
      <line
        x1="20" y1="9" x2="20" y2="31"
        stroke={`url(#${id}-grad)`}
        strokeWidth="1.8"
        strokeLinecap="round"
        filter={animate ? `url(#${id}-glow)` : undefined}
      />

      {/* PHI SYMBOL — the oval/circle */}
      <ellipse
        cx="20" cy="19"
        rx="6.5" ry="7.5"
        stroke={`url(#${id}-grad)`}
        strokeWidth="1.6"
        fill="none"
        filter={animate ? `url(#${id}-glow)` : undefined}
      />

      {/* Scan ring — orbiting dot */}
      {animate && (
        <circle r="1.2" fill="#5A93FF" opacity="0.9">
          <animateMotion
            dur="4s"
            repeatCount="indefinite"
            path="M20,11.5 C26.5,11.5 26.5,26.5 20,26.5 C13.5,26.5 13.5,11.5 20,11.5"
          />
          <animate
            attributeName="opacity"
            values="0.4;1;0.4"
            dur="4s"
            repeatCount="indefinite"
          />
        </circle>
      )}

      {/* Pulse ring */}
      {animate && (
        <ellipse
          cx="20" cy="19"
          rx="6.5" ry="7.5"
          stroke="#3D7EFF"
          strokeWidth="0.5"
          fill="none"
          opacity="0"
        >
          <animate
            attributeName="rx" values="6.5;11;14"
            dur="3s" repeatCount="indefinite"
          />
          <animate
            attributeName="ry" values="7.5;12;15"
            dur="3s" repeatCount="indefinite"
          />
          <animate
            attributeName="opacity" values="0.6;0.2;0"
            dur="3s" repeatCount="indefinite"
          />
        </ellipse>
      )}

      {/* Corner scan lines (decorative) */}
      <line x1="10" y1="14" x2="13" y2="14" stroke="#3D7EFF" strokeWidth="0.5" opacity="0.3" />
      <line x1="27" y1="14" x2="30" y2="14" stroke="#3D7EFF" strokeWidth="0.5" opacity="0.3" />
      <line x1="10" y1="24" x2="13" y2="24" stroke="#3D7EFF" strokeWidth="0.5" opacity="0.3" />
      <line x1="27" y1="24" x2="30" y2="24" stroke="#3D7EFF" strokeWidth="0.5" opacity="0.3" />
    </svg>
  );
}

/**
 * Stylized Sentryɸ wordmark.
 * "Sentry" in light weight, "ɸ" in accent gradient with glow.
 */
export function BrandTitle({
  size = 'md',
  className,
}: {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}) {
  const fontSize = size === 'sm' ? '15px' : size === 'md' ? '18px' : '24px';
  const phiSize = size === 'sm' ? '17px' : size === 'md' ? '22px' : '30px';

  return (
    <span
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'baseline',
        fontFamily: "'Inter', sans-serif",
        letterSpacing: '-0.5px',
      }}
    >
      <span
        style={{
          fontWeight: 600,
          fontSize,
          color: 'var(--text-primary, #F0F2F8)',
        }}
      >
        Sentry
      </span>
      <span
        style={{
          fontWeight: 700,
          fontSize: phiSize,
          background: 'linear-gradient(135deg, #5A93FF 0%, #3D7EFF 50%, #7C4DFF 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
          filter: 'drop-shadow(0 0 8px rgba(61, 126, 255, 0.4))',
          marginLeft: '1px',
        }}
      >
        ɸ
      </span>
    </span>
  );
}

/**
 * Logo + Wordmark combo for nav / footer.
 */
export function LogoFull({ size = 28, className }: LogoProps) {
  return (
    <span
      style={{ display: 'flex', alignItems: 'center', gap: '10px' }}
      className={className}
    >
      <Logo size={size} />
      <BrandTitle size="md" />
    </span>
  );
}
