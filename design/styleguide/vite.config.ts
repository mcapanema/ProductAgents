import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Standalone styleguide dev server — the review surface for every design phase.
export default defineConfig({
  plugins: [react()],
  server: { port: 5174, open: true },
});
