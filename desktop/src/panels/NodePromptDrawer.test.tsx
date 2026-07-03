import { describe, it, expect } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
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

const debateNode = { id: "debate", prompts: ["debate", "debate.advocate"] };

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
    expect(screen.getByText("Debate prompts")).toBeInTheDocument();
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
    expect(await screen.findByText("Saved.")).toBeInTheDocument();
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
