import { useEffect, useState } from "react";
import { UpOutlined, DownOutlined } from "@ant-design/icons";
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

const COLLAPSE_STORAGE_KEY = "pa-legend-collapsed";

function readStoredCollapsed(): boolean {
  return localStorage.getItem(COLLAPSE_STORAGE_KEY) === "1";
}

export function WorkflowLegend() {
  const [collapsed, setCollapsed] = useState(readStoredCollapsed);

  useEffect(() => {
    localStorage.setItem(COLLAPSE_STORAGE_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  return (
    <div className="wf-legend" aria-label="Graph legend" data-collapsed={collapsed}>
      <div className="wf-legend__head">
        <span className="wf-legend__title">
          {collapsed ? "Legend" : "Reading the graph — flows top to bottom"}
        </span>
        <button
          type="button"
          className="wf-legend__toggle"
          aria-expanded={!collapsed}
          aria-label={collapsed ? "Show graph legend" : "Hide graph legend"}
          onClick={() => setCollapsed((c) => !c)}
        >
          {collapsed ? <UpOutlined /> : <DownOutlined />}
        </button>
      </div>
      {!collapsed && (
        <>
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
        </>
      )}
    </div>
  );
}
