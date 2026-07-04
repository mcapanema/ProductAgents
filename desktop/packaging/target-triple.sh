#!/usr/bin/env bash
# Shared by build-sidecar.sh / ensure-sidecar.sh. Sets TRIPLE and EXT.
# Source this file; do not execute directly.

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

case "$TRIPLE" in
  *windows*) EXT=".exe" ;;
  *)         EXT="" ;;
esac
