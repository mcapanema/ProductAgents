import { test, expect } from "@playwright/test";

// Proves the full browser → WS bridge → ipc → Application Layer round-trip:
// the React panels reach the live backend through `productagents serve-ws`.
// Assertions are DB-content-tolerant — either real rows render or the empty
// state shows; both mean the IPC round-trip resolved (not hung, not crashed).

test("Decision Explorer completes an IPC round-trip via the WS bridge", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("navigation").getByRole("button", { name: "Decisions" }).click();

  await expect(
    page
      .locator(".list-item")
      .first()
      .or(page.getByText(/no decisions recorded yet/i)),
  ).toBeVisible({ timeout: 15_000 });
});

test("Sessions completes an IPC round-trip via the WS bridge", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("navigation").getByRole("button", { name: "Sessions" }).click();

  await expect(
    page
      .locator(".list-item")
      .first()
      .or(page.getByText(/no sessions recorded yet/i)),
  ).toBeVisible({ timeout: 15_000 });
});
