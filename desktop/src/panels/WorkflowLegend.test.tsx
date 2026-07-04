import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { WorkflowLegend } from "./WorkflowLegend";

describe("WorkflowLegend", () => {
  it("explains how to read the graph", () => {
    render(<WorkflowLegend />);
    expect(screen.getByText(/reading the graph/i)).toBeInTheDocument();
    expect(screen.getByText(/top to bottom/i)).toBeInTheDocument();
  });

  it("labels the analyst, spine, conditional-path, editable, and status keys", () => {
    render(<WorkflowLegend />);
    expect(screen.getByText(/five analysts.*parallel/i)).toBeInTheDocument();
    expect(screen.getByText(/sequential reasoning step/i)).toBeInTheDocument();
    expect(screen.getByText(/conditional path/i)).toBeInTheDocument();
    expect(screen.getByText(/click to edit/i)).toBeInTheDocument();
    expect(screen.getByText(/live-run status/i)).toBeInTheDocument();
  });
});
