import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { ConnectorsPanel } from "./ConnectorsPanel";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";
import type { ConnectorConfigEntry, ConnectorHealth, ConnectorList, ConnectorSync } from "../ipc/types";

const github: ConnectorConfigEntry = {
  connector: "github",
  installed: true,
  title: "GitHub",
  description: "Syncs repository issues into customer feedback.",
  config: { owner: "acme", repo: "widgets", enabled: true },
  schema: {
    properties: { enabled: { type: "boolean" }, owner: { type: "string" }, repo: { type: "string" } },
    required: ["owner", "repo"],
  },
  problems: [],
};
const jira: ConnectorConfigEntry = {
  connector: "jira",
  installed: true,
  title: "Jira",
  description: "Syncs Jira issues into customer feedback.",
  config: {},
  schema: { properties: { enabled: { type: "boolean" }, url: { type: "string" } } },
  problems: [],
};

const list: ConnectorList = {
  connectors: [{ name: "github" }],
  problems: [],
  last_synced: { github: "2026-06-29T10:00:00+00:00" },
};
const health: ConnectorHealth = {
  statuses: { github: { ok: true, detail: "reachable" } },
  problems: [],
};
const sync: ConnectorSync = {
  results: [{ connector: "github", written: 7, ok: true, error: null }],
  problems: [],
};

function renderPanel(overrides: Record<string, unknown> = {}) {
  const client = {
    connectorsConfigList: async () => [github, jira],
    connectorsList: async () => list,
    connectorsHealth: async () => health,
    connectorsSync: async () => sync,
    connectorsConfigSave: async () => github,
    ...overrides,
  } as unknown as IpcClient;
  render(
    <IpcProvider client={client}>
      <ConnectorsPanel />
    </IpcProvider>,
  );
}

describe("ConnectorsPanel", () => {
  it("groups connectors into Enabled and Available and selects the first enabled one", async () => {
    renderPanel();
    const nav = await screen.findByRole("navigation", { name: "Connectors" });
    expect(within(nav).getByText("Enabled")).toBeInTheDocument();
    expect(within(nav).getByText("Available")).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: /github/i })).toHaveAttribute("aria-current", "page");
    // detail screen for the selected connector: registry title + description
    expect(await screen.findByRole("heading", { name: "GitHub" })).toBeInTheDocument();
    expect(screen.getByText(/repository issues into customer feedback/i)).toBeInTheDocument();
    expect(screen.getByText("Not checked")).toBeInTheDocument();
    expect(screen.getByText(/last synced/i)).toBeInTheDocument();
  });

  it("opens a connector's configuration screen on click", async () => {
    renderPanel();
    const nav = await screen.findByRole("navigation", { name: "Connectors" });
    fireEvent.click(within(nav).getByRole("button", { name: /jira/i }));
    expect(await screen.findByRole("heading", { name: "Jira" })).toBeInTheDocument();
    expect(screen.getByText("Not connected")).toBeInTheDocument();
    // the schema-driven form is on the screen
    expect(screen.getByLabelText(/jira url/i)).toBeInTheDocument();
  });

  it("shows Connected with the health detail after Check health", async () => {
    renderPanel();
    await screen.findByRole("heading", { name: "GitHub" });
    fireEvent.click(screen.getByRole("button", { name: /check health/i }));
    expect(await screen.findByText("Connected")).toBeInTheDocument();
    expect(screen.getByText(/reachable/)).toBeInTheDocument();
  });

  it("shows the written count after Sync now", async () => {
    renderPanel();
    await screen.findByRole("heading", { name: "GitHub" });
    fireEvent.click(screen.getByRole("button", { name: /sync now/i }));
    expect(await screen.findByText(/7 records written/)).toBeInTheDocument();
  });

  it("scopes Check health and Sync now to the selected connector", async () => {
    const calls: (string | undefined)[] = [];
    renderPanel({
      connectorsHealth: async (c?: string) => {
        calls.push(c);
        return health;
      },
      connectorsSync: async (c?: string) => {
        calls.push(c);
        return sync;
      },
    });
    await screen.findByRole("heading", { name: "GitHub" });
    fireEvent.click(screen.getByRole("button", { name: /check health/i }));
    expect(await screen.findByText("Connected")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /sync now/i }));
    expect(await screen.findByText(/7 records written/)).toBeInTheDocument();
    expect(calls).toEqual(["github", "github"]);
  });
});
