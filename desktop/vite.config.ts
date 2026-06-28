import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// ponytail: fixed port 1420 so tauri.conf.json devUrl matches; clearScreen off
// keeps Rust build errors visible.
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: { port: 1420, strictPort: true },
});
