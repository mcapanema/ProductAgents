import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { WorkflowToolbar } from "./WorkflowToolbar";
import type { WorkflowSummary } from "../ipc/types";

const alpha: WorkflowSummary = { name: "alpha", title: "Alpha", description: "", is_default: true };
const beta: WorkflowSummary = { name: "beta", title: "Beta", description: "", is_default: false };

function noop() {}

describe("WorkflowToolbar", () => {
  it("marks the default workflow with a star and disables Delete/Rename for builtin", () => {
    render(
      <WorkflowToolbar
        workflows={[alpha, beta]}
        current={{ ...alpha, builtin: true }}
        dirty={false}
        onSelect={noop}
        onCreate={noop}
        onClone={noop}
        onRename={noop}
        onDelete={noop}
        onSetDefault={noop}
        onSave={noop}
      />,
    );
    expect(screen.getByText(/★/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /delete/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /rename/i })).toBeDisabled();
  });

  it("enables Delete/Rename for a non-builtin workflow", () => {
    render(
      <WorkflowToolbar
        workflows={[alpha, beta]}
        current={{ ...beta, builtin: false }}
        dirty={false}
        onSelect={noop}
        onCreate={noop}
        onClone={noop}
        onRename={noop}
        onDelete={noop}
        onSetDefault={noop}
        onSave={noop}
      />,
    );
    expect(screen.getByRole("button", { name: /delete/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: /rename/i })).toBeEnabled();
  });

  it("opens a modal on + New and calls onCreate(name, title)", async () => {
    const onCreate = vi.fn();
    render(
      <WorkflowToolbar
        workflows={[alpha, beta]}
        current={{ ...alpha, builtin: true }}
        dirty={false}
        onSelect={noop}
        onCreate={onCreate}
        onClone={noop}
        onRename={noop}
        onDelete={noop}
        onSetDefault={noop}
        onSave={noop}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /new/i }));
    fireEvent.change(await screen.findByPlaceholderText("name"), { target: { value: "gamma" } });
    fireEvent.change(screen.getByPlaceholderText("title"), { target: { value: "Gamma" } });
    fireEvent.click(screen.getByRole("button", { name: /create/i }));
    expect(onCreate).toHaveBeenCalledWith("gamma", "Gamma");
  });

  it("disables Save when not dirty and Set default when already default", () => {
    render(
      <WorkflowToolbar
        workflows={[alpha, beta]}
        current={{ ...alpha, builtin: true }}
        dirty={false}
        onSelect={noop}
        onCreate={noop}
        onClone={noop}
        onRename={noop}
        onDelete={noop}
        onSetDefault={noop}
        onSave={noop}
      />,
    );
    expect(screen.getByRole("button", { name: /^save$/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /set default/i })).toBeDisabled();
  });

  it("enables Save when dirty", () => {
    render(
      <WorkflowToolbar
        workflows={[alpha, beta]}
        current={{ ...alpha, builtin: true }}
        dirty
        onSelect={noop}
        onCreate={noop}
        onClone={noop}
        onRename={noop}
        onDelete={noop}
        onSetDefault={noop}
        onSave={noop}
      />,
    );
    expect(screen.getByRole("button", { name: /^save$/i })).toBeEnabled();
  });
});
