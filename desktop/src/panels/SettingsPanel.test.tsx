import { beforeAll, beforeEach, describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { SettingsPanel } from "./SettingsPanel";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";
import type { ConfigSetParams, ConfigStatus, WorkspaceInfo } from "../ipc/types";

const reloadSpy = vi.fn();
beforeAll(() => {
  Object.defineProperty(window, "location", {
    value: { ...window.location, reload: reloadSpy },
    writable: true,
  });
});
beforeEach(() => reloadSpy.mockClear());

const status: ConfigStatus = {
  model: "anthropic:claude-sonnet-4-6",
  provider: "anthropic",
  key_var: "ANTHROPIC_API_KEY",
  key_present: true,
  problems: [],
  settings: {
    debate_rounds: 2,
    judge_threshold: 0.7,
    judge_max_retries: 1,
    max_retries: 6,
  },
  origins: {
    model: "db",
    model_provider: "db",
    debate_rounds: "db",
    judge_threshold: "db",
    judge_max_retries: "db",
    max_retries: "db",
  },
  providers: [
    { id: "anthropic", label: "Anthropic", key_var: "ANTHROPIC_API_KEY", default_model: "anthropic:claude-sonnet-4-6" },
    { id: "openai", label: "OpenAI", key_var: "OPENAI_API_KEY", default_model: "openai:gpt-4o" },
  ],
};

const workspace: WorkspaceInfo = {
  name: "default",
  active: true,
  created_at: "2026-06-28T00:00:00+00:00",
  root: "/home/u/.productagents/workspaces/default",
  db_url: "sqlite:///home/u/.productagents/workspaces/default/productagents.db",
  connectors_file: "/home/u/.productagents/workspaces/default/connectors.yaml",
  env_file: "/home/u/.productagents/workspaces/default/.env",
  log_file: "/home/u/.productagents/workspaces/default/productagents.log",
  prompts_dir: "/home/u/.productagents/workspaces/default/prompts",
};

function client(overrides: Partial<IpcClient> = {}): IpcClient {
  return {
    configGet: async () => status,
    workspacesShow: async () => workspace,
    ...overrides,
  } as unknown as IpcClient;
}

function renderPanel(c: IpcClient, onThemeChange = vi.fn(), running = false) {
  render(
    <IpcProvider client={c}>
      <SettingsPanel theme="light" onThemeChange={onThemeChange} running={running} />
    </IpcProvider>,
  );
  return { onThemeChange };
}

describe("SettingsPanel", () => {
  it("shows the Workspace/Application sub-navigation and defaults to Configuration", async () => {
    renderPanel(client());
    await screen.findByDisplayValue("anthropic:claude-sonnet-4-6");
    const nav = screen.getByRole("navigation", { name: /settings sections/i });
    expect(within(nav).getByRole("button", { name: /configuration/i })).toHaveAttribute("aria-current", "page");
    expect(within(nav).queryByRole("button", { name: /connectors/i })).not.toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: /preferences/i })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: /runtime/i })).toBeInTheDocument();
    // Logging is runtime config now — never a GUI field.
    expect(screen.queryByLabelText(/log level/i)).not.toBeInTheDocument();
  });

  it("navigating to Preferences shows the theme control; Configuration hides it", async () => {
    const { onThemeChange } = renderPanel(client());
    await screen.findByDisplayValue("anthropic:claude-sonnet-4-6");
    expect(screen.queryByRole("radio", { name: /dark/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /preferences/i }));
    fireEvent.click(screen.getByRole("radio", { name: /dark/i }));
    expect(onThemeChange).toHaveBeenCalledWith("dark");
  });

  it("shows the current model and key status on load, never echoing the key", async () => {
    renderPanel(client());
    expect(await screen.findByDisplayValue("anthropic:claude-sonnet-4-6")).toBeInTheDocument();
    // Key presence is conveyed by the API-key field's caption, never its value.
    expect(screen.getByText(/key present — leave blank to keep it/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/api key/i)).toHaveValue("");
  });

  it("changing provider dropdown sets model to that provider's default", async () => {
    renderPanel(client());
    await screen.findByDisplayValue("anthropic:claude-sonnet-4-6");
    // Exact match: "Provider max retries" also matches /provider/i.
    fireEvent.mouseDown(screen.getByLabelText("provider"));
    fireEvent.click(await screen.findByTitle("OpenAI"));
    expect(screen.getByLabelText(/model/i)).toHaveValue("openai:gpt-4o");
  });

  it("renders every pipeline tunable bound to its own setting", async () => {
    // Distinct values so a JSX swap between two Pref blocks is caught.
    const distinct: ConfigStatus = {
      ...status,
      settings: { debate_rounds: 3, judge_threshold: 0.85, judge_max_retries: 2, max_retries: 5 },
    };
    renderPanel(client({ configGet: async () => distinct } as Partial<IpcClient>));
    await screen.findByDisplayValue("anthropic:claude-sonnet-4-6");
    expect(screen.getByRole("spinbutton", { name: /debate rounds/i })).toHaveValue("3");
    // InputNumber's step=0.05 infers 2-decimal precision ("0.85"); compare numerically per
    // the documented jsdom/antd fallback (getAttribute over toHaveValue's string match).
    expect(Number(screen.getByRole("spinbutton", { name: /judge threshold/i }).getAttribute("value"))).toBe(0.85);
    expect(screen.getByRole("spinbutton", { name: /judge max retries/i })).toHaveValue("2");
    expect(screen.getByRole("spinbutton", { name: /provider max retries/i })).toHaveValue("5");
  });

  it("Runtime section shows a fallback when workspaces.show fails", async () => {
    renderPanel(client({ workspacesShow: async () => Promise.reject(new Error("nope")) } as Partial<IpcClient>));
    await screen.findByDisplayValue("anthropic:claude-sonnet-4-6");
    fireEvent.click(screen.getByRole("button", { name: /runtime/i }));
    expect(await screen.findByText(/workspace details unavailable/i)).toBeInTheDocument();
  });

  it("surfaces config problems", async () => {
    const bad: ConfigStatus = { ...status, key_present: false, problems: ["Missing API key: set OPENAI_API_KEY."] };
    renderPanel(client({ configGet: async () => bad } as Partial<IpcClient>));
    expect(await screen.findByText(/Missing API key/)).toBeInTheDocument();
  });

  it("saves the four tunables and model via config.set", async () => {
    const configSet = vi.fn(async (_params: ConfigSetParams) => status);
    renderPanel(client({ configSet } as Partial<IpcClient>));
    await screen.findByDisplayValue("anthropic:claude-sonnet-4-6");
    fireEvent.change(screen.getByRole("spinbutton", { name: /debate rounds/i }), { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));
    await waitFor(() => expect(configSet).toHaveBeenCalled());
    const params = configSet.mock.calls[0][0];
    expect(params.settings).toEqual({
      debate_rounds: 3, judge_threshold: 0.7, judge_max_retries: 1, max_retries: 6,
    });
  });

  it("labels env-overridden fields", async () => {
    const overridden = { ...status, origins: { ...status.origins, debate_rounds: "env" as const } };
    renderPanel(client({ configGet: async () => overridden } as Partial<IpcClient>));
    await screen.findByDisplayValue("anthropic:claude-sonnet-4-6");
    expect(screen.getByText(/overridden by environment/i)).toBeInTheDocument();
  });

  it("Runtime section shows workspace paths read-only", async () => {
    renderPanel(client());
    await screen.findByDisplayValue("anthropic:claude-sonnet-4-6");
    fireEvent.click(screen.getByRole("button", { name: /runtime/i }));
    expect(await screen.findByText(workspace.db_url!)).toBeInTheDocument();
  });

  it("shows Saved after a successful save and clears it on the next edit", async () => {
    const configSet = vi.fn(async () => status);
    renderPanel(client({ configSet } as Partial<IpcClient>));
    await screen.findByDisplayValue("anthropic:claude-sonnet-4-6");
    fireEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(await screen.findByText("Saved")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("spinbutton", { name: /debate rounds/i }), { target: { value: "3" } });
    expect(screen.queryByText("Saved")).not.toBeInTheDocument();
  });

  it("surfaces a failed save without clearing the form", async () => {
    const configSet = vi.fn(async () => {
      throw new Error("boom");
    });
    renderPanel(client({ configSet } as Partial<IpcClient>));
    await screen.findByDisplayValue("anthropic:claude-sonnet-4-6");
    fireEvent.change(screen.getByRole("spinbutton", { name: /debate rounds/i }), { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(await screen.findByText(/save failed/i)).toBeInTheDocument();
    expect(screen.getByRole("spinbutton", { name: /debate rounds/i })).toHaveValue("3");
  });

  it("prefills the rename field with the active workspace and disables when unchanged", async () => {
    renderPanel(client());
    const input = await screen.findByRole("textbox", { name: "workspace name" });
    expect(input).toHaveValue("default");
    expect(screen.getByRole("button", { name: "Rename" })).toBeDisabled();
  });

  it("renames then reloads", async () => {
    const workspacesRename = vi.fn().mockResolvedValue({ name: "main", active: true, created_at: "t" });
    renderPanel(client({ workspacesRename } as Partial<IpcClient>));
    const input = await screen.findByRole("textbox", { name: "workspace name" });
    fireEvent.change(input, { target: { value: "main" } });
    fireEvent.click(screen.getByRole("button", { name: "Rename" }));
    await waitFor(() => expect(workspacesRename).toHaveBeenCalledWith("default", "main"));
    await waitFor(() => expect(reloadSpy).toHaveBeenCalled());
  });

  it("shows a backend error inline and does not reload", async () => {
    const workspacesRename = vi
      .fn()
      .mockRejectedValue(new Error("WorkspaceError: workspace already exists: main"));
    renderPanel(client({ workspacesRename } as Partial<IpcClient>));
    const input = await screen.findByRole("textbox", { name: "workspace name" });
    fireEvent.change(input, { target: { value: "main" } });
    fireEvent.click(screen.getByRole("button", { name: "Rename" }));
    expect(await screen.findByText(/already exists/)).toBeInTheDocument();
    expect(reloadSpy).not.toHaveBeenCalled();
  });

  it("disables rename while a run streams and for invalid names", async () => {
    renderPanel(client(), vi.fn(), true);
    const input = await screen.findByRole("textbox", { name: "workspace name" });
    fireEvent.change(input, { target: { value: "main" } });
    expect(screen.getByRole("button", { name: "Rename" })).toBeDisabled();
  });

  it("renders an icon beside each settings nav item", async () => {
    renderPanel(client()); // uses the file's existing render helper + fake client
    // Each section button in the secondary nav carries a leading svg icon.
    const configBtn = await screen.findByRole("button", { name: /configuration/i });
    expect(configBtn.querySelector("svg.settings-nav__icon")).not.toBeNull();
    const prefsBtn = screen.getByRole("button", { name: /preferences/i });
    expect(prefsBtn.querySelector("svg.settings-nav__icon")).not.toBeNull();
  });
});
