import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { RawEvents } from "./RawEvents";
import type { IpcEvent } from "../ipc/types";

describe("RawEvents", () => {
  it("renders nothing when there are no events", () => {
    const { container } = render(<RawEvents events={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders a labelled summary and event type, but not JSON payload when collapsed", () => {
    const events: IpcEvent[] = [
      { type: "NodeProgress", payload: { node: "market", message: "go" } },
    ];
    const { container } = render(<RawEvents events={events} />);
    expect(screen.getByText(/raw events \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText("NodeProgress")).toBeInTheDocument();
    expect(container.querySelector("details")).not.toHaveAttribute("open");
    // JSON payload should NOT be rendered when details is collapsed (performance optimization)
    expect(screen.queryByText(/"node": "market"/)).not.toBeInTheDocument();
  });

  it("shows the JSON payload after clicking the summary to expand", async () => {
    const events: IpcEvent[] = [
      { type: "NodeProgress", payload: { node: "market", message: "go" } },
    ];
    render(<RawEvents events={events} />);
    fireEvent.click(screen.getByText(/raw events \(1\)/i));
    // jsdom fires <details>'s "toggle" event asynchronously (spec-accurate), so
    // the onToggle-driven React state update lands a tick after the click.
    await waitFor(() => expect(screen.getByText(/"node": "market"/)).toBeInTheDocument());
  });
});
