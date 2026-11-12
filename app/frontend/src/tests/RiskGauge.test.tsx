/**
 * Sentryφ — RiskGauge Tests (W5)
 * src/tests/RiskGauge.test.tsx
 *
 * Tests:
 *   - Renders with correct ARIA label
 *   - Shows correct initial score (animated=false to skip RAF)
 *   - Applies correct risk level class (low / medium / high / critical)
 *   - Custom label prop rendered
 *   - Score clamped to 0-100
 *   - SVG elements present
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { RiskGauge } from "../components/common/RiskGauge";

describe("RiskGauge", () => {
  it("renders accessible label with score and level", () => {
    render(<RiskGauge score={72} animated={false} />);
    const gauge = screen.getByRole("img");
    expect(gauge).toBeInTheDocument();
    expect(gauge).toHaveAttribute(
      "aria-label",
      expect.stringContaining("72")
    );
    expect(gauge).toHaveAttribute(
      "aria-label",
      expect.stringContaining("HIGH")
    );
  });

  it("displays the score number", () => {
    render(<RiskGauge score={42} animated={false} />);
    // The score should appear in the SVG text element
    const container = screen.getByRole("img").querySelector("svg");
    expect(container?.textContent).toContain("42");
  });

  it("applies low risk class for score < 25", () => {
    const { container } = render(<RiskGauge score={10} animated={false} />);
    expect(container.firstChild).toHaveClass("risk-gauge--low");
  });

  it("applies medium risk class for score 25-49", () => {
    const { container } = render(<RiskGauge score={40} animated={false} />);
    expect(container.firstChild).toHaveClass("risk-gauge--medium");
  });

  it("applies high risk class for score 50-74", () => {
    const { container } = render(<RiskGauge score={60} animated={false} />);
    expect(container.firstChild).toHaveClass("risk-gauge--high");
  });

  it("applies critical risk class for score >= 75", () => {
    const { container } = render(<RiskGauge score={90} animated={false} />);
    expect(container.firstChild).toHaveClass("risk-gauge--critical");
  });

  it("renders custom label prop", () => {
    render(<RiskGauge score={50} animated={false} label="Threat Index" />);
    expect(screen.getByText("Threat Index")).toBeInTheDocument();
  });

  it("clamps score above 100 to 100", () => {
    const { container } = render(<RiskGauge score={150} animated={false} />);
    // Should be treated as 100 — critical class
    expect(container.firstChild).toHaveClass("risk-gauge--critical");
    expect(container.querySelector("svg")?.textContent).toContain("100");
  });

  it("clamps score below 0 to 0", () => {
    const { container } = render(<RiskGauge score={-5} animated={false} />);
    expect(container.firstChild).toHaveClass("risk-gauge--low");
    expect(container.querySelector("svg")?.textContent).toContain("0");
  });

  it("renders SVG with track and fill paths", () => {
    const { container } = render(<RiskGauge score={55} animated={false} />);
    const paths = container.querySelectorAll("path");
    // track + fill = 2 path elements
    expect(paths.length).toBeGreaterThanOrEqual(2);
  });

  it("sets aria-hidden on the inner SVG", () => {
    const { container } = render(<RiskGauge score={30} animated={false} />);
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("aria-hidden", "true");
  });

  it("renders with custom size", () => {
    const { container } = render(
      <RiskGauge score={50} animated={false} size={200} />
    );
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("width", "200");
    expect(svg).toHaveAttribute("height", "200");
  });
});
