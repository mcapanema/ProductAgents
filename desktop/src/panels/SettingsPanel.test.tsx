import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SettingsPanel } from "./SettingsPanel";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";
import type { ConfigSetParams, ConfigStatus, WorkspaceInfo } from "../ipc/types";

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
    log_level: "INFO",
    github_repo: "",
    github_token_present: false,
  },
  providers: [
    { id: "anthropic", label: "Anthropic", key_var: "ANTHROPIC_API_KEY", default_model: "anthropic:claude-sonnet-4-6" },
    { id: "openai", label: "OpenAI", key_var: "OPENAI_API_KEY", default_model: "openai:gpt-4o" },
  ],
};

const workspace: WorkspaceInfo = {
  name: "default",
  active: true,
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

function renderPanel(c: IpcClient, onThemeChange = vi.fn()) {
  render(
    <IpcProvider client={c}>
      <SettingsPanel theme="light" onThemeChange={onThemeChange} />
    </IpcProvider>,
  );
  return { onThemeChange };
}

describe("SettingsPanel", () => {
  it("renders the theme control and reports changes", () => {
    const { onThemeChange } = renderPanel(client());
    expect(screen.getByRole("radio", { name: /light/i })).toBeChecked();
    fireEvent.click(screen.getByRole("radio", { name: /dark/i }));
    expect(onThemeChange).toHaveBeenCalledWith("dark");
  });

  it("shows the current model and key status on load, never echoing the key", async () => {
    renderPanel(client());
    expect(await screen.findByDisplayValue("anthropic:claude-sonnet-4-6")).toBeInTheDocument();
    // Exact match: the API-key field's own description also contains "Key present".
    expect(screen.getByText("Key present")).toBeInTheDocument();
    expect(screen.getByLabelText(/api key/i)).toHaveValue("");
  });

  it("renders every pipeline tunable from config settings", async () => {
    renderPanel(client());
    await screen.findByDisplayValue("anthropic:claude-sonnet-4-6");
    expect(screen.getByRole("spinbutton", { name: /debate rounds/i })).toHaveValue("2");
    // InputNumber's step=0.05 infers 2-decimal precision ("0.70"); compare numerically per
    // the brief's documented jsdom/antd fallback (getAttribute over toHaveValue's string match).
    expect(Number(screen.getByRole("spinbutton", { name: /judge threshold/i }).getAttribute("value"))).toBe(0.7);
    expect(screen.getByRole("spinbutton", { name: /judge max retries/i })).toHaveValue("1");
    expect(screen.getByRole("spinbutton", { name: /provider max retries/i })).toHaveValue("6");
  });

  it("saves the full form including tunables via config.set", async () => {
    const configSet = vi.fn(async (_params: ConfigSetParams) => status);
    renderPanel(client({ configSet } as Partial<IpcClient>));
    await screen.findByDisplayValue("anthropic:claude-sonnet-4-6");

    fireEvent.change(screen.getByRole("spinbutton", { name: /debate rounds/i }), { target: { value: "3" } });
    fireEvent.change(screen.getByLabelText(/github repository/i), { target: { value: "acme/widgets" } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => expect(configSet).toHaveBeenCalled());
    const params = configSet.mock.calls[0][0];
    expect(params.model).toBe("anthropic:claude-sonnet-4-6");
    expect(params.provider).toBe("anthropic");
    expect(params.api_key).toBeUndefined(); // blank secret omitted
    expect(params.settings).toMatchObject({
      debate_rounds: 3,
      judge_threshold: 0.7,
      judge_max_retries: 1,
      max_retries: 6,
      log_level: "INFO",
      github_repo: "acme/widgets",
    });
    expect(params.settings!.github_token).toBeUndefined();
  });

  it("changing provider dropdown sets model to that provider's default", async () => {
    renderPanel(client());
    await screen.findByDisplayValue("anthropic:claude-sonnet-4-6");
    // Exact match: "Provider max retries" also matches /provider/i.
    fireEvent.mouseDown(screen.getByLabelText("provider"));
    fireEvent.click(await screen.findByTitle("OpenAI"));
    expect(screen.getByLabelText(/model/i)).toHaveValue("openai:gpt-4o");
  });

  it("shows workspace paths read-only and hides the section when unavailable", async () => {
    renderPanel(client());
    expect(await screen.findByText(workspace.db_url)).toBeInTheDocument();
    expect(screen.getByText(workspace.prompts_dir)).toBeInTheDocument();
  });

  it("hides the workspace section when workspaces.show fails", async () => {
    renderPanel(client({ workspacesShow: async () => Promise.reject(new Error("nope")) } as Partial<IpcClient>));
    await screen.findByDisplayValue("anthropic:claude-sonnet-4-6");
    expect(screen.queryByText(/^workspace$/i)).not.toBeInTheDocument();
  });

  it("surfaces config problems", async () => {
    const bad: ConfigStatus = { ...status, key_present: false, problems: ["Missing API key: set OPENAI_API_KEY."] };
    renderPanel(client({ configGet: async () => bad } as Partial<IpcClient>));
    expect(await screen.findByText(/Missing API key/)).toBeInTheDocument();
  });
});
