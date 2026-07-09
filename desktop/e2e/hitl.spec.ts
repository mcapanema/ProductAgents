import { test, expect } from "@playwright/test";

// Exercises the Run panel's human-in-the-loop approval flow against a real,
// configured model — the one live-execution path bridge.spec.ts deliberately
// leaves uncovered (see e2e/CLAUDE.md: "The Run panel's live execution is not
// covered here — it needs a configured model + API key"). Skipped by default so
// `npm run e2e` never makes a live model call; opt in locally with:
//
//   PA_E2E_HITL=1 npm run e2e -- hitl.spec.ts
//
// This requires the active workspace to have a tool-calling-capable model +
// API key configured (see root CLAUDE.md's "Structured output requires
// tool/function calling" note) — the run genuinely executes the advisory
// pipeline up to the governance interrupt.
test.skip(
  !process.env.PA_E2E_HITL,
  "set PA_E2E_HITL=1 (with a configured model + API key) to run the live HITL flow",
);

test("runs a decision with Require approval and completes after Approve", async ({ page }) => {
  test.setTimeout(120_000);

  await page.goto("/");
  const main = page.getByRole("main");

  await main.getByLabel("initiative").fill("HITL e2e smoke test");
  await main.getByLabel(/require approval/i).check();
  await main.getByRole("button", { name: "Run" }).click();

  // Real model call through the full analyst/debate/strategist/judge/risk chain
  // before the governance interrupt surfaces the Approve button.
  const approveButton = main.getByRole("button", { name: "Approve" });
  await expect(approveButton).toBeVisible({ timeout: 90_000 });
  await approveButton.click();

  // Resuming past governance runs the rest of the graph to completion.
  await expect(main.locator(".run-status")).toContainText(/finished/i, { timeout: 30_000 });
});
