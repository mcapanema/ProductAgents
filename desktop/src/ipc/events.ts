export type StageStatus = "pending" | "running" | "done" | "failed";

export type StageKey =
  | "customer_research" | "product_analytics" | "market" | "business" | "technical"
  | "recall" | "debate" | "strategist" | "judge" | "risk" | "governance" | "final";

/** Nested-model payload shapes as they arrive over the wire (see events.py). */
export interface AnalystReportPayload {
  analyst: string;
  role: string;
  findings: string[];
  signals: string[];
  failed: boolean;
}
export interface RecommendationPayload {
  recommendation: string;
  confidence: number;
  rationale: string;
  expected_outcomes: string[];
  failed: boolean;
}
export interface JudgedPayload {
  passed: boolean;
  evidence_grounding_score: number;
  rationale_coherence_score: number;
  critique: string;
  attempt: number;
}
export interface RiskAssessedPayload {
  reviewer: string;
  role: string;
  level: string;
  rationale: string;
}

export type StageDetail =
  | { kind: "none" }
  | { kind: "analyst"; report: AnalystReportPayload | null }
  | { kind: "debate"; turns: { round: number; side: string; argument: string }[] }
  | { kind: "recall"; lessons: string[] }
  | { kind: "recommendation"; recommendation: RecommendationPayload | null }
  | { kind: "judge"; judged: JudgedPayload }
  | { kind: "risk"; rows: RiskAssessedPayload[] }
  | { kind: "governance"; verdict: string; rationale: string }
  | { kind: "final"; verdict: string; rationale: string; decidedBy: string };

export interface StageState {
  key: StageKey;
  label: string;
  status: StageStatus;
  detail: StageDetail;
}

export const emptyDetail = (): StageDetail => ({ kind: "none" });

export const STAGE_DEFS: readonly { key: StageKey; label: string }[] = [
  { key: "customer_research", label: "Customer Research" },
  { key: "product_analytics", label: "Product Analytics" },
  { key: "market", label: "Market" },
  { key: "business", label: "Business" },
  { key: "technical", label: "Technical" },
  { key: "recall", label: "Recall" },
  { key: "debate", label: "Debate" },
  { key: "strategist", label: "Recommendation" },
  { key: "judge", label: "Judge" },
  { key: "risk", label: "Risk" },
  { key: "governance", label: "Governance" },
  { key: "final", label: "Final Verdict" },
];

const STAGE_KEYS = new Set<string>(STAGE_DEFS.map((d) => d.key));

/** Node names from NodeProgress/AnalystCompleted/NodeFailed → a stage key. */
export function nodeToStage(node: string): StageKey | undefined {
  if (node === "human_approval") return "final";
  return STAGE_KEYS.has(node) ? (node as StageKey) : undefined;
}

/** Stages with no single terminal event; promoted to done once a later stage starts. */
export const NO_TERMINAL = new Set<StageKey>(["debate", "risk"]);
