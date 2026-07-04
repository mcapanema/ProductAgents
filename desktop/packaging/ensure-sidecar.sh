#!/usr/bin/env bash
# Runs automatically before every `npm run tauri ...` (wired as `pretauri` in
# package.json). Tauri validates tauri.conf.json's externalBin even for dev
# builds, but the sidecar binary is gitignored (~38MB) and doesn't travel with
# git worktree checkouts. Make that a non-issue instead of a recurring manual
# step: if the binary for this machine's target triple is already present,
# this is a no-op; otherwise copy it from another worktree of the same repo
# (instant — debug builds spawn the dev sidecar so staleness doesn't matter),
# falling back to a full `make build-sidecar` rebuild if no copy is available
# anywhere (e.g. a genuinely fresh clone).
set -euo pipefail

cd "$(dirname "$0")/../.."  # repo root

# shellcheck source=./target-triple.sh
source desktop/packaging/target-triple.sh

BIN_NAME="productagents-ipc-${TRIPLE}${EXT}"
BIN_PATH="desktop/src-tauri/binaries/${BIN_NAME}"

if [ -f "$BIN_PATH" ]; then
  exit 0
fi

mkdir -p desktop/src-tauri/binaries

GIT_DIR="$(git rev-parse --git-dir 2>/dev/null)" || GIT_DIR=""
GIT_COMMON="$(git rev-parse --git-common-dir 2>/dev/null)" || GIT_COMMON=""
if [ -n "$GIT_DIR" ] && [ "$(cd "$GIT_DIR" && pwd -P)" != "$(cd "$GIT_COMMON" && pwd -P)" ]; then
  # We're in a linked worktree — look for the binary in every other worktree
  # of this repo (the main checkout first, since that's where `make
  # build-sidecar` is normally run).
  MAIN_ROOT="$(git -C "$GIT_COMMON/.." rev-parse --show-toplevel)"
  for candidate in "$MAIN_ROOT" $(git worktree list --porcelain | sed -n 's/^worktree //p'); do
    SRC="$candidate/desktop/src-tauri/binaries/${BIN_NAME}"
    if [ -f "$SRC" ] && [ "$(cd "$candidate" && pwd -P)" != "$(pwd -P)" ]; then
      cp "$SRC" "$BIN_PATH"
      echo "sidecar -> copied from $candidate" >&2
      exit 0
    fi
  done
fi

echo "sidecar binary missing everywhere — building it now (make build-sidecar)..." >&2
bash desktop/packaging/build-sidecar.sh
