import path from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

function resolveCoverageInclude(): string[] {
  const configured = process.env.VITEST_COVERAGE_INCLUDE
    ?.split(",")
    .map((value) => value.trim())
    .filter(Boolean)
    .map((value) => (value.startsWith("frontend/") ? value.slice("frontend/".length) : value));

  if (configured && configured.length > 0) {
    return configured;
  }

  return [
    "src/components/catasto/file-picker.tsx",
    "src/components/catasto/meter-reading-import-report.tsx",
  ];
}

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup-vitest.ts"],
    include: [
      "tests/unit/**/*.test.ts",
      "tests/unit/**/*.test.tsx",
      "tests/unit/**/*.test.js",
      "tests/unit/**/*.test.jsx",
    ],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html", "cobertura"],
      reportsDirectory: "./coverage",
      include: resolveCoverageInclude(),
      exclude: ["src/**/*.d.ts"],
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
