import { describe, expect, test } from "vitest";

import { getPresenzeCompanyLabel } from "@/lib/presenze-display";

describe("getPresenzeCompanyLabel", () => {
  test("returns trimmed company label when present", () => {
    expect(getPresenzeCompanyLabel("  Acme Srl  ", "ACME", "fallback")).toBe("Acme Srl");
  });

  test("returns fallback for empty or whitespace labels", () => {
    expect(getPresenzeCompanyLabel(null, "ACME", "fallback")).toBe("fallback");
    expect(getPresenzeCompanyLabel("", "ACME", "fallback")).toBe("fallback");
    expect(getPresenzeCompanyLabel("   ", "ACME", "fallback")).toBe("fallback");
  });

  test("defaults fallback to empty string", () => {
    expect(getPresenzeCompanyLabel(undefined, null)).toBe("");
  });
});
