import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("renders the title and description", () => {
    render(<EmptyState title="No sessions yet" description="Runs will appear here." />);
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("No sessions yet");
    expect(status).toHaveTextContent("Runs will appear here.");
  });

  it("renders a default decorative icon", () => {
    render(<EmptyState title="Empty" />);
    const svg = screen.getByRole("status").querySelector("svg");
    expect(svg).not.toBeNull();
    expect(svg).toHaveAttribute("aria-hidden", "true");
  });

  it("renders a provided action", () => {
    render(<EmptyState title="Empty" action={<button>Go</button>} />);
    expect(screen.getByRole("button", { name: "Go" })).toBeInTheDocument();
  });

  it("omits description and action when not given", () => {
    render(<EmptyState title="Only title" />);
    const status = screen.getByRole("status");
    expect(status.querySelector(".empty-state__desc")).toBeNull();
    expect(status.querySelector(".empty-state__action")).toBeNull();
  });
});
