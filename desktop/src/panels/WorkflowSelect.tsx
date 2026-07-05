import { Select } from "antd";
import type { WorkflowSummary } from "../ipc/types";
import "./WorkflowSelect.css";

export function WorkflowSelect({
  workflows,
  value,
  onChange,
  disabled,
}: {
  workflows: WorkflowSummary[];
  value: string | undefined;
  onChange: (name: string) => void;
  disabled?: boolean;
}) {
  return (
    <label className="wf-select">
      <span className="wf-select__label">Workflow</span>
      <Select
        aria-label="workflow"
        value={value}
        onChange={(val) => onChange(val as string)}
        disabled={disabled || workflows.length === 0}
        options={workflows.map((w) => ({ label: w.title, value: w.name }))}
        popupMatchSelectWidth={false}
        className="wf-select__control"
      />
    </label>
  );
}
