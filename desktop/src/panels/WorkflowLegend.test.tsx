import { beforeEach, describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { WorkflowLegend } from "./WorkflowLegend";

beforeEach(() => {
  localStorage.clear();
});

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

  it("hides the legend items and shows a compact label when collapsed", () => {
    render(<WorkflowLegend />);
    fireEvent.click(screen.getByRole("button", { name: "Hide graph legend" }));
    expect(screen.getByText("Legend")).toBeInTheDocument();
    expect(screen.queryByText(/five analysts.*parallel/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Show graph legend" })).toBeInTheDocument();
  });

  it("persists the collapsed state across remounts via localStorage", () => {
    const { unmount } = render(<WorkflowLegend />);
    fireEvent.click(screen.getByRole("button", { name: "Hide graph legend" }));
    unmount();
    render(<WorkflowLegend />);
    expect(screen.getByRole("button", { name: "Show graph legend" })).toBeInTheDocument();
  });
});
