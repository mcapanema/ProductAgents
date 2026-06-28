import type { DecisionDetail } from "../ipc/types";

export function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`;
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
