import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { WorkflowSelect } from "./WorkflowSelect";
import type { WorkflowSummary } from "../ipc/types";

const wfs: WorkflowSummary[] = [
  { name: "evaluate_initiative", title: "Evaluate Initiative", description: "a" },
  { name: "roadmap", title: "Roadmap Prioritization", description: "b" },
];

describe("WorkflowSelect", () => {
  it("shows the selected workflow's title", () => {
    render(<WorkflowSelect workflows={wfs} value="evaluate_initiative" onChange={() => {}} />);
    expect(screen.getByTitle("Evaluate Initiative")).toBeInTheDocument();
  });

  it("calls onChange with the chosen workflow name", async () => {
    const onChange = vi.fn();
    render(<WorkflowSelect workflows={wfs} value="evaluate_initiative" onChange={onChange} />);
    fireEvent.mouseDown(screen.getByRole("combobox", { name: "workflow" }));
    fireEvent.click(await screen.findByTitle("Roadmap Prioritization"));
    expect(onChange).toHaveBeenCalledWith("roadmap");
  });

  it("is disabled when there are no workflows", () => {
    render(<WorkflowSelect workflows={[]} value={undefined} onChange={() => {}} />);
    expect(screen.getByRole("combobox", { name: "workflow" })).toBeDisabled();
  });
});
