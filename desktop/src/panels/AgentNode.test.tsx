import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ReactFlowProvider } from "@xyflow/react";
import AgentNode from "./AgentNode";
import type { AgentNodeData } from "./AgentNode";

function renderNode(data: Partial<AgentNodeData> = {}) {
  const full: AgentNodeData = {
    id: "customer_research",
    kind: "analyst-customer",
    status: "idle",
    editable: true,
    selected: false,
    step: 1,
    ...data,
  };
  render(
    <ReactFlowProvider>
      {/* AgentNode reads only `data`; the other NodeProps are unused in the body. */}
      <AgentNode data={full} id={full.id} selected={full.selected} type="agent"
        dragging={false} zIndex={0} isConnectable={false}
        draggable={false} selectable={false} deletable={false}
        positionAbsoluteX={0} positionAbsoluteY={0} />
    </ReactFlowProvider>,
  );
  return full;
}

describe("AgentNode", () => {
  it("shows the kind label and role eyebrow", () => {
    renderNode();
    expect(screen.getByText("Customer Research")).toBeInTheDocument();
    expect(screen.getByText("Analyst")).toBeInTheDocument();
  });

  it("exposes an accessible name that includes the label and status", () => {
    renderNode({ status: "running" });
    const el = screen.getByRole("button");
    expect(el.getAttribute("aria-label")).toMatch(/Customer Research/);
    expect(el.getAttribute("aria-label")).toMatch(/running/i);
  });

  it("marks editable nodes as clickable and non-editable ones as not", () => {
    renderNode({ editable: true });
    expect(screen.getByRole("button")).toHaveAttribute("data-editable", "true");
  });

  it("renders a non-editable node without the edit affordance", () => {
    renderNode({ id: "recall", kind: "memory", editable: false });
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    const el = document.querySelector(".agent-node") as HTMLElement;
    expect(el).toHaveAttribute("data-editable", "false");
    expect(el).not.toHaveAttribute("role");
  });

  it("shows its pipeline step number and includes it in the accessible name", () => {
    renderNode({ step: 3 });
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByRole("button").getAttribute("aria-label")).toMatch(/^Step 3,/);
  });

  it("hides the step number and role eyebrow for terminal nodes", () => {
    renderNode({ id: "__start__", kind: "terminal", editable: false, step: 0 });
    expect(document.querySelector(".agent-node__step")).not.toBeInTheDocument();
    const el = document.querySelector(".agent-node") as HTMLElement;
    expect(el.getAttribute("aria-label")).not.toMatch(/^Step/);
  });

  it("labels the two terminal nodes distinctly by id, not a shared 'Terminal'", () => {
    renderNode({ id: "__start__", kind: "terminal", editable: false, step: 0 });
    expect(screen.getByText("Start")).toBeInTheDocument();
    expect(screen.queryByText("Terminal")).not.toBeInTheDocument();
  });

  it("labels the end terminal node distinctly too", () => {
    renderNode({ id: "__end__", kind: "terminal", editable: false, step: 0 });
    expect(screen.getByText("End")).toBeInTheDocument();
    expect(screen.queryByText("Terminal")).not.toBeInTheDocument();
  });
});
