import { describe, expect, test } from "vitest";

import {
  formatRiordinoDate,
  formatRiordinoFileSize,
  formatRiordinoLabel,
} from "@/components/riordino/shared/format";

describe("formatRiordinoLabel", () => {
  test("returns dash for empty values", () => {
    expect(formatRiordinoLabel(null)).toBe("—");
    expect(formatRiordinoLabel("")).toBe("—");
  });

  test("title-cases underscore separated values", () => {
    expect(formatRiordinoLabel("in_lavorazione")).toBe("In Lavorazione");
  });
});

describe("formatRiordinoDate", () => {
  test("returns dash for empty values", () => {
    expect(formatRiordinoDate(undefined)).toBe("—");
  });

  test("returns raw value for invalid dates", () => {
    expect(formatRiordinoDate("not-a-date")).toBe("not-a-date");
  });

  test("formats valid ISO dates without time", () => {
    const formatted = formatRiordinoDate("2026-06-15T10:30:00.000Z");
    expect(formatted).toMatch(/15\/06\/2026/);
    expect(formatted).not.toMatch(/:/);
  });

  test("formats valid ISO dates with time", () => {
    const formatted = formatRiordinoDate("2026-06-15T10:30:00.000Z", true);
    expect(formatted).toMatch(/15\/06\/2026/);
    expect(formatted).toMatch(/:/);
  });
});

describe("formatRiordinoFileSize", () => {
  test("formats bytes, kilobytes, and megabytes", () => {
    expect(formatRiordinoFileSize(512)).toBe("512 B");
    expect(formatRiordinoFileSize(2048)).toBe("2.0 KB");
    expect(formatRiordinoFileSize(5 * 1024 * 1024)).toBe("5.0 MB");
  });
});
