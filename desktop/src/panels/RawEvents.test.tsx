import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { RawEvents } from "./RawEvents";
import type { IpcEvent } from "../ipc/types";

describe("RawEvents", () => {
  it("renders nothing when there are no events", () => {
    const { container } = render(<RawEvents events={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders a labelled summary and each event's type + JSON payload", () => {
    const events: IpcEvent[] = [
      { type: "NodeProgress", payload: { node: "market", message: "go" } },
    ];
    render(<RawEvents events={events} />);
    expect(screen.getByText(/raw events \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText("NodeProgress")).toBeInTheDocument();
    expect(screen.getByText(/"node":"market"/)).toBeInTheDocument();
  });
});
