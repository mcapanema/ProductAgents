import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { App } from "antd";
import { WorkflowToolbar, type CurrentWorkflow } from "./WorkflowToolbar";
import type { WorkflowSummary } from "../ipc/types";

const alpha: WorkflowSummary = { name: "alpha", title: "Alpha", description: "", is_default: true };
const beta: WorkflowSummary = { name: "beta", title: "Beta", description: "", is_default: false };

async function noop() {}

function renderToolbar(overrides: Partial<React.ComponentProps<typeof WorkflowToolbar>> = {}) {
  const props: React.ComponentProps<typeof WorkflowToolbar> = {
    workflows: [alpha, beta],
    current: { ...alpha, builtin: true } as CurrentWorkflow,
    dirty: false,
    onSelect: noop,
    onCreate: noop,
    onClone: noop,
    onRename: noop,
    onDelete: noop,
    onSetDefault: noop,
    onSave: noop,
    ...overrides,
  };
  render(
    <App>
      <WorkflowToolbar {...props} />
    </App>,
  );
}

describe("WorkflowToolbar", () => {
  it("marks the default workflow with a star and disables Delete/Rename for builtin", () => {
    renderToolbar();
    expect(screen.getByText(/★/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /delete/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /rename/i })).toBeDisabled();
  });

  it("enables Delete/Rename for a non-builtin workflow", () => {
    renderToolbar({ current: { ...beta, builtin: false } });
    expect(screen.getByRole("button", { name: /delete/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: /rename/i })).toBeEnabled();
  });

  it("opens a modal on + New and calls onCreate(name, title, description)", async () => {
    const onCreate = vi.fn();
    renderToolbar({ onCreate });
    fireEvent.click(screen.getByRole("button", { name: /new/i }));
    fireEvent.change(await screen.findByPlaceholderText("name"), { target: { value: "gamma" } });
    fireEvent.change(screen.getByPlaceholderText("title"), { target: { value: "Gamma" } });
    fireEvent.change(screen.getByPlaceholderText(/description/i), { target: { value: "A new pipeline." } });
    fireEvent.click(screen.getByRole("button", { name: /create/i }));
    expect(onCreate).toHaveBeenCalledWith("gamma", "Gamma", "A new pipeline.");
  });

  it("keeps the Create modal open and shows the error when onCreate rejects", async () => {
    const onCreate = vi.fn().mockRejectedValue(new Error("workflow 'gamma' already exists"));
    renderToolbar({ onCreate });
    fireEvent.click(screen.getByRole("button", { name: /new/i }));
    fireEvent.change(await screen.findByPlaceholderText("name"), { target: { value: "gamma" } });
    fireEvent.click(screen.getByRole("button", { name: /create/i }));

    expect(await screen.findByText(/already exists/i)).toBeInTheDocument();
    // Modal stayed open — the name field is still there, not silently closed.
    expect(screen.getByPlaceholderText("name")).toBeInTheDocument();
  });

  it("prefills name and title on Rename and calls onRename(newName, title)", async () => {
    const onRename = vi.fn();
    renderToolbar({ current: { ...beta, builtin: false }, onRename });
    fireEvent.click(screen.getByRole("button", { name: /rename/i }));
    const dialog = await screen.findByRole("dialog");
    const nameInput = within(dialog).getByPlaceholderText("name");
    const titleInput = within(dialog).getByPlaceholderText("title");
    expect(nameInput).toHaveValue(beta.name);
    expect(titleInput).toHaveValue(beta.title);
    fireEvent.change(titleInput, { target: { value: "Better Beta" } });
    fireEvent.click(within(dialog).getByRole("button", { name: /^rename$/i }));
    expect(onRename).toHaveBeenCalledWith(beta.name, "Better Beta");
  });

  it("does not show a description field on Rename or Clone", async () => {
    renderToolbar({ current: { ...beta, builtin: false } });
    fireEvent.click(screen.getByRole("button", { name: /rename/i }));
    expect(await screen.findByPlaceholderText("name")).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/description/i)).not.toBeInTheDocument();
  });

  it("shows the confirm dialog on Delete and calls onDelete when confirmed", async () => {
    const onDelete = vi.fn();
    renderToolbar({ current: { ...beta, builtin: false }, onDelete });
    fireEvent.click(screen.getByRole("button", { name: /^delete$/i }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getAllByText(/delete "beta"\?/i).length).toBeGreaterThan(0);
    fireEvent.click(within(dialog).getByRole("button", { name: /^delete$/i }));
    expect(onDelete).toHaveBeenCalled();
  });

  it("disables Save when not dirty and Set default when already default", () => {
    renderToolbar();
    expect(screen.getByRole("button", { name: /^save$/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /set default/i })).toBeDisabled();
  });

  it("enables Save when dirty", () => {
    renderToolbar({ dirty: true });
    expect(screen.getByRole("button", { name: /^save$/i })).toBeEnabled();
  });
});
