import { describe, expect, test } from "vitest";

import { summarizeExcelImport } from "@/app/catasto/gis/excel-references";

const counts = (overrides: Partial<Record<"processed" | "found" | "not_found" | "multiple" | "invalid", number>> = {}) => ({
  processed: 10,
  found: 4,
  not_found: 0,
  multiple: 0,
  invalid: 0,
  ...overrides,
});

describe("summarizeExcelImport", () => {
  test("reports an error when no particella was found, regardless of geometry", () => {
    expect(summarizeExcelImport(counts({ found: 0, processed: 5, not_found: 5 }), 3)).toEqual({
      kind: "error",
      message: "Nessuna particella trovata su 5 righe.",
    });
  });

  test("reports an error when found particelle have no geometry", () => {
    expect(summarizeExcelImport(counts({ found: 4, not_found: 2 }), 0)).toEqual({
      kind: "error",
      message: "Trovate 4 particelle ma nessuna ha geometria: controlla che lo shapefile sia stato importato.",
    });
  });

  test("returns null for a clean import with geometry", () => {
    expect(summarizeExcelImport(counts(), 4)).toBeNull();
  });

  test("returns null when the anomaly sum is not positive (including NaN)", () => {
    expect(summarizeExcelImport(counts({ not_found: Number.NaN }), 4)).toBeNull();
  });

  test("lists every anomaly in the original order", () => {
    expect(summarizeExcelImport(counts({ found: 6, processed: 12, not_found: 3, multiple: 2, invalid: 1 }), 6)).toEqual({
      kind: "info",
      message: "Import completato: trovate 6/12. Non trovate: 3. Multiple: 2. Righe invalide: 1.",
    });
  });

  test.each([
    [{ not_found: 2 }, "Import completato: trovate 4/10. Non trovate: 2."],
    [{ multiple: 1 }, "Import completato: trovate 4/10. Multiple: 1."],
    [{ invalid: 5 }, "Import completato: trovate 4/10. Righe invalide: 5."],
  ])("lists only the non-zero anomaly %o", (overrides, message) => {
    expect(summarizeExcelImport(counts(overrides), 2)).toEqual({ kind: "info", message });
  });
});
