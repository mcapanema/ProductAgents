// desktop/src/ui/ThemeShell.test.tsx
import { afterEach, describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";
import { ThemeShell } from "./ThemeShell";

afterEach(() => {
  vi.restoreAllMocks();
  document.documentElement.removeAttribute("data-theme");
  document.documentElement.removeAttribute("data-density");
});

describe("ThemeShell", () => {
  it("writes data-theme and data-density onto <html>", () => {
    render(
      <ThemeShell theme="dark" density="compact">
        <div>child</div>
      </ThemeShell>,
    );
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(document.documentElement.getAttribute("data-density")).toBe("compact");
  });

  it("re-reads resolved tokens only after the attribute commit (the pilot's dark-mode color-lag fix)", () => {
    const calls: string[] = [];
    const realSetAttribute = document.documentElement.setAttribute.bind(document.documentElement);
    vi.spyOn(document.documentElement, "setAttribute").mockImplementation((name, value) => {
      calls.push(`set:${name}=${value}`);
      realSetAttribute(name, value);
    });
    const realGetComputedStyle = window.getComputedStyle.bind(window);
    vi.spyOn(window, "getComputedStyle").mockImplementation((el, pseudo) => {
      calls.push("read");
      return realGetComputedStyle(el, pseudo as string | undefined);
    });

    const { rerender } = render(
      <ThemeShell theme="light" density="comfortable">
        <div>child</div>
      </ThemeShell>,
    );
    calls.length = 0; // only the toggle matters, not the initial mount

    rerender(
      <ThemeShell theme="dark" density="comfortable">
        <div>child</div>
      </ThemeShell>,
    );

    const setIndex = calls.indexOf("set:data-theme=dark");
    expect(setIndex).toBeGreaterThanOrEqual(0);
    expect(calls.slice(setIndex + 1)).toContain("read");
  });
});
