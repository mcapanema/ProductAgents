import type { IpcEvent } from "../ipc/types";
import type { StageKey, StageState, StageStatus } from "../ipc/events";
import { STAGE_DEFS, nodeToStage, NO_TERMINAL, emptyDetail } from "../ipc/events";
import type {
  AnalystReportPayload,
  RecommendationPayload,
  JudgedPayload,
  RiskAssessedPayload,
} from "../ipc/events";

// ponytail: minimal Map-based state machine; incremental only if a run ever emits thousands of events.
export function deriveStages(events: IpcEvent[]): StageState[] {
  const byKey = new Map<StageKey, StageState>(
    STAGE_DEFS.map((d) => [d.key, { key: d.key, label: d.label, status: "pending", detail: emptyDetail() }]),
  );
  const set = (key: StageKey | undefined, status: StageStatus): void => {
    if (!key) return;
    const st = byKey.get(key);
    if (!st) return;
    // never downgrade a settled stage back to running
    if (status === "running" && (st.status === "done" || st.status === "failed")) return;
    st.status = status;
  };

  for (const e of events) {
    const p = e.payload;
    switch (e.type) {
      case "NodeProgress":
        set(nodeToStage(String(p.node ?? "")), "running");
        break;
      case "AnalystCompleted": {
        const key = nodeToStage(String(p.node ?? ""));
        const report = (p.report as AnalystReportPayload | undefined) ?? null;
        const st = key ? byKey.get(key) : undefined;
        if (st) st.detail = { kind: "analyst", report };
        set(key, report?.failed ? "failed" : "done");
        break;
      }
      case "DebateTurnEmitted": {
        const st = byKey.get("debate")!;
        const turns = st.detail.kind === "debate" ? st.detail.turns : [];
        st.detail = {
          kind: "debate",
          turns: [...turns, { round: Number(p.round ?? 0), side: String(p.side ?? ""), argument: String(p.argument ?? "") }],
        };
        set("debate", "running");
        break;
      }
      case "LessonsRecalled": {
        byKey.get("recall")!.detail = { kind: "recall", lessons: (p.lessons as string[] | undefined) ?? [] };
        set("recall", "done");
        break;
      }
      case "Recommended": {
        byKey.get("strategist")!.detail = { kind: "recommendation", recommendation: (p.recommendation as RecommendationPayload | undefined) ?? null };
        set("strategist", "done");
        break;
      }
      case "Judged": {
        byKey.get("judge")!.detail = { kind: "judge", judged: p as unknown as JudgedPayload };
        set("judge", "done");
        break;
      }
      case "RiskAssessed": {
        const st = byKey.get("risk")!;
        const rows = st.detail.kind === "risk" ? st.detail.rows : [];
        st.detail = { kind: "risk", rows: [...rows, p as unknown as RiskAssessedPayload] };
        set("risk", "running");
        break;
      }
      case "GovernanceAdvised": {
        byKey.get("governance")!.detail = { kind: "governance", verdict: String(p.verdict ?? ""), rationale: String(p.rationale ?? "") };
        set("governance", "done");
        break;
      }
      case "ApprovalRequested":
        set("final", "running");
        break;
      case "FinalVerdict": {
        byKey.get("final")!.detail = { kind: "final", verdict: String(p.verdict ?? ""), rationale: String(p.rationale ?? ""), decidedBy: String(p.decided_by ?? "") };
        set("final", "done");
        break;
      }
      case "SessionFinished":
        set("final", "done");
        break;
      case "NodeFailed":
      case "SessionFailed":
        set(nodeToStage(String(p.node ?? "")), "failed");
        break;
      // SessionStarted and any unknown type: no-op
    }
  }

  // Promote terminal-less stages (debate, risk) to done once a later stage started.
  const order = STAGE_DEFS.map((d) => d.key);
  const anyLaterStarted = (i: number) => order.slice(i + 1).some((k) => byKey.get(k)!.status !== "pending");
  order.forEach((key, i) => {
    const st = byKey.get(key)!;
    if (st.status === "running" && NO_TERMINAL.has(key) && anyLaterStarted(i)) st.status = "done";
  });

  return order.map((k) => byKey.get(k)!);
}
