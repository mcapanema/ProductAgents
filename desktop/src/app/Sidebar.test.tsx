import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { Sidebar } from "./Sidebar";

const LABELS = [
  "Run",
  "Workflows",
  "Sessions",
  "Decisions",
  "Memory",
  "Connectors",
  "Prompts",
  "Settings",
  "Reflection",
];

function renderSidebar(view = "run") {
  const onNavigate = vi.fn();
  render(
    <Sidebar
      view={view as never}
      onNavigate={onNavigate}
      theme="light"
      onThemeChange={vi.fn()}
      density="comfortable"
      onDensityChange={vi.fn()}
    />,
  );
  return { nav: screen.getByRole("navigation"), onNavigate };
}

describe("Sidebar", () => {
  it("renders all nine nav items with an icon each", () => {
    const { nav } = renderSidebar();
    for (const label of LABELS) {
      const item = within(nav).getByRole("button", { name: label });
      expect(item.querySelector("svg.sidebar-icon")).not.toBeNull();
    }
  });

  it("marks the active view with aria-current and calls onNavigate on click", () => {
    const { nav, onNavigate } = renderSidebar("decisions");
    expect(within(nav).getByRole("button", { name: "Decisions" })).toHaveAttribute("aria-current", "page");
    fireEvent.click(within(nav).getByRole("button", { name: "Settings" }));
    expect(onNavigate).toHaveBeenCalledWith("settings");
  });
});
