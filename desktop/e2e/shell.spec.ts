import { test, expect } from "@playwright/test";

// Shell-only checks: render + navigation. These pass regardless of backend data
// (the sidebar and panel headings don't depend on the WS bridge returning rows).

test("renders the sidebar nav and defaults to the Run panel", async ({ page }) => {
  await page.goto("/");
  const nav = page.getByRole("navigation");
  await expect(nav.getByRole("button", { name: "Run" })).toBeVisible();
  await expect(nav.getByRole("button", { name: "Sessions" })).toBeVisible();
  await expect(nav.getByRole("button", { name: "Decisions" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /run a decision/i }),
  ).toBeVisible();
});

test("navigates to the Decision Explorer and back to Run", async ({ page }) => {
  await page.goto("/");
  const nav = page.getByRole("navigation");

  await nav.getByRole("button", { name: "Decisions" }).click();
  await expect(
    page.getByRole("heading", { name: /decision explorer/i }),
  ).toBeVisible();

  await nav.getByRole("button", { name: "Run" }).click();
  await expect(
    page.getByRole("heading", { name: /run a decision/i }),
  ).toBeVisible();
});
