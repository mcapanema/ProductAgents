# Releasing ProductAgents (desktop)

Releases are built by `.github/workflows/release.yml` on a `v*` tag: a matrix of
native runners (macOS arm64 + Intel, Ubuntu, Windows) each freezes its own
PyInstaller sidecar and runs `tauri build`, and `tauri-apps/tauri-action`
uploads the installers + a signed `latest.json` to a **draft** GitHub Release.

## One-time setup

1. **Updater signing key** (already generated during Phase 9):
   - `TAURI_SIGNING_PRIVATE_KEY` — contents of the private key file
     (`~/.tauri/productagents-updater.key`).
   - `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` — empty string (the key was generated
     with `--ci`/no password; rotate by regenerating with a password if needed).
   - Add both under **Settings → Secrets and variables → Actions**.
   - The matching **public** key lives in `desktop/src-tauri/tauri.conf.json`
     (`plugins.updater.pubkey`). To rotate, run
     `cd desktop && npm run tauri signer generate -- -w ~/.tauri/productagents-updater.key`,
     update the pubkey, and replace both secrets.

## Cutting a release

1. Bump the version in **all four** files to the same value (a test enforces
   this — `tests/test_packaging.py::test_desktop_version_matches_pyproject`):
   - `pyproject.toml` → `[project] version`
   - `desktop/src-tauri/tauri.conf.json` → `version`
   - `desktop/src-tauri/Cargo.toml` → `[package] version`
   - `desktop/package.json` → `version`
2. `uv run pytest tests/test_packaging.py` — green.
3. Commit, then tag and push:
   ```bash
   git tag v0.1.1 && git push origin v0.1.1
   ```
4. Watch the **release** workflow. When green, open the draft Release, confirm
   all platform installers + `latest.json` are attached, write notes, and
   **Publish**. The updater feed
   (`.../releases/latest/download/latest.json`) resolves to the newest
   published release, so publishing is what ships the update to existing users.

## Auto-update flow

Installed apps call `check()` against the `latest.json` on the latest Release,
verify its minisign signature against the embedded `pubkey`, download the new
bundle, install, and relaunch (Settings → "Check for updates"). This is
independent of OS code-signing.

## Adding OS code-signing later (currently unsigned)

Builds ship unsigned today. To sign without restructuring anything:
- **macOS**: set `APPLE_CERTIFICATE`, `APPLE_CERTIFICATE_PASSWORD`,
  `APPLE_SIGNING_IDENTITY`, `APPLE_ID`, `APPLE_PASSWORD`, `APPLE_TEAM_ID` as
  Actions secrets — `tauri-action` notarizes automatically when present. No
  workflow code change needed.
- **Windows**: configure `bundle.windows.certificateThumbprint` (or an Azure
  Trusted Signing block) in `tauri.conf.json` and add the cert secret.
These are additive; the rest of the pipeline is unchanged.
