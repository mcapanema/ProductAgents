import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { ConnectorIcon } from "./connectorIcons";

describe("ConnectorIcon", () => {
  it("renders a filled brand logo for known connectors", () => {
    const { container } = render(<ConnectorIcon name="github" />);
    const svg = container.querySelector("svg.connector-icon");
    expect(svg).not.toBeNull();
    expect(svg?.getAttribute("fill")).toBe("currentColor");
    expect(svg?.getAttribute("aria-hidden")).toBe("true");
  });

  it("renders a filled brand logo for obsidian", () => {
    const { container } = render(<ConnectorIcon name="obsidian" />);
    const svg = container.querySelector("svg.connector-icon");
    expect(svg).not.toBeNull();
    expect(svg?.getAttribute("fill")).toBe("currentColor");
  });

  it("falls back to an outline plug for unknown connectors", () => {
    const { container } = render(<ConnectorIcon name="mystery" size={16} />);
    const svg = container.querySelector("svg.connector-icon");
    expect(svg?.getAttribute("fill")).toBe("none");
    expect(svg?.getAttribute("width")).toBe("16");
  });
});
