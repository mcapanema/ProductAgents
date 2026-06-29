import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PromptsPanel } from "./PromptsPanel";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";
import type { PromptSummary } from "../ipc/types";

const list: PromptSummary[] = [
  { name: "strategist", versions: [0, 1, 2], active: 2 },
  { name: "judge", versions: [0], active: 0 },
];

function fake(): IpcClient {
  return {
    promptsList: async () => list,
    promptsShow: async (name: string, version: number) => ({
      name,
      version,
      text: `text of ${name}@${version}`,
    }),
    promptsDiff: async (name: string, old: number, next: number) => ({
      name,
      old,
      new: next,
      diff: `diff ${name} ${old}->${next}`,
    }),
  } as unknown as IpcClient;
}

function renderPanel(client: IpcClient) {
  render(
    <IpcProvider client={client}>
      <PromptsPanel />
    </IpcProvider>,
  );
}

describe("PromptsPanel", () => {
  it("lists prompt names on load", async () => {
    renderPanel(fake());
    expect(await screen.findByText("strategist")).toBeInTheDocument();
    expect(screen.getByText("judge")).toBeInTheDocument();
  });

  it("shows the active version's text after selecting a prompt", async () => {
    renderPanel(fake());
    fireEvent.click(await screen.findByText("strategist"));
    await waitFor(() =>
      expect(screen.getByText(/text of strategist@2/)).toBeInTheDocument(),
    );
  });

  it("shows a diff vs default when the prompt has overrides", async () => {
    renderPanel(fake());
    fireEvent.click(await screen.findByText("strategist"));
    await screen.findByText(/text of strategist@2/);
    fireEvent.click(screen.getByRole("button", { name: /diff vs default/i }));
    await waitFor(() =>
      expect(screen.getByText(/diff strategist 0->2/)).toBeInTheDocument(),
    );
  });

  it("offers no diff button for a default-only prompt", async () => {
    renderPanel(fake());
    fireEvent.click(await screen.findByText("judge"));
    await waitFor(() =>
      expect(screen.getByText(/text of judge@0/)).toBeInTheDocument(),
    );
    expect(screen.queryByRole("button", { name: /diff vs default/i })).toBeNull();
  });
});
