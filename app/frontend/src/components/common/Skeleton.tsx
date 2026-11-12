/**
 * Sentryφ — Skeleton Components (W4.4)
 * components/common/Skeleton.tsx
 *
 * Reusable skeleton loading states for all major page layouts.
 * Uses CSS shimmer animation from index.css .skeleton class.
 */

import React from "react";

interface SkeletonProps {
  className?: string;
  width?: string | number;
  height?: string | number;
  style?: React.CSSProperties;
}

export function Skeleton({ className = "", width, height, style }: SkeletonProps) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{ width, height, ...style }}
      aria-hidden="true"
    />
  );
}

/** Text-line skeleton, with optional width control */
export function SkeletonText({ width = "100%", lines = 1, gap = 8 }: { width?: string | number; lines?: number; gap?: number }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap }} aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className="skeleton--text"
          width={i === lines - 1 && lines > 1 ? "65%" : width}
        />
      ))}
    </div>
  );
}

/** Card-shaped skeleton */
export function SkeletonCard({ height = 120 }: { height?: number }) {
  return <Skeleton className="skeleton--card" height={height} />;
}

/** Full results-page skeleton */
export function ResultsPageSkeleton() {
  return (
    <div className="skeleton-page" aria-label="Loading results…" aria-busy="true">
      {/* Header */}
      <div className="skeleton-row">
        <Skeleton className="skeleton--avatar" />
        <div style={{ flex: 1 }}>
          <Skeleton className="skeleton--title" width="40%" style={{ marginBottom: 6 }} />
          <Skeleton className="skeleton--text" width="60%" />
        </div>
        <Skeleton width={80} height={30} style={{ borderRadius: "var(--radius-full)" }} />
      </div>

      {/* Stats row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        {[1, 2, 3, 4].map((n) => (
          <SkeletonCard key={n} height={80} />
        ))}
      </div>

      {/* OWASP grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8 }}>
        {Array.from({ length: 10 }).map((_, i) => (
          <SkeletonCard key={i} height={64} />
        ))}
      </div>

      {/* Findings list */}
      {[1, 2, 3, 4, 5].map((n) => (
        <div key={n} className="skeleton-row" style={{ padding: "10px 0" }}>
          <Skeleton width={8} height={48} style={{ borderRadius: "var(--radius-xs)" }} />
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
            <Skeleton className="skeleton--text" width="50%" />
            <Skeleton className="skeleton--text" width="80%" />
          </div>
          <Skeleton className="skeleton--badge" />
        </div>
      ))}
    </div>
  );
}

/** Scan-page skeleton */
export function ScanPageSkeleton() {
  return (
    <div className="skeleton-page" aria-label="Initializing scan…" aria-busy="true">
      <Skeleton className="skeleton--title" width="30%" />
      <SkeletonCard height={8} />
      {[1, 2, 3].map((n) => (
        <div key={n} className="skeleton-row">
          <Skeleton width={20} height={20} style={{ borderRadius: "var(--radius-full)" }} />
          <SkeletonText width="60%" lines={2} />
        </div>
      ))}
    </div>
  );
}

export default Skeleton;
