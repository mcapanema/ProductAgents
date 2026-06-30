import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { OrgMemoryPanel } from "./OrgMemoryPanel";
import { IpcProvider } from "../app/IpcProvider";
import type { IpcClient } from "../ipc/client";
import type { Lesson } from "../ipc/types";

const lessons: Lesson[] = [
  { decision_id: "d1", title: "Add SSO", text: "took longer than predicted", validated: true, prediction_accuracy: 0.5 },
  { decision_id: "d2", title: "Billing migration", text: 'Decided "Build it" (70% confidence): r', validated: false, prediction_accuracy: null },
];

function fake(): IpcClient {
  return { memoryLessons: async () => lessons } as unknown as IpcClient;
}

describe("OrgMemoryPanel", () => {
  it("lists lessons with a validated marker", async () => {
    render(
      <IpcProvider client={fake()}>
        <OrgMemoryPanel />
      </IpcProvider>,
    );
    expect(await screen.findByText("took longer than predicted")).toBeInTheDocument();
    expect(screen.getByText(/Billing migration/)).toBeInTheDocument();
  });
});
