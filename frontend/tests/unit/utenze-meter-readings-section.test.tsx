import { describe, expect, test } from "vitest";

import { parseNumeric } from "@/components/utenze/number-format";

describe("UtenzeMeterReadingsSection numeric parsing", () => {
  test("keeps backend decimal strings from being inflated as Italian thousands", () => {
    expect(parseNumeric("173098.000")).toBe(173098);
    expect(parseNumeric("32660.000")).toBe(32660);
    expect(parseNumeric("1209.02")).toBe(1209.02);
  });

  test("parses Italian comma decimals and mixed thousands formats", () => {
    expect(parseNumeric("511,17")).toBe(511.17);
    expect(parseNumeric("1.209,02")).toBe(1209.02);
    expect(parseNumeric("1,209.02")).toBe(1209.02);
  });

  test("rejects empty or invalid values", () => {
    expect(parseNumeric("")).toBeNull();
    expect(parseNumeric("   ")).toBeNull();
    expect(parseNumeric(null)).toBeNull();
    expect(parseNumeric(undefined)).toBeNull();
    expect(parseNumeric("not-a-number")).toBeNull();
    expect(parseNumeric(Number.NaN)).toBeNull();
    expect(parseNumeric(42)).toBe(42);
  });
});
