import { beforeEach, describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useThemePreference } from "./useThemePreference";
import { THEME_STORAGE_KEY } from "./theme";

function Harness() {
  const { pref, setPref, resolved } = useThemePreference();
  return (
    <div>
      <span data-testid="pref">{pref}</span>
      <span data-testid="resolved">{resolved}</span>
      <button onClick={() => setPref("dark")}>set dark</button>
      <button onClick={() => setPref("system")}>set system</button>
    </div>
  );
}

describe("useThemePreference", () => {
  beforeEach(() => localStorage.clear());

  it("defaults to light and resolves to light", () => {
    render(<Harness />);
    expect(screen.getByTestId("pref").textContent).toBe("light");
    expect(screen.getByTestId("resolved").textContent).toBe("light");
  });

  it("setPref updates state, resolves, and persists to localStorage", () => {
    render(<Harness />);
    fireEvent.click(screen.getByText("set dark"));
    expect(screen.getByTestId("pref").textContent).toBe("dark");
    expect(screen.getByTestId("resolved").textContent).toBe("dark");
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });

  it("resolves 'system' via the OS preference (matchMedia stub -> light)", () => {
    render(<Harness />);
    fireEvent.click(screen.getByText("set system"));
    expect(screen.getByTestId("pref").textContent).toBe("system");
    expect(screen.getByTestId("resolved").textContent).toBe("light");
  });

  it("restores the persisted preference on mount", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "dark");
    render(<Harness />);
    expect(screen.getByTestId("pref").textContent).toBe("dark");
  });
});
