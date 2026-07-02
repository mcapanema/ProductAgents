import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SettingsConnectors } from "./SettingsConnectors";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";
import type { ConnectorConfigEntry } from "../ipc/types";

const entry: ConnectorConfigEntry = {
  connector: "github",
  installed: true,
  config: { owner: "acme", repo: "widgets", token_env: "PRODUCTAGENTS_GITHUB_TOKEN", enabled: true },
  schema: {
    properties: {
      enabled: { type: "boolean" }, owner: { type: "string" },
      repo: { type: "string" }, token_env: { type: "string" },
    },
    required: ["owner", "repo"],
  },
  problems: [],
};

function renderWith(overrides: Partial<IpcClient> = {}) {
  const c = { ...overrides } as unknown as IpcClient;
  render(
    <IpcProvider client={c}>
      <SettingsConnectors />
    </IpcProvider>,
  );
  return c;
}

describe("SettingsConnectors", () => {
  it("renders each connector's fields from its schema", async () => {
    renderWith({ connectorsConfigList: async () => [entry] });
    expect(await screen.findByDisplayValue("acme")).toBeInTheDocument();
    expect(screen.getByRole("switch", { name: /github enabled/i })).toBeChecked();
    // secret reference field + companion secret-value input
    expect(screen.getByLabelText(/github token_env/i)).toHaveValue("PRODUCTAGENTS_GITHUB_TOKEN");
    expect(screen.getByLabelText(/github secret PRODUCTAGENTS_GITHUB_TOKEN/i)).toHaveValue("");
  });

  it("saves the edited block and typed secrets", async () => {
    const connectorsConfigSave = vi.fn(async () => entry);
    renderWith({ connectorsConfigList: async () => [entry], connectorsConfigSave });
    await screen.findByDisplayValue("acme");
    fireEvent.change(screen.getByLabelText(/github repo/i), { target: { value: "gadgets" } });
    fireEvent.change(screen.getByLabelText(/github secret PRODUCTAGENTS_GITHUB_TOKEN/i), { target: { value: "ghp_x" } });
    fireEvent.click(screen.getByRole("button", { name: /save github/i }));
    await waitFor(() =>
      expect(connectorsConfigSave).toHaveBeenCalledWith(
        "github",
        expect.objectContaining({ owner: "acme", repo: "gadgets", enabled: true }),
        { PRODUCTAGENTS_GITHUB_TOKEN: "ghp_x" },
      ),
    );
  });

  it("surfaces a rejected save as an inline error", async () => {
    const connectorsConfigSave = vi.fn(async () => {
      throw new Error("connector 'github': env var X is not set");
    });
    renderWith({ connectorsConfigList: async () => [entry], connectorsConfigSave });
    await screen.findByDisplayValue("acme");
    fireEvent.click(screen.getByRole("button", { name: /save github/i }));
    expect(await screen.findByText(/env var X is not set/)).toBeInTheDocument();
  });

  it("shows an empty state when nothing is installed", async () => {
    renderWith({ connectorsConfigList: async () => [] });
    expect(await screen.findByText(/no connectors installed/i)).toBeInTheDocument();
  });
});
