import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { PromptsPanel } from "./PromptsPanel";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";

function fake(overrides: Record<string, unknown> = {}): IpcClient {
  return {
    promptsList: async () => [
      { name: "market", versions: [0], active: 0 },
      { name: "strategist", versions: [0], active: 0 },
      // has an override (active !== 0) so it exercises the diff button + version switching
      { name: "judge", versions: [0, 1], active: 1 },
    ],
    promptsShow: async (name: string, version: number) => ({
      name,
      version,
      text: `${name} body v${version} $evidence`,
    }),
    promptsSave: async (name: string) => ({ name, versions: [0, 1], active: 1 }),
    promptsRollback: async (name: string) => ({ name, versions: [0, 1], active: 1 }),
    promptsDiff: async () => ({ name: "judge", old: 0, new: 1, diff: "- old body\n+ new body" }),
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

  it("hides the Diff vs default button for a prompt with no overrides", async () => {
    renderPanel(fake());
    fireEvent.click(await screen.findByText("market"));
    await screen.findByRole("button", { name: /save as new version/i });
    expect(screen.queryByRole("button", { name: /diff vs default/i })).not.toBeInTheDocument();
  });

  it("renders the diff against default when Diff vs default is clicked", async () => {
    renderPanel(fake());
    fireEvent.click(await screen.findByText("judge"));
    fireEvent.click(await screen.findByRole("button", { name: /diff vs default/i }));
    expect(await screen.findByText(/- old body/)).toBeInTheDocument();
  });

  it("switches versions when a version button is clicked", async () => {
    renderPanel(fake());
    fireEvent.click(await screen.findByText("judge"));
    expect(await screen.findByDisplayValue(/judge body v1/)).toBeInTheDocument();
    // scope to the detail pane and anchor the name: the list rows are buttons too
    // now (M9) and the rollback button's label also contains "v0 · default", so an
    // unscoped/unanchored query matches more than one.
    const detailPane = (await screen.findByRole("heading", { name: "judge" })).closest(
      ".master-detail__detail",
    ) as HTMLElement;
    fireEvent.click(within(detailPane).getByRole("button", { name: /^v0 . default$/i }));
    expect(await screen.findByDisplayValue(/judge body v0/)).toBeInTheDocument();
  });

  it("calls promptsSave with the prompt name and edited text", async () => {
    const promptsSave = vi.fn(async (name: string) => ({
      name,
      versions: [0, 1],
      active: 1,
    }));
    renderPanel(fake({ promptsSave }));
    fireEvent.click(await screen.findByText("market"));
    fireEvent.change(await screen.findByDisplayValue(/market body/), {
      target: { value: "edited $evidence" },
    });
    fireEvent.click(screen.getByRole("button", { name: /save as new version/i }));
    await screen.findByText(/saved a new version/i);
    expect(promptsSave).toHaveBeenCalledWith("market", "edited $evidence");
  });

  it("prompt rows are keyboard-operable buttons", async () => {
    renderPanel(fake());
    const row = await screen.findByRole("button", { name: /market/i });
    row.focus();
    fireEvent.keyDown(row, { key: "Enter" }); // native <button> activates on Enter
    fireEvent.click(row); // native button: Enter/Space dispatch click
    expect(await screen.findByRole("button", { name: /save as new version/i })).toBeInTheDocument();
  });

  it("labels the glyph-only rollback button for screen readers", async () => {
    renderPanel(fake());
    fireEvent.click(await screen.findByText("judge"));
    expect(
      await screen.findByRole("button", { name: /roll back to v0/i }),
    ).toBeInTheDocument();
  });
});
