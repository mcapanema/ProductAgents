#!/usr/bin/env bash
# Freeze the IPC sidecar and place it where Tauri's externalBin expects it.
# Host-platform build only (macOS/Linux). Run from anywhere.
set -euo pipefail

cd "$(dirname "$0")/../.."  # repo root

# shellcheck source=./target-triple.sh
source desktop/packaging/target-triple.sh

uv run --group package pyinstaller \
  --noconfirm --clean \
  --distpath desktop/build/dist \
  --workpath desktop/build/work \
  desktop/packaging/productagents-ipc.spec

mkdir -p desktop/src-tauri/binaries
cp "desktop/build/dist/productagents-ipc${EXT}" \
   "desktop/src-tauri/binaries/productagents-ipc-${TRIPLE}${EXT}"

echo "sidecar -> desktop/src-tauri/binaries/productagents-ipc-${TRIPLE}${EXT}"
