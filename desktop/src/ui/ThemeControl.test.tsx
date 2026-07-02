import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ThemeControl } from "./ThemeControl";

describe("ThemeControl", () => {
  it("renders Light, Dark, and System options", () => {
    render(<ThemeControl value="light" onChange={vi.fn()} />);
    expect(screen.getByRole("radio", { name: /light/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /dark/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /system/i })).toBeInTheDocument();
  });

  it("marks the current value as checked", () => {
    render(<ThemeControl value="dark" onChange={vi.fn()} />);
    expect(screen.getByRole("radio", { name: /dark/i })).toBeChecked();
  });

  it("calls onChange with the clicked option's value", () => {
    const onChange = vi.fn();
    render(<ThemeControl value="light" onChange={onChange} />);
    fireEvent.click(screen.getByRole("radio", { name: /system/i }));
    expect(onChange).toHaveBeenCalledWith("system");
  });
});
