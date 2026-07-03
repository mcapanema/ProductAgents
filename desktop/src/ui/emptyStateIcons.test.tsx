import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { EmptyStateIcon } from "./emptyStateIcons";

describe("EmptyStateIcon", () => {
  it("renders a distinct glyph per screen name", () => {
    const { container: sessions } = render(<EmptyStateIcon name="sessions" />);
    const { container: decisions } = render(<EmptyStateIcon name="decisions" />);
    const { container: connectors } = render(<EmptyStateIcon name="connectors" />);
    expect(sessions.innerHTML).not.toEqual(decisions.innerHTML);
    expect(sessions.innerHTML).not.toEqual(connectors.innerHTML);
    expect(decisions.innerHTML).not.toEqual(connectors.innerHTML);
  });

  it("renders a decorative, accessible svg", () => {
    const { container } = render(<EmptyStateIcon name="run" />);
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("aria-hidden", "true");
    expect(svg).toHaveAttribute("viewBox", "0 0 24 24");
  });
});
