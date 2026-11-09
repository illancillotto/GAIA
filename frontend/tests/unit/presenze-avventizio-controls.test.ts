import { describe, expect, it } from "vitest";
import { monthlyCellTone, monthlyDayStatus } from "@/lib/presenze-monthly-presentation";
import { buildMonthlySheet, type MonthlyDay } from "@/lib/presenze-monthly-sheet";

function day(overrides: Partial<MonthlyDay> = {}): MonthlyDay {
  const values = Array(13).fill(0);
  values[12] = "AG";
  return { date: "2026-10-02", present: true, weekend: false, values, ...overrides };
}

describe("Avventizio monthly projection controls", () => {
  it.each([undefined, false, true])("preserves the distinction from ordinary AG (%s)", flag => {
    const item = day({ avventizioNoPunches: flag });
    expect(monthlyDayStatus(item, "2026-10-02")).toEqual(flag
      ? { tone: "absence", label: "Assenza di timbrature (Avventizio)" }
      : { tone: "danger", label: "Da giustificare" });
    expect(monthlyCellTone(item, 12, "2026-10-02")).toBe(flag ? "absence" : "danger");
  });

  it.each([
    ["2026-10-03", true, "future", "Previsto: Assenza giustificata"],
    ["2026-10-03", false, "future", "Previsto: Assenza giustificata"],
    ["2026-10-02", false, "neutral", "In attesa di dati"],
    ["2026-10-01", false, "warning", "Dati mancanti"],
  ] as const)("keeps date and missing-data precedence (%s, %s)", (date, present, tone, label) => {
    expect(monthlyDayStatus(day({ date, present, avventizioNoPunches: true }), "2026-10-02"))
      .toEqual({ tone, label });
  });

  it.each([undefined, false, true, null, "true", 1])("normalizes only the exact API boolean (%s)", flag => {
    const record = Object.freeze({
      work_date: "2026-10-02", export_ordinary_minutes: 0, export_extra_minutes: 0,
      export_absence_code: "AG", avventizio_no_punches: flag,
    });
    const sheet = buildMonthlySheet("2026-10", [record]);
    expect(sheet.days[1]!.avventizioNoPunches).toBe(flag === true);
    expect(sheet.days[0]).not.toHaveProperty("avventizioNoPunches");
    expect(sheet.totals.slice(0, 9)).toEqual(Array(9).fill(0));
    expect(sheet.workedDays).toBe(0);
    expect(sheet.paidDays).toBe(0);
    expect(sheet.totals[12]).toBe(1);
  });

  it("does not turn a stale flag into AG when another absence code is present", () => {
    const item = day({ avventizioNoPunches: true });
    item.values[12] = "F";
    item.values[8] = 60;
    expect(monthlyDayStatus(item, "2026-10-02"))
      .toEqual({ tone: "absence", label: "Ore + Ferie" });
  });

  it("returns independent status objects across renders", () => {
    const record = day({ avventizioNoPunches: true });
    const first = monthlyDayStatus(record, "2026-10-02");
    first.label = "Temporary consumer label";
    expect(monthlyDayStatus(record, "2026-10-02"))
      .toEqual({ tone: "absence", label: "Assenza di timbrature (Avventizio)" });
  });
});
