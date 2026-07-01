import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// ponytail: fixed port 1420 so tauri.conf.json devUrl matches; clearScreen off
// keeps Rust build errors visible.
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    // src/ui/tokens.css @imports the design-system token CSS from ../design/
    // (repo-root sibling) so those files stay the single source of truth instead
    // of a copy — the dev server's default fs allowlist only covers desktop/, so
    // widen it to the repo root.
    fs: { allow: [".."] },
  },
});
