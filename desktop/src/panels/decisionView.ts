import type { DecisionDetail } from "../ipc/types";

export function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export interface DecisionSections {
  evidence: { field: string; source: string; location: string }[];
  debate: { round: number; side: string; argument: string }[];
  risks: { reviewer: string; role: string; level: string; rationale: string }[];
  governance: { verdict: string; rationale: string; decided_by: string } | null;
}

/** Pull the persisted-but-previously-unrendered detail sections off a decision. */
export function decisionSections(detail: DecisionDetail): DecisionSections {
  const r = detail.record;
  return {
    evidence: r.evidence_sources ?? [],
    debate: r.debate ?? [],
    risks: r.risks ?? [],
    governance: r.governance ?? null,
  };
}

/** Flatten a decision's prediction vs. reality for the explorer detail view. */
export function predictionRows(detail: DecisionDetail): {
  predicted: string[];
  actual: string[];
  lessons: string[];
} {
  return {
    predicted: detail.record.recommendation.expected_outcomes,
    actual: detail.outcomes.flatMap((o) => o.actual_outcomes),
    lessons: detail.outcomes.flatMap((o) => o.lessons_learned),
  };
}
