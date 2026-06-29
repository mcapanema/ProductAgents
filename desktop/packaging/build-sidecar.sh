#!/usr/bin/env bash
# Freeze the IPC sidecar and place it where Tauri's externalBin expects it.
# Host-platform build only (macOS/Linux). Run from anywhere.
set -euo pipefail

cd "$(dirname "$0")/../.."  # repo root

TRIPLE="$(rustc -Vv 2>/dev/null | sed -n 's/^host: //p')" || true
if [ -z "$TRIPLE" ]; then
  # ponytail: fallback when rustc is not installed — derive triple from uname.
  # On macOS arm64 uname returns "arm64"; Tauri/rustc expect "aarch64".
  _ARCH="$(uname -m)"
  _OS="$(uname -s)"
  case "$_ARCH" in
    arm64)  _ARCH="aarch64" ;;
    x86_64) _ARCH="x86_64" ;;
  esac
  case "$_OS" in
    Darwin)            TRIPLE="${_ARCH}-apple-darwin" ;;
    Linux)             TRIPLE="${_ARCH}-unknown-linux-gnu" ;;
    MINGW*|MSYS*|CYGWIN*|Windows_NT) TRIPLE="${_ARCH}-pc-windows-msvc" ;;
    *) echo "could not determine target triple (no rustc, unsupported OS: $_OS)" >&2; exit 1 ;;
  esac
  echo "rustc not found; using derived triple: $TRIPLE" >&2
fi

uv run --group package pyinstaller \
  --noconfirm --clean \
  --distpath desktop/build/dist \
  --workpath desktop/build/work \
  desktop/packaging/productagents-ipc.spec

# On Windows PyInstaller emits productagents-ipc.exe; externalBin wants the
# triple suffix BEFORE the extension.
case "$TRIPLE" in
  *windows*) EXT=".exe" ;;
  *)         EXT="" ;;
esac

mkdir -p desktop/src-tauri/binaries
cp "desktop/build/dist/productagents-ipc${EXT}" \
   "desktop/src-tauri/binaries/productagents-ipc-${TRIPLE}${EXT}"

echo "sidecar -> desktop/src-tauri/binaries/productagents-ipc-${TRIPLE}${EXT}"
