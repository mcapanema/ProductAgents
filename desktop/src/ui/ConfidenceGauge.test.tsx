import { render } from "@testing-library/react";
import { ConfidenceGauge } from "./ConfidenceGauge";

function gauge(value: number, props = {}) {
  const { container } = render(<ConfidenceGauge value={value} {...props} />);
  const el = container.querySelector(".confidence-gauge") as HTMLElement;
  return {
    label: el.getAttribute("aria-label"),
    fill: el.style.getPropertyValue("--gauge-fill"),
    pct: el.style.getPropertyValue("--gauge-pct"),
    text: container.querySelector(".confidence-gauge__val")?.textContent,
  };
}

it("renders the numeric reading and percent width from a 0–1 value", () => {
  const g = gauge(0.72);
  expect(g.text).toBe("72%");
  expect(g.pct).toBe("72%");
  expect(g.label).toBe("Confidence: 72%");
});

it("maps value to the tier fill: <40 low, <70 medium, else high", () => {
  expect(gauge(0.3).fill).toBe("var(--ai-confidence-low)");
  expect(gauge(0.5).fill).toBe("var(--ai-confidence-medium)");
  expect(gauge(0.9).fill).toBe("var(--ai-confidence-high)");
});

it("clamps out-of-range values to 0–100", () => {
  expect(gauge(1.5).text).toBe("100%");
  expect(gauge(-0.2).text).toBe("0%");
});

it("supports a custom aria label and hiding the value", () => {
  const g = gauge(0.8, { label: "Grounding", showValue: false });
  expect(g.label).toBe("Grounding: 80%");
  expect(g.text).toBeUndefined();
});
