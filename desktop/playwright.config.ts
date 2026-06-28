import { defineConfig, devices } from "@playwright/test";

/**
 * Drives the React frontend in a real (headless) Chromium against the Vite dev
 * server — the part of the GUI that can be browser-automated (the native Tauri
 * window cannot be on macOS). Two web servers are started:
 *   1. `npm run dev`  → the Vite frontend at http://localhost:1420
 *   2. `productagents serve-ws` → the dev WebSocket bridge at ws://127.0.0.1:7420,
 *      so the browser transport reaches the live Application Layer (decisions,
 *      sessions, run). Both are health-checked by TCP port (the WS bridge speaks
 *      no HTTP, so `port` — not `url` — is the correct probe).
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: false,
  use: {
    baseURL: "http://localhost:1420",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "npm run dev",
      port: 1420,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: "uv run productagents serve-ws --port 7420",
      port: 7420,
      cwd: "..", // repo root — `uv run` resolves the workspace from here
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
