/**
 * Sentryφ — Skeleton Component Tests (W5)
 * src/tests/Skeleton.test.tsx
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  Skeleton,
  SkeletonText,
  SkeletonCard,
  ResultsPageSkeleton,
  ScanPageSkeleton,
} from "../components/common/Skeleton";

describe("Skeleton", () => {
  it("renders with skeleton class", () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toHaveClass("skeleton");
  });

  it("applies additional className", () => {
    const { container } = render(<Skeleton className="skeleton--text" />);
    expect(container.firstChild).toHaveClass("skeleton--text");
  });

  it("applies width and height styles", () => {
    const { container } = render(<Skeleton width={200} height={40} />);
    const el = container.firstChild as HTMLElement;
    expect(el.style.width).toBe("200px");
    expect(el.style.height).toBe("40px");
  });

  it("is aria-hidden", () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toHaveAttribute("aria-hidden", "true");
  });
});

describe("SkeletonText", () => {
  it("renders correct number of lines", () => {
    const { container } = render(<SkeletonText lines={4} />);
    const lines = container.querySelectorAll(".skeleton--text");
    expect(lines.length).toBe(4);
  });

  it("renders single line by default", () => {
    const { container } = render(<SkeletonText />);
    const lines = container.querySelectorAll(".skeleton--text");
    expect(lines.length).toBe(1);
  });
});

describe("SkeletonCard", () => {
  it("renders with skeleton--card class", () => {
    const { container } = render(<SkeletonCard />);
    expect(container.firstChild).toHaveClass("skeleton--card");
  });

  it("accepts custom height", () => {
    const { container } = render(<SkeletonCard height={80} />);
    const el = container.firstChild as HTMLElement;
    expect(el.style.height).toBe("80px");
  });
});

describe("ResultsPageSkeleton", () => {
  it("renders with aria-busy=true and label", () => {
    render(<ResultsPageSkeleton />);
    const el = screen.getByLabelText("Loading results…");
    expect(el).toBeInTheDocument();
    expect(el).toHaveAttribute("aria-busy", "true");
  });

  it("renders skeleton-page class", () => {
    const { container } = render(<ResultsPageSkeleton />);
    expect(container.firstChild).toHaveClass("skeleton-page");
  });
});

describe("ScanPageSkeleton", () => {
  it("renders with aria-busy=true", () => {
    render(<ScanPageSkeleton />);
    const el = screen.getByLabelText("Initializing scan…");
    expect(el).toBeInTheDocument();
    expect(el).toHaveAttribute("aria-busy", "true");
  });
});
