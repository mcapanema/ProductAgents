import { beforeEach, describe, it, expect, vi } from "vitest";
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
  "Reflection",
  "Settings",
];

function renderSidebar({ view = "run", running = false }: { view?: string; running?: boolean } = {}) {
  const onNavigate = vi.fn();
  const utils = render(
    <Sidebar view={view as never} onNavigate={onNavigate} running={running} />,
  );
  return { nav: screen.getByRole("navigation"), onNavigate, ...utils };
}

beforeEach(() => {
  localStorage.clear();
});

describe("Sidebar", () => {
  it("renders all nine nav items with an icon each", () => {
    const { nav } = renderSidebar();
    for (const label of LABELS) {
      const item = within(nav).getByRole("button", { name: label });
      expect(item.querySelector("svg.sidebar-icon")).not.toBeNull();
    }
  });

  it("marks the active view with aria-current and calls onNavigate on click", () => {
    const { nav, onNavigate } = renderSidebar({ view: "decisions" });
    expect(within(nav).getByRole("button", { name: "Decisions" })).toHaveAttribute("aria-current", "page");
    fireEvent.click(within(nav).getByRole("button", { name: "Settings" }));
    expect(onNavigate).toHaveBeenCalledWith("settings");
  });

  it("does not render a density control", () => {
    renderSidebar();
    expect(screen.queryByLabelText("Density")).not.toBeInTheDocument();
  });

  it("collapses to an icon-only rail on toggle, hiding labels", () => {
    const { nav } = renderSidebar();
    const settingsBefore = within(nav).getByRole("button", { name: "Settings" });
    expect(settingsBefore.querySelector(".sidebar-label")).not.toBeNull();
    fireEvent.click(within(nav).getByRole("button", { name: "Collapse sidebar" }));
    const settingsItem = within(nav).getByRole("button", { name: "Settings" });
    expect(settingsItem.querySelector(".sidebar-label")).toBeNull();
    expect(within(nav).getByRole("button", { name: "Expand sidebar" })).toBeInTheDocument();
  });

  it("persists the collapsed state across remounts via localStorage", () => {
    const first = renderSidebar();
    fireEvent.click(within(first.nav).getByRole("button", { name: "Collapse sidebar" }));
    first.unmount();
    const second = renderSidebar();
    expect(within(second.nav).getByRole("button", { name: "Expand sidebar" })).toBeInTheDocument();
  });

  it("shows an amber live-run dot on the Run item when running is true", () => {
    const { nav } = renderSidebar({ running: true });
    expect(within(nav).getByLabelText("run in progress")).toBeInTheDocument();
  });

  it("does not show the live-run dot when running is false", () => {
    const { nav } = renderSidebar({ running: false });
    expect(within(nav).queryByLabelText("run in progress")).toBeNull();
  });

  it("keeps the Run button's accessible name as its visible label while running", () => {
    const { nav } = renderSidebar({ running: true });
    expect(within(nav).getByRole("button", { name: "Run" })).toBeInTheDocument();
  });

  it("renders Settings as the last nav item", () => {
    const { nav } = renderSidebar();
    const buttons = within(nav)
      .getAllByRole("button")
      .filter((b) => b.classList.contains("sidebar-item"));
    const last = buttons[buttons.length - 1];
    expect(last).toHaveTextContent("Settings");
  });
});
