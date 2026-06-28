# src-tauri/ — the Rust shell (sidecar host + IPC bridge)

The native window and the bridge to the Python backend. Its **only** job is
transport: spawn the sidecar, frame its NDJSON, and shuttle lines to/from the
webview. No product logic lives here.

## What it does (`src/lib.rs`)

- On startup, spawns the sidecar with **`std::process`** — `uv run productagents
  ipc`, cwd = `repo_root()`, stdin/stdout piped. We deliberately use `std::process`,
  **not `tauri-plugin-shell`**, so there is no shell-scope permission config and
  no extra plugin dependency.
- Stores the child's stdin in Tauri managed state (`Sidecar(Mutex<ChildStdin>)`).
- A reader thread emits each stdout line to the webview as a **`ipc://message`**
  event (payload = the raw JSON line).
- Exposes the **`ipc_send(line: String)`** command, which writes `line + "\n"` to
  the child's stdin. The arg name `line` must match the JS `invoke("ipc_send",
  { line })` in `../src/ipc/transport.ts`, and `ipc://message` must match the
  `listen(...)` there.
- `repo_root()` = `env!("CARGO_MANIFEST_DIR")` + `../..` (`src-tauri → desktop →
  repo`). The dev sidecar resolves the uv workspace from there.

## Files

- `src/lib.rs` — `run()` (builder + sidecar spawn) and the `ipc_send` command.
- `src/main.rs` — thin entry calling `productagents_desktop_lib::run()`. The
  `[lib] name` in `Cargo.toml` must match this path.
- `Cargo.toml` — deps: `tauri`, `serde`, `serde_json` (no `tauri-plugin-shell`).
- `tauri.conf.json` — window + bundle config. `bundle.active = true` means
  `generate_context!()` **requires icons to exist** (see below).
- `build.rs` — `tauri_build::build()`.
- `icons/` — committed. **Required to compile.** Regenerate from the source PNG
  with `npm run tauri icon ../app-icon.png` (run from `desktop/`). Missing icons
  fail the Rust build with `failed to open icon .../icon.png`.

## Build / tracked files

- `cargo build` (from `src-tauri/`) is the fastest compile check; it does not
  open a window. `npm run tauri dev` (from `desktop/`) builds + launches.
- **`Cargo.lock` is committed** (this crate is an application binary).
- **`gen/schemas/` and `target/` are gitignored** (generated).

## Dev-mode ceilings (deferred to Phase 8e packaging)

- `# ponytail:` the sidecar is spawned as `uv run productagents ipc` for dev. The
  child `Child` handle is dropped after startup, and `std::process` does not kill
  it on app exit — **the sidecar can orphan** on quit. Phase 8e replaces this dev
  spawn with a bundled PyInstaller sidecar binary wired as a Tauri `externalBin`,
  which also fixes lifecycle. Don't add process-reaping plumbing before then.
