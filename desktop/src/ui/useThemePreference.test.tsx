import { beforeEach, describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, renderHook, act, waitFor } from "@testing-library/react";
import { useThemePreference } from "./useThemePreference";
import { THEME_STORAGE_KEY } from "./theme";
import type { IpcClient } from "../ipc/client";

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

  it("applies the DB preference once IPC is ready, without writing back", async () => {
    window.localStorage.setItem("pa-theme", "light");
    const preferencesGet = vi.fn(async () => ({ theme: "dark" }));
    const preferencesSet = vi.fn(async () => ({ theme: "dark" }));
    const ipc = { preferencesGet, preferencesSet } as unknown as IpcClient;

    const { result } = renderHook(() => useThemePreference(ipc));
    await waitFor(() => expect(result.current.pref).toBe("dark"));
    expect(window.localStorage.getItem("pa-theme")).toBe("dark");
    expect(preferencesSet).not.toHaveBeenCalled();
  });

  it("setPref persists to localStorage and the workspace DB", async () => {
    const preferencesGet = vi.fn(async () => ({ theme: null }));
    const preferencesSet = vi.fn(async () => ({ theme: "system" }));
    const ipc = { preferencesGet, preferencesSet } as unknown as IpcClient;

    const { result } = renderHook(() => useThemePreference(ipc));
    act(() => result.current.setPref("system"));
    expect(window.localStorage.getItem("pa-theme")).toBe("system");
    await waitFor(() => expect(preferencesSet).toHaveBeenCalledWith("system"));
  });

  it("ignores an invalid DB value", async () => {
    window.localStorage.setItem("pa-theme", "light");
    const ipc = {
      preferencesGet: vi.fn(async () => ({ theme: "purple" })),
      preferencesSet: vi.fn(),
    } as unknown as IpcClient;
    const { result } = renderHook(() => useThemePreference(ipc));
    await new Promise((r) => setTimeout(r, 0));
    expect(result.current.pref).toBe("light");
  });
});
