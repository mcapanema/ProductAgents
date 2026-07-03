import { Handle, Position, type NodeProps } from "@xyflow/react";
import { KIND_META, type NodeKind } from "./workflowNodeKinds";
import { statusStyle } from "./nodeStatus";
import { tokenVar } from "../ui/tokens";
import type { NodeStatus } from "../ipc/types";
import "./AgentNode.css";

export interface AgentNodeData {
  id: string;
  kind: NodeKind;
  status: NodeStatus;
  editable: boolean;
  selected: boolean;
  [key: string]: unknown; // React Flow node data is an index type
}

export default function AgentNode({ data }: NodeProps) {
  const d = data as AgentNodeData;
  const meta = KIND_META[d.kind];
  const st = statusStyle(d.status);
  const Icon = meta.icon;
  const isTerminal = d.kind === "terminal";
  const label = meta.label;

  const style = {
    "--node-accent": tokenVar(meta.colorToken as `--${string}`),
    "--node-status-border": st.border,
    "--node-status-text": d.status === "idle" ? undefined : st.text,
  } as React.CSSProperties;

  const ariaStatus = d.status === "idle" ? "" : `, ${d.status.replace("-", " ")}`;

  return (
    <div
      className={`agent-node${isTerminal ? " agent-node--terminal" : ""}`}
      style={style}
      data-editable={d.editable ? "true" : "false"}
      data-selected={d.selected ? "true" : "false"}
      data-status={d.status}
      role={d.editable ? "button" : undefined}
      tabIndex={0}
      aria-label={`${label}${d.editable ? ", edit prompts" : ""}${ariaStatus}`}
    >
      <Handle type="target" position={Position.Top} isConnectable={false} />
      {!isTerminal && <span className="agent-node__rail" aria-hidden />}
      <span className="agent-node__icon" aria-hidden><Icon /></span>
      <span className="agent-node__body">
        {!isTerminal && <div className="agent-node__role">{meta.role}</div>}
        <div className="agent-node__label">{label}</div>
      </span>
      <Handle type="source" position={Position.Bottom} isConnectable={false} />
    </div>
  );
}
