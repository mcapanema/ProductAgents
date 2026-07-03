import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ConnectorConfigForm } from "./ConnectorConfigForm";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";
import type { ConnectorConfigEntry } from "../ipc/types";

const entry: ConnectorConfigEntry = {
  connector: "github",
  installed: true,
  // config reflects what's actually persisted (the *_env convention); schema
  // is the real GitHubConfig shape (raw `token`, optional -> anyOf string|null).
  config: { owner: "acme", repo: "widgets", token_env: "PRODUCTAGENTS_GITHUB_TOKEN", enabled: true },
  schema: {
    properties: {
      enabled: { type: "boolean" }, owner: { type: "string" },
      repo: { type: "string" },
      token: { anyOf: [{ type: "string" }, { type: "null" }], title: "Token" },
    },
    required: ["owner", "repo"],
  },
  problems: [],
};

function renderWith(overrides: Partial<IpcClient> = {}, onSaved = () => {}) {
  const c = { ...overrides } as unknown as IpcClient;
  render(
    <IpcProvider client={c}>
      <ConnectorConfigForm key={entry.connector} entry={entry} onSaved={onSaved} />
    </IpcProvider>,
  );
  return c;
}

describe("ConnectorConfigForm", () => {
  it("renders the connector's fields from its schema", () => {
    renderWith();
    expect(screen.getByDisplayValue("acme")).toBeInTheDocument();
    expect(screen.getByRole("switch", { name: /github enabled/i })).toBeChecked();
    // secret reference field + companion secret-value input
    expect(screen.getByLabelText(/github token_env/i)).toHaveValue("PRODUCTAGENTS_GITHUB_TOKEN");
    expect(screen.getByLabelText(/github secret PRODUCTAGENTS_GITHUB_TOKEN/i)).toHaveValue("");
  });

  it("saves the edited block and typed secrets, then reports the update", async () => {
    const connectorsConfigSave = vi.fn(async () => entry);
    const onSaved = vi.fn();
    renderWith({ connectorsConfigSave }, onSaved);
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
    expect(onSaved).toHaveBeenCalledWith(entry);
  });

  it("surfaces a rejected save as an inline error", async () => {
    const connectorsConfigSave = vi.fn(async () => {
      throw new Error("connector 'github': env var X is not set");
    });
    renderWith({ connectorsConfigSave });
    fireEvent.click(screen.getByRole("button", { name: /save github/i }));
    expect(await screen.findByText(/env var X is not set/)).toBeInTheDocument();
  });
});
