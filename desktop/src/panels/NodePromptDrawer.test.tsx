import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NodePromptDrawer } from "./NodePromptDrawer";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";

function fake(overrides: Record<string, unknown> = {}): IpcClient {
  return {
    promptsList: async () => [
      { name: "debate", versions: [0], active: 0 },
      { name: "debate.advocate", versions: [0, 1], active: 1 },
    ],
    promptsShow: async (name: string, version: number) => ({
      name,
      version,
      text: `${name}@${version}`,
    }),
    promptsSave: async (name: string) => ({
      name,
      versions: [0, 1],
      active: 1,
    }),
    ...overrides,
  } as unknown as IpcClient;
}

const debateNode = { id: "debate", prompts: ["debate", "debate.advocate"], kind: "debate", config: {} };

function renderDrawer(client: IpcClient, node = debateNode) {
  render(
    <IpcProvider client={client}>
      <NodePromptDrawer node={node} onClose={() => {}} />
    </IpcProvider>,
  );
}

describe("NodePromptDrawer", () => {
  it("loads the active version of every prompt the node renders", async () => {
    renderDrawer(fake());
    expect(await screen.findByDisplayValue("debate@0")).toBeInTheDocument();
    expect(
      await screen.findByDisplayValue("debate.advocate@1"),
    ).toBeInTheDocument();
    expect(screen.getByText("Debate")).toBeInTheDocument();
  });

  it("saves an edited prompt as a new version", async () => {
    const saves: [string, string][] = [];
    renderDrawer(
      fake({
        promptsSave: async (name: string, text: string) => {
          saves.push([name, text]);
          return { name, versions: [0, 1], active: 1 };
        },
      }),
    );
    const area = await screen.findByDisplayValue("debate@0");
    fireEvent.change(area, { target: { value: "argue harder" } });
    fireEvent.click(
      screen.getAllByRole("button", { name: /save as new version/i })[0],
    );
    expect(await screen.findByText(/Saved a new version/)).toBeInTheDocument();
    expect(saves).toEqual([["debate", "argue harder"]]);
  });

  it("renders no drawer content when closed", () => {
    render(
      <IpcProvider client={fake()}>
        <NodePromptDrawer node={null} onClose={() => {}} />
      </IpcProvider>,
    );
    expect(screen.queryByText(/prompts/)).not.toBeInTheDocument();
  });
});

function fake2(overrides: Record<string, unknown> = {}): IpcClient {
  return {
    promptsList: async () => [{ name: "strategist", versions: [0, 1], active: 1 }],
    promptsShow: async (name: string, version: number) => ({ name, version, text: "Decide.\n$initiative" }),
    promptsSave: async (name: string) => ({ name, versions: [0, 1, 2], active: 2 }),
    ...overrides,
  } as unknown as IpcClient;
}
const strategistNode = { id: "strategist", prompts: ["strategist"], kind: "strategist", config: {} };
function renderDrawer2(client: IpcClient, onDirtyChange = () => {}) {
  render(<IpcProvider client={client}><NodePromptDrawer node={strategistNode} onClose={() => {}} onDirtyChange={onDirtyChange} /></IpcProvider>);
}

describe("NodePromptDrawer editor", () => {
  it("shows the node role header and current version label", async () => {
    renderDrawer2(fake2());
    expect(await screen.findByText(/Synthesis/)).toBeInTheDocument(); // KIND_META.strategist.role
    expect(await screen.findByText(/v1 · active/)).toBeInTheDocument();
  });

  it("lists the template variables used in the prompt", async () => {
    renderDrawer2(fake2());
    expect(await screen.findByText("$initiative")).toBeInTheDocument();
  });

  it("reports dirty state when the draft changes", async () => {
    const onDirty = vi.fn();
    renderDrawer2(fake2(), onDirty);
    const area = await screen.findByDisplayValue(/Decide\./);
    fireEvent.change(area, { target: { value: "Decide boldly.\n$initiative" } });
    await waitFor(() => expect(onDirty).toHaveBeenCalledWith(true));
  });

  it("surfaces a save error instead of failing silently", async () => {
    renderDrawer2(fake2({ promptsSave: async () => { throw new Error("boom"); } }));
    const area = await screen.findByDisplayValue(/Decide\./);
    fireEvent.change(area, { target: { value: "changed\n$initiative" } });
    fireEvent.click(screen.getAllByRole("button", { name: /save as new version/i })[0]);
    expect(await screen.findByText(/couldn't save/i)).toBeInTheDocument();
  });
});
