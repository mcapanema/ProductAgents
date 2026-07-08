import { describe, it, expect } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { PromptsPanel } from "./PromptsPanel";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";

function fake(overrides: Record<string, unknown> = {}): IpcClient {
  return {
    promptsList: async () => [
      { name: "market", versions: [0], active: 0 },
      { name: "strategist", versions: [0], active: 0 },
    ],
    promptsShow: async (name: string, version: number) => ({
      name,
      version,
      text: `${name} body $evidence`,
    }),
    promptsSave: async (name: string) => ({ name, versions: [0, 1], active: 1 }),
    promptsRollback: async (name: string) => ({ name, versions: [0, 1], active: 1 }),
    promptsDiff: async () => ({ name: "market", old: 0, new: 1, diff: "" }),
    ...overrides,
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
  it("disables Save until the draft is edited, then enables it", async () => {
    renderPanel(fake());
    fireEvent.click(await screen.findByText("market"));
    const save = await screen.findByRole("button", { name: /save as new version/i });
    expect(save).toBeDisabled();
    fireEvent.change(await screen.findByDisplayValue(/market body/), {
      target: { value: "edited $evidence" },
    });
    expect(save).toBeEnabled();
  });

  it("shows a success alert after a save", async () => {
    renderPanel(fake());
    fireEvent.click(await screen.findByText("market"));
    fireEvent.change(await screen.findByDisplayValue(/market body/), {
      target: { value: "edited $evidence" },
    });
    fireEvent.click(screen.getByRole("button", { name: /save as new version/i }));
    expect(await screen.findByText(/saved a new version/i)).toBeInTheDocument();
  });

  it("surfaces a save error instead of failing silently", async () => {
    renderPanel(fake({ promptsSave: async () => { throw new Error("ValueError: bad $placeholder"); } }));
    fireEvent.click(await screen.findByText("market"));
    fireEvent.change(await screen.findByDisplayValue(/market body/), {
      target: { value: "broken $nonsense" },
    });
    fireEvent.click(screen.getByRole("button", { name: /save as new version/i }));
    expect(await screen.findByText(/couldn't save/i)).toBeInTheDocument();
  });

  it("guards unsaved edits when switching prompts", async () => {
    renderPanel(fake());
    fireEvent.click(await screen.findByText("market"));
    fireEvent.change(await screen.findByDisplayValue(/market body/), {
      target: { value: "unsaved $evidence" },
    });
    // clicking another prompt must NOT silently discard the edit
    fireEvent.click(screen.getByText("strategist"));
    expect(await screen.findByText(/unsaved changes/i)).toBeInTheDocument();
    // the edited draft is still on screen (switch was blocked)
    expect(screen.getByDisplayValue("unsaved $evidence")).toBeInTheDocument();
    // discarding proceeds to the new prompt
    fireEvent.click(screen.getByRole("button", { name: /discard/i }));
    await waitFor(() =>
      expect(screen.getByDisplayValue(/strategist body/)).toBeInTheDocument(),
    );
  });
});
