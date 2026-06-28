# desktop/ — the V3 Tauri + React GUI

The desktop app is a **presentation adapter**, exactly like `productagents.app`'s
CLI/TUI — it owns no business logic. It talks to the platform **only** over the
JSON-over-stdio IPC protocol (`productagents ipc`), so it **never** imports
LangGraph, connectors, persistence, or any Python at all. It is a separate
JS/Rust project and is **not a member of the uv workspace**.

The cardinal rule mirrors the Python presentation contract: the GUI knows the
**NDJSON envelope**, nothing about how workflows execute. New backend capability
reaches the GUI as a new IPC method, never as a direct dependency.

## How it talks to the platform

```
React panels ── IpcClient ── transport ──┬─ Tauri shell (src-tauri) ── stdio ── `productagents ipc`
                                          └─ dev WebSocket ── `productagents serve-ws`  (browser/e2e only)
```

- In the packaged/native app, the Rust shell (`src-tauri/`) spawns `productagents
  ipc` as a child and bridges its stdout/stdin to the webview.
- In a plain browser (Vite dev server / Playwright), `transport.ts::createClient()`
  detects the absence of Tauri and falls back to the dev WebSocket bridge
  (`ws://127.0.0.1:7420`, served by `productagents serve-ws`). See `e2e/CLAUDE.md`.

## File structure

- `src/main.tsx` — React entry; mounts `<App>`.
- `src/ipc/` — **the seam to the backend.**
  - `types.ts` — TypeScript mirrors of the IPC envelope and result shapes. These
    **must stay in sync** with the Python builders (`ipc._decision_summary` /
    `_decision_detail`, `_session_dict`, etc.). If you change a Python result
    shape, change the matching type here.
  - `client.ts` — `IpcClient`: transport-agnostic. Correlates responses to
    requests by `id`, fans `run` events to a per-call `onEvent` handler. Takes a
    `send` + `subscribe` at construction so it unit-tests with no transport.
  - `transport.ts` — `isTauri()`, `createTauriClient()` (invoke/listen),
    `createWsClient()` (dev WebSocket, injectable socket), and `createClient()`
    which picks the right one for the environment.
- `src/app/` — `App.tsx` (sidebar nav + selected panel), `IpcProvider.tsx`
  (`useIpc()` context; builds the client once on mount, or takes an injected one
  in tests; `useIpc()` returns `IpcClient | null` — **null until ready, panels
  must handle it**), `App.css` (minimal IDE-like shell).
- `src/panels/` — one panel per resource. **Pure logic is extracted and
  unit-tested**, components stay thin: `runReducer.ts` (Run event stream),
  `decisionView.ts` (`formatConfidence`/`predictionRows`); `RunPanel.tsx`,
  `SessionsPanel.tsx`, `DecisionsPanel.tsx`.
- `src-tauri/` — the Rust shell (see `src-tauri/CLAUDE.md`).
- `e2e/` — Playwright browser tests (see `e2e/CLAUDE.md`).

## Commands

```bash
cd desktop
npm install            # first time (needs Node ≥ 18)
npm run dev            # Vite frontend only, http://localhost:1420 (browser-driveable)
npm run tauri dev      # build the Rust shell + open the native window (needs Rust toolchain)
npm test               # Vitest unit tests
npm run build          # tsc typecheck + Vite production build
npm run e2e            # Playwright (starts Vite + the WS bridge; needs `npx playwright install chromium`)
```

## Conventions

- **Degrade, never crash** (same ethos as the Python nodes). List loads use
  `.catch(() => set[])`; detail fetches use `try/catch`; a failed transport
  leaves `useIpc()` null and panels show their loading/empty states.
- **Match on envelope shape, not error text.** IPC `error` strings are
  human-facing; branch on `result`/`event`/`error` keys, never parse the string.
- **Test pure logic with Vitest, not components.** Reducers/selectors/formatters
  get direct unit tests (`*.test.ts`); components get light render/interaction
  tests with `@testing-library/react` and a fake `IpcClient`. jest-dom matchers
  are registered via `src/test-setup.ts` (wired in `vitest.config.ts`).
- **Vitest excludes `e2e/**`** — Playwright specs use their own runner.
- The native window **cannot** be browser-automated on macOS; automated UI
  testing runs the frontend in a real browser via the bridge (`e2e/`).
