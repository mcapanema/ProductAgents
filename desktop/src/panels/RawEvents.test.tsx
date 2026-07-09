import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
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
    render(<RawEvents events={events} />);
    expect(screen.getByText(/raw events \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText("NodeProgress")).toBeInTheDocument();
    // JSON payload should NOT be rendered when details is collapsed (performance optimization)
    expect(screen.queryByText(/"node": "market"/)).not.toBeInTheDocument();
  });

  it("does not stringify events when details is collapsed", () => {
    const events: IpcEvent[] = [
      { type: "NodeProgress", payload: { node: "market", message: "go" } },
    ];
    const { container } = render(<RawEvents events={events} />);
    const details = container.querySelector("details");
    expect(details).not.toHaveAttribute("open");
    // JSON payload should not be rendered when closed
    expect(screen.queryByText(/"node": "market"/)).not.toBeInTheDocument();
  });
});
