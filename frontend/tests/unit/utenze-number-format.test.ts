import { describe, expect, test } from "vitest";

import { parseNumeric } from "@/components/utenze/number-format";

describe("parseNumeric", () => {
  test("returns null for empty values", () => {
    expect(parseNumeric(null)).toBeNull();
    expect(parseNumeric("")).toBeNull();
    expect(parseNumeric("   ")).toBeNull();
  });

  test("returns finite numbers unchanged", () => {
    expect(parseNumeric(12.5)).toBe(12.5);
    expect(parseNumeric(Number.NaN)).toBeNull();
  });

  test("parses comma and dot decimal separators", () => {
    expect(parseNumeric("1.234,56")).toBe(1234.56);
    expect(parseNumeric("1,234.56")).toBe(1234.56);
    expect(parseNumeric("12,5")).toBe(12.5);
    expect(parseNumeric("12.5")).toBe(12.5);
  });

  test("returns null for non-numeric strings", () => {
    expect(parseNumeric("abc")).toBeNull();
  });
});
