import { tokenVar } from "../ui/tokens";
import { statusStyle } from "./nodeStatus";
import type { NodeStatus } from "../ipc/types";
import "./WorkflowLegend.css";

const ANALYST_TOKENS = [
  "--ai-analyst-customer",
  "--ai-analyst-analytics",
  "--ai-analyst-market",
  "--ai-analyst-business",
  "--ai-analyst-technical",
] as const;

const STATUS_SAMPLE: NodeStatus[] = ["running", "done", "degraded", "failed", "awaiting-human"];

export function WorkflowLegend() {
  return (
    <div className="wf-legend" aria-label="Graph legend">
      <span className="wf-legend__title">Reading the graph — flows top to bottom</span>
      <span className="wf-legend__item">
        <span style={{ display: "inline-flex", gap: 2 }} aria-hidden>
          {ANALYST_TOKENS.map((t) => (
            <span key={t} className="wf-legend__swatch" style={{ background: tokenVar(t) }} />
          ))}
        </span>
        Five analysts, run in parallel
      </span>
      <span className="wf-legend__item">
        <span className="wf-legend__swatch" style={{ background: tokenVar("--accent") }} aria-hidden />
        A sequential reasoning step
      </span>
      <span className="wf-legend__item">
        <span className="wf-legend__edge" aria-hidden /> Conditional path (e.g. judge → strategist retry)
      </span>
      <span className="wf-legend__item">
        <span className="wf-legend__ring" aria-hidden /> Ringed node: click to edit its prompts
      </span>
      <span className="wf-legend__item">
        <span style={{ display: "inline-flex", gap: 2 }} aria-hidden>
          {STATUS_SAMPLE.map((s) => (
            <span key={s} className="wf-legend__swatch" style={{ background: statusStyle(s).border }} />
          ))}
        </span>
        Live-run status: running, done, degraded, failed, awaiting input
      </span>
    </div>
  );
}
