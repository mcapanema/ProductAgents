import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ConnectorsPanel } from "./ConnectorsPanel";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";
import type { ConnectorHealth, ConnectorList, ConnectorSync } from "../ipc/types";

const list: ConnectorList = {
  connectors: [{ name: "github" }],
  problems: ["connector 'slack': unknown (not installed)"],
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

function fake(): IpcClient {
  return {
    connectorsList: async () => list,
    connectorsHealth: async () => health,
    connectorsSync: async () => sync,
  } as unknown as IpcClient;
}

describe("ConnectorsPanel", () => {
  it("lists connectors and config problems on load", async () => {
    render(
      <IpcProvider client={fake()}>
        <ConnectorsPanel />
      </IpcProvider>,
    );
    expect(await screen.findByText("github")).toBeInTheDocument();
    expect(
      screen.getByText(/connector 'slack': unknown/),
    ).toBeInTheDocument();
  });

  it("shows health detail after Check health", async () => {
    render(
      <IpcProvider client={fake()}>
        <ConnectorsPanel />
      </IpcProvider>,
    );
    await screen.findByText("github");
    fireEvent.click(screen.getByRole("button", { name: /check health/i }));
    await waitFor(() =>
      expect(screen.getByText(/reachable/)).toBeInTheDocument(),
    );
  });

  it("shows written counts after Sync now", async () => {
    render(
      <IpcProvider client={fake()}>
        <ConnectorsPanel />
      </IpcProvider>,
    );
    await screen.findByText("github");
    fireEvent.click(screen.getByRole("button", { name: /sync now/i }));
    await waitFor(() =>
      expect(screen.getByText(/7 written/)).toBeInTheDocument(),
    );
  });

  it("shows the last-sync timestamp on load", async () => {
    render(
      <IpcProvider client={fake()}>
        <ConnectorsPanel />
      </IpcProvider>,
    );
    await screen.findByText("github");
    await waitFor(() =>
      expect(screen.getByText(/last sync 2026-06-29/)).toBeInTheDocument(),
    );
  });

  it("shows error text when sync result is failed", async () => {
    const failedSync: ConnectorSync = {
      results: [{ connector: "github", written: 0, ok: false, error: "401 unauthorized" }],
      problems: [],
    };
    const failClient: IpcClient = {
      ...fake(),
      connectorsSync: async () => failedSync,
    } as unknown as IpcClient;
    render(
      <IpcProvider client={failClient}>
        <ConnectorsPanel />
      </IpcProvider>,
    );
    await screen.findByText("github");
    fireEvent.click(screen.getByRole("button", { name: /sync now/i }));
    await waitFor(() =>
      expect(screen.getByText(/401 unauthorized/)).toBeInTheDocument(),
    );
  });
});
