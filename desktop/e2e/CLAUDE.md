# e2e/ — Playwright browser tests

The native Tauri window **cannot** be browser-automated on macOS (no WKWebView
WebDriver; `tauri-driver` is Windows/Linux only). So end-to-end UI testing drives
the **React frontend in a real headless browser** (Chromium) against the Vite dev
server, with the dev WebSocket bridge standing in for the Tauri sidecar.

Vitest owns unit tests (`src/**/*.test.ts*`); Playwright owns these browser specs.
Vitest is configured to **exclude `e2e/**`** so the two runners never collide.

## How it wires up (`../playwright.config.ts`)

`webServer` starts **two** processes before the specs and tears them down after:
1. `npm run dev` → the Vite frontend at `http://localhost:1420`.
2. `uv run productagents serve-ws --port 7420` (cwd `..`) → the dev WebSocket
   bridge exposing the same Application Layer as `productagents ipc`.

Both are health-checked by **TCP `port`**, not `url` — the bridge speaks no HTTP,
so an HTTP probe would fail/log noise. Outside Tauri, the frontend's
`createClient()` auto-connects to `ws://127.0.0.1:7420`, so the in-browser app
reaches live backend data.

## The specs

- `shell.spec.ts` — render + navigation only. Passes regardless of backend data
  (sidebar buttons + panel headings don't depend on IPC results).
- `bridge.spec.ts` — proves the full **browser → WS → ipc → platform** round-trip.
  Assertions are **DB-content-tolerant**: each uses Playwright's `locator.or()` to
  accept *either* real rows (`.list-item`) *or* the empty-state text. Both outcomes
  prove the IPC round-trip resolved (didn't hang, didn't crash) — so the specs are
  green whether or not the workspace has decisions/sessions.

## Running

```bash
cd desktop
npx playwright install chromium   # first time
npm run e2e                       # self-contained: boots Vite + bridge, runs specs
```

## Conventions

- Query by **role/text**, scoped to regions where ambiguous (e.g. the sidebar
  "Run" button and the panel's "Run" submit button both exist —
  `getByRole("navigation").getByRole("button", { name: "Run" })`).
- Keep new specs **backend-state-independent** (use the `.or(empty-state)` pattern)
  unless the spec itself seeds data first.
- **The Run panel's live execution is not covered here** — it needs a configured
  model + API key. Cover Run only in a spec that sets one up, or leave it manual.
- `playwright-report/` and `test-results/` are gitignored.
