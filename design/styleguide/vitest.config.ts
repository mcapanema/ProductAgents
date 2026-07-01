import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Pure-logic tests only (see antd-pilot/theme.test.ts) — the gallery
// components themselves are verified in-browser, matching every other
// module in this styleguide (see design/design-system-plan.md).
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
  },
});
