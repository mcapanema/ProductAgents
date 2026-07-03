import type { ComponentType } from "react";
import {
  SearchOutlined,
  BarChartOutlined,
  GlobalOutlined,
  DollarOutlined,
  ToolOutlined,
  MessageOutlined,
  CompassOutlined,
  AuditOutlined,
  SafetyOutlined,
  CheckCircleOutlined,
  HistoryOutlined,
  UserOutlined,
  BorderOutlined,
} from "@ant-design/icons";

export type NodeKind =
  | "analyst-customer"
  | "analyst-analytics"
  | "analyst-market"
  | "analyst-business"
  | "analyst-technical"
  | "debate"
  | "strategist"
  | "judge"
  | "risk"
  | "governance"
  | "memory"
  | "approval"
  | "terminal"
  | "spine";

export interface KindMeta {
  label: string;
  role: string; // short group name shown as an eyebrow on the node
  description: string; // one-line "what this agent does" (tooltip)
  colorToken: string; // design-token var NAME for the node accent
  icon: ComponentType;
}

const BY_ID: Record<string, NodeKind> = {
  customer_research: "analyst-customer",
  product_analytics: "analyst-analytics",
  market: "analyst-market",
  business: "analyst-business",
  technical: "analyst-technical",
  debate: "debate",
  strategist: "strategist",
  judge: "judge",
  risk: "risk",
  governance: "governance",
  recall: "memory",
  human_approval: "approval",
  __start__: "terminal",
  __end__: "terminal",
};

export function nodeKind(id: string): NodeKind {
  return BY_ID[id] ?? "spine";
}

export const KIND_META: Record<NodeKind, KindMeta> = {
  "analyst-customer": { label: "Customer Research", role: "Analyst", description: "Reads synced customer feedback and evidence for demand signals.", colorToken: "--ai-analyst-customer", icon: SearchOutlined },
  "analyst-analytics": { label: "Product Analytics", role: "Analyst", description: "Interprets usage metrics and behavioural data.", colorToken: "--ai-analyst-analytics", icon: BarChartOutlined },
  "analyst-market": { label: "Market", role: "Analyst", description: "Assesses market size, trend and competitive context.", colorToken: "--ai-analyst-market", icon: GlobalOutlined },
  "analyst-business": { label: "Business", role: "Analyst", description: "Weighs revenue, cost and strategic business impact.", colorToken: "--ai-analyst-business", icon: DollarOutlined },
  "analyst-technical": { label: "Technical", role: "Analyst", description: "Judges feasibility, effort and technical risk.", colorToken: "--ai-analyst-technical", icon: ToolOutlined },
  debate: { label: "Debate", role: "Dialectic", description: "Advocate vs Skeptic argue the initiative across rounds.", colorToken: "--accent", icon: MessageOutlined },
  strategist: { label: "Strategist", role: "Synthesis", description: "Synthesizes findings, debate and past lessons into a recommendation.", colorToken: "--accent", icon: CompassOutlined },
  judge: { label: "Judge", role: "Evaluation", description: "Scores the recommendation on evidence grounding and coherence.", colorToken: "--accent", icon: AuditOutlined },
  risk: { label: "Risk", role: "Evaluation", description: "Reviews the recommendation for downside and failure modes.", colorToken: "--accent", icon: SafetyOutlined },
  governance: { label: "Governance", role: "Advisory", description: "Applies advisory governance policy to the decision.", colorToken: "--accent", icon: CheckCircleOutlined },
  memory: { label: "Recall", role: "Memory", description: "Retrieves lessons from relevant past decisions.", colorToken: "--ai-thinking", icon: HistoryOutlined },
  approval: { label: "Human Approval", role: "Human-in-the-loop", description: "Pauses for a human Approve / Reject / Request-analysis verdict.", colorToken: "--ai-awaiting-human", icon: UserOutlined },
  terminal: { label: "Terminal", role: "Flow", description: "Pipeline entry / exit.", colorToken: "--text-tertiary", icon: BorderOutlined },
  spine: { label: "Step", role: "Pipeline", description: "A pipeline step.", colorToken: "--accent", icon: BorderOutlined },
};
