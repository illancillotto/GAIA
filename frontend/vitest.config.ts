import path from "node:path";
import { execFileSync } from "node:child_process";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const FRONTEND_RUNTIME_RE = /^frontend\/src\/.*\.(ts|tsx|js|jsx)$/;
const FRONTEND_RUNTIME_EXCLUDED_RE = /^frontend\/src\/(types\/|.*\.d\.ts$)/;

function configuredCoverageInclude(): string[] | null {
  const configured = process.env.VITEST_COVERAGE_INCLUDE?.split(",")
    .map((value) => value.trim())
    .filter(Boolean)
    .map((value) => (value.startsWith("frontend/") ? value.slice("frontend/".length) : value));

  if (configured && configured.length > 0) {
    return configured;
  }

  return null;
}

function changedRuntimeCoverageInclude(): string[] {
  const baseRef = process.env.VITEST_COVERAGE_BASE_REF || "origin/main";
  try {
    const output = execFileSync("git", ["diff", "--name-only", `${baseRef}...HEAD`], {
      cwd: path.resolve(__dirname, ".."),
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    });
    return output
      .split(/\r?\n/)
      .map((value) => value.trim())
      .filter((value) => FRONTEND_RUNTIME_RE.test(value) && !FRONTEND_RUNTIME_EXCLUDED_RE.test(value))
      .map((value) => value.slice("frontend/".length));
  } catch {
    return [];
  }
}

function resolveCoverageInclude(): string[] {
  const configured = configuredCoverageInclude();
  if (configured !== null) {
    return configured;
  }

  return changedRuntimeCoverageInclude();
}

const coverageInclude = resolveCoverageInclude();
const coverageThreshold = coverageInclude.length > 0 ? 100 : 0;

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
      include: coverageInclude,
      exclude: ["src/**/*.d.ts", "src/types/**"],
      thresholds: {
        lines: coverageThreshold,
        functions: coverageThreshold,
        statements: coverageThreshold,
        branches: coverageThreshold,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
