import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
    // e2e/ holds Playwright specs (their own runner); keep them out of Vitest.
    exclude: ["e2e/**", "**/node_modules/**", "**/dist/**"],
  },
});
