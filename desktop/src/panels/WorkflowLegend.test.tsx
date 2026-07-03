import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { WorkflowLegend } from "./WorkflowLegend";

describe("WorkflowLegend", () => {
  it("explains the graph's visual language", () => {
    render(<WorkflowLegend />);
    expect(screen.getByText(/analyst/i)).toBeInTheDocument();
    expect(screen.getByText(/conditional/i)).toBeInTheDocument();
    expect(screen.getByText(/click to edit prompts/i)).toBeInTheDocument();
  });
});
