import type { CSSProperties } from "react";
import "./ConfidenceGauge.css";

// Tier thresholds match the styleguide phase4b ConfidenceBar: <40 low (red),
// <70 medium (amber), else high (teal). Fill resolves through the theme-aware
// --ai-confidence-* scale, so it flips correctly light/dark.
function tierOf(pct: number): "low" | "medium" | "high" {
  return pct < 40 ? "low" : pct < 70 ? "medium" : "high";
}

/**
 * The confidence gauge — the design system's signature motif. Accepts the raw
 * canonical `confidence` (0–1, as carried by Recommendation / judge scores) and
 * renders it as a measured quantity: a tier-colored bar plus the numeric reading.
 */
export function ConfidenceGauge({
  value,
  label = "Confidence",
  showValue = true,
}: {
  value: number; // 0–1
  label?: string;
  showValue?: boolean;
}) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <span
      className="confidence-gauge"
      role="img"
      aria-label={`${label}: ${pct}%`}
      style={{ "--gauge-fill": `var(--ai-confidence-${tierOf(pct)})`, "--gauge-pct": `${pct}%` } as CSSProperties}
    >
      <span className="confidence-gauge__track" aria-hidden>
        <span className="confidence-gauge__fill" />
      </span>
      {showValue && <span className="confidence-gauge__val" aria-hidden>{pct}%</span>}
    </span>
  );
}
