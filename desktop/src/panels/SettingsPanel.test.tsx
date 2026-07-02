import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SettingsPanel } from "./SettingsPanel";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";
import type { ConfigStatus } from "../ipc/types";

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

function renderPanel(client: IpcClient, onThemeChange = vi.fn()) {
  render(
    <IpcProvider client={client}>
      <SettingsPanel theme="light" onThemeChange={onThemeChange} />
    </IpcProvider>,
  );
  return { onThemeChange };
}

describe("SettingsPanel", () => {
  it("renders the theme control and reports changes", () => {
    const { onThemeChange } = renderPanel({ configGet: async () => status } as unknown as IpcClient);
    // Theme control is independent of config load — present immediately.
    expect(screen.getByRole("radio", { name: /light/i })).toBeChecked();
    fireEvent.click(screen.getByRole("radio", { name: /dark/i }));
    expect(onThemeChange).toHaveBeenCalledWith("dark");
  });

  it("shows the current model and key status on load", async () => {
    renderPanel({ configGet: async () => status } as unknown as IpcClient);
    expect(await screen.findByDisplayValue("anthropic:claude-sonnet-4-6")).toBeInTheDocument();
    expect(screen.getByText(/key present/i)).toBeInTheDocument();
    // The stored key is never echoed into the field.
    expect(screen.getByLabelText(/api key/i)).toHaveValue("");
  });

  it("saves the edited model and api key via config.set", async () => {
    const configSet = vi.fn(async () => ({ ...status, model: "openai:gpt-4o" }));
    renderPanel({ configGet: async () => status, configSet } as unknown as IpcClient);
    await screen.findByDisplayValue("anthropic:claude-sonnet-4-6");

    fireEvent.change(screen.getByLabelText(/model/i), { target: { value: "openai:gpt-4o" } });
    fireEvent.change(screen.getByLabelText(/api key/i), { target: { value: "sk-new" } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() =>
      expect(configSet).toHaveBeenCalledWith({ model: "openai:gpt-4o", provider: "openai", api_key: "sk-new" }),
    );
    // The key field is cleared after a successful save (no echo of the just-set key).
    await waitFor(() => expect(screen.getByLabelText(/api key/i)).toHaveValue(""));
  });

  it("changing provider dropdown sets model to that provider's default", async () => {
    renderPanel({ configGet: async () => status } as unknown as IpcClient);
    await screen.findByDisplayValue("anthropic:claude-sonnet-4-6");

    fireEvent.mouseDown(screen.getByLabelText(/provider/i));
    fireEvent.click(await screen.findByTitle("OpenAI"));

    expect(screen.getByLabelText(/model/i)).toHaveValue("openai:gpt-4o");
  });

  it("surfaces config problems", async () => {
    const bad: ConfigStatus = { ...status, key_present: false, problems: ["Missing API key: set OPENAI_API_KEY."] };
    renderPanel({ configGet: async () => bad } as unknown as IpcClient);
    expect(await screen.findByText(/Missing API key/)).toBeInTheDocument();
  });
});
