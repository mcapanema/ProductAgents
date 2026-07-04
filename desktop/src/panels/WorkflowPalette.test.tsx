import { fireEvent, render, screen } from "@testing-library/react";
import { WorkflowPalette, newInstanceId } from "./WorkflowPalette";

const palette = [
  { kind: "market", label: "Market", role: "analyst", singleton: false,
    prompts: ["market"], reads: [], writes: ["reports"] },
  { kind: "judge", label: "Judge", role: "decision", singleton: true,
    prompts: ["judge"], reads: [], writes: [] },
];

test("lists palette kinds and fires onAdd", () => {
  const onAdd = vi.fn();
  render(<WorkflowPalette palette={palette} onAdd={onAdd} />);
  fireEvent.click(screen.getByRole("button", { name: /Market/ }));
  expect(onAdd).toHaveBeenCalledWith("market");
});

test("newInstanceId suffixes duplicates, keeps singleton ids", () => {
  expect(newInstanceId("market", new Set())).toBe("market");
  expect(newInstanceId("market", new Set(["market"]))).toBe("market#2");
  expect(newInstanceId("judge", new Set())).toBe("judge");
});
