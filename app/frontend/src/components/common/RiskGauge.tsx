/**
 * Sentryφ — RiskGauge Component (W4.3)
 * components/common/RiskGauge.tsx
 *
 * Animated SVG radial gauge for displaying risk scores 0–100.
 * Features:
 *   - Smooth arc fill animation on mount (1.4s cubic-bezier)
 *   - Animated counter from 0 → score
 *   - Color-coded arc: low (green) → medium (amber) → high (orange) → critical (red)
 *   - Responsive: accepts size prop
 *   - ARIA accessible with role="img" + aria-label
 */

import React, { useEffect, useRef, useState } from "react";

type RiskLevel = "low" | "medium" | "high" | "critical";

interface RiskGaugeProps {
  score: number;         // 0–100
  size?: number;         // SVG width/height px (default 160)
  strokeWidth?: number;  // Arc thickness (default 10)
  animated?: boolean;    // Enable animation (default true)
  label?: string;        // Below-score label (default "Risk Score")
  className?: string;
}

function getRiskLevel(score: number): RiskLevel {
  if (score < 25) return "low";
  if (score < 50) return "medium";
  if (score < 75) return "high";
  return "critical";
}

function getRiskColor(level: RiskLevel): string {
  switch (level) {
    case "low":      return "var(--severity-low)";
    case "medium":   return "var(--severity-medium)";
    case "high":     return "var(--severity-high)";
    case "critical": return "var(--severity-critical)";
  }
}

function getRiskLabel(level: RiskLevel): string {
  switch (level) {
    case "low":      return "LOW";
    case "medium":   return "MEDIUM";
    case "high":     return "HIGH";
    case "critical": return "CRITICAL";
  }
}

export function RiskGauge({
  score,
  size = 160,
  strokeWidth = 10,
  animated = true,
  label = "Risk Score",
  className = "",
}: RiskGaugeProps) {
  const clampedScore = Math.max(0, Math.min(100, score));
  const level = getRiskLevel(clampedScore);
  const color = getRiskColor(level);

  // SVG arc math
  const radius = (size - strokeWidth * 2) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const startAngle = -220; // degrees (bottom-left)
  const totalAngle = 260;  // sweep range

  const polarToCartesian = (angle: number) => {
    const rad = ((angle - 90) * Math.PI) / 180;
    return {
      x: cx + radius * Math.cos(rad),
      y: cy + radius * Math.sin(rad),
    };
  };

  const arcPath = (fromDeg: number, toDeg: number) => {
    const start = polarToCartesian(fromDeg);
    const end   = polarToCartesian(toDeg);
    const largeArc = toDeg - fromDeg > 180 ? 1 : 0;
    return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArc} 1 ${end.x} ${end.y}`;
  };

  const circumference = 2 * Math.PI * radius;
  const arcLength = (totalAngle / 360) * circumference;
  const fillLength = (clampedScore / 100) * arcLength;
  const dashOffset = arcLength - fillLength;

  // Animated counter
  const [displayScore, setDisplayScore] = useState(animated ? 0 : clampedScore);
  const animRef = useRef<number | null>(null);

  useEffect(() => {
    if (!animated) {
      setDisplayScore(clampedScore);
      return;
    }
    const duration = 1400;
    const start = performance.now();
    const from = 0;
    const to = clampedScore;

    const tick = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Cubic ease-out
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayScore(Math.round(from + (to - from) * eased));
      if (progress < 1) {
        animRef.current = requestAnimationFrame(tick);
      }
    };

    animRef.current = requestAnimationFrame(tick);
    return () => {
      if (animRef.current != null) cancelAnimationFrame(animRef.current);
    };
  }, [clampedScore, animated]);

  // The arc fills from startAngle to startAngle + totalAngle
  const fillPath = arcPath(startAngle, startAngle + totalAngle);

  return (
    <div
      className={`risk-gauge risk-gauge--${level} ${className}`}
      role="img"
      aria-label={`${label}: ${clampedScore} out of 100 — ${getRiskLabel(level)} risk`}
    >
      <svg
        width={size}
        height={size}
        className="risk-gauge__svg"
        aria-hidden="true"
      >
        {/* Track arc */}
        <path
          d={arcPath(startAngle, startAngle + totalAngle)}
          className="risk-gauge__track"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />

        {/* Fill arc — animated via stroke-dashoffset */}
        <path
          d={fillPath}
          className="risk-gauge__fill"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          stroke={color}
          strokeDasharray={`${arcLength} ${circumference}`}
          strokeDashoffset={animated ? dashOffset : dashOffset}
          style={{
            strokeDashoffset: dashOffset,
            transition: animated
              ? "stroke-dashoffset 1.4s cubic-bezier(0.4, 0, 0.2, 1)"
              : "none",
          }}
        />

        {/* Score number */}
        <text
          x={cx}
          y={cy - 6}
          className="risk-gauge__label"
          fill={color}
          fontSize={size * 0.22}
          fontWeight={700}
          fontFamily="Inter, sans-serif"
        >
          {displayScore}
        </text>

        {/* Sub-label: level */}
        <text
          x={cx}
          y={cy + size * 0.14}
          className="risk-gauge__sublabel"
          fontSize={size * 0.075}
          fill="var(--fg-muted)"
          fontFamily="Inter, sans-serif"
          fontWeight={500}
          letterSpacing="0.08em"
          textAnchor="middle"
        >
          {getRiskLabel(level)}
        </text>
      </svg>

      <span className="risk-gauge__title">{label}</span>
    </div>
  );
}

export default RiskGauge;
