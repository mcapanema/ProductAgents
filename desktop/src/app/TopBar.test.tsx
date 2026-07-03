import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import type { IpcClient } from "../ipc/client";
import { IpcProvider } from "./IpcProvider";
import { TopBar } from "./TopBar";

vi.mock("../ipc/transport", () => ({
  isTauri: () => false,
}));

const reloadSpy = vi.fn();
beforeAll(() => {
  Object.defineProperty(window, "location", {
    value: { ...window.location, reload: reloadSpy },
    writable: true,
  });
});

function fakeIpc(overrides: Partial<Record<keyof IpcClient, unknown>> = {}) {
  return {
    workspacesList: vi.fn().mockResolvedValue([
      { name: "default", active: true },
      { name: "acme", active: false },
    ]),
    workspacesCreate: vi
      .fn()
      .mockResolvedValue({ name: "beta", active: false }),
    workspacesUse: vi
      .fn()
      .mockResolvedValue({ name: "acme", active: true }),
    decisionsList: vi.fn().mockResolvedValue([
      { id: "d1", title: "Dark mode", recommendation: "go", confidence: 0.8, created_at: "t" },
    ]),
    sessionsList: vi.fn().mockResolvedValue([]),
    workflowsList: vi.fn().mockResolvedValue([]),
    ...overrides,
  } as unknown as IpcClient;
}

function renderBar(ipc = fakeIpc(), props: Partial<Parameters<typeof TopBar>[0]> = {}) {
  return render(
    <IpcProvider client={ipc}>
      <TopBar view="run" onNavigate={vi.fn()} running={false} {...props} />
    </IpcProvider>,
  );
}

describe("TopBar", () => {
  it("shows the active workspace and the current view crumb", async () => {
    renderBar();
    // antd's Select renders the selected label as text too, colliding with the
    // breadcrumb's "default" text node — `title` on the selector is unambiguous.
    await waitFor(() => expect(screen.getByTitle("default")).toBeInTheDocument());
    expect(screen.getByRole("navigation", { name: "Breadcrumb" })).toBeInTheDocument();
    expect(screen.getByText("Run")).toBeInTheDocument();
  });

  it("switches workspace via the selector and reloads", async () => {
    const ipc = fakeIpc();
    renderBar(ipc);
    await waitFor(() => expect(screen.getByTitle("default")).toBeInTheDocument());
    fireEvent.mouseDown(screen.getByRole("combobox", { name: "Workspace" }));
    fireEvent.click(await screen.findByTitle("acme"));
    await waitFor(() => expect(ipc.workspacesUse).toHaveBeenCalledWith("acme"));
    await waitFor(() => expect(reloadSpy).toHaveBeenCalled());
  });

  it("creates a workspace through the modal, then switches to it and reloads", async () => {
    const ipc = fakeIpc();
    renderBar(ipc);
    await waitFor(() => expect(screen.getByTitle("default")).toBeInTheDocument());
    fireEvent.mouseDown(screen.getByRole("combobox", { name: "Workspace" }));
    fireEvent.click(await screen.findByText("＋ New workspace…"));
    const input = await screen.findByPlaceholderText("workspace name");
    fireEvent.change(input, { target: { value: "beta" } });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => expect(ipc.workspacesCreate).toHaveBeenCalledWith("beta"));
    await waitFor(() => expect(ipc.workspacesUse).toHaveBeenCalledWith("beta"));
    await waitFor(() => expect(reloadSpy).toHaveBeenCalled());
  });

  it("rejects an invalid workspace name without calling the backend", async () => {
    const ipc = fakeIpc();
    renderBar(ipc);
    await waitFor(() => expect(screen.getByTitle("default")).toBeInTheDocument());
    fireEvent.mouseDown(screen.getByRole("combobox", { name: "Workspace" }));
    fireEvent.click(await screen.findByText("＋ New workspace…"));
    const input = await screen.findByPlaceholderText("workspace name");
    fireEvent.change(input, { target: { value: "bad name" } });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));
    expect(await screen.findByText(/invalid workspace name/i)).toBeInTheDocument();
    expect(ipc.workspacesCreate).not.toHaveBeenCalled();
  });

  it("search navigates to the matched entry's panel", async () => {
    const onNavigate = vi.fn();
    const ipc = fakeIpc();
    render(
      <IpcProvider client={ipc}>
        <TopBar view="run" onNavigate={onNavigate} running={false} />
      </IpcProvider>,
    );
    const search = screen.getByRole("combobox", { name: "Global search" });
    fireEvent.focus(search);
    await waitFor(() => expect(ipc.decisionsList).toHaveBeenCalled());
    fireEvent.change(search, { target: { value: "dark" } });
    fireEvent.click(await screen.findByText("Dark mode"));
    expect(onNavigate).toHaveBeenCalledWith("decisions");
  });

  it("New decision navigates to the run view", async () => {
    const onNavigate = vi.fn();
    const ipc = fakeIpc();
    render(
      <IpcProvider client={ipc}>
        <TopBar view="decisions" onNavigate={onNavigate} running={false} />
      </IpcProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: /new decision/i }));
    expect(onNavigate).toHaveBeenCalledWith("run");
  });

  it("disables workspace switching and search while a run streams", async () => {
    renderBar(fakeIpc(), { running: true });
    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: "Workspace" })).toBeDisabled(),
    );
    expect(screen.getByRole("combobox", { name: "Global search" })).toBeDisabled();
  });
});
