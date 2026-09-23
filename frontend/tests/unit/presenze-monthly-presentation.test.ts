import { describe, expect, it } from "vitest";
import { monthlyAbsenceLabel, monthlyDayStatus, monthlyCellTone, monthlyDisplayCell } from "@/lib/presenze-monthly-presentation";
import { monthlyCell, type MonthlyDay } from "@/lib/presenze-monthly-sheet";
const today = "2026-09-23";
function day(total: number | null = 0, code: string | null = null): MonthlyDay {
  const values = Array(13).fill(0); values[8] = total; values[12] = code;
  return { date: "2026-09-01", weekend: false, present: true, values };
}
describe("monthly presentation", () => {
  it("uses words for known and unknown absence codes without treating leave as an error", () => {
    expect(monthlyAbsenceLabel("F")).toBe("Ferie");
    expect(monthlyAbsenceLabel("NEW")).toBe("Causale NEW");
    for (const [record, tone, label] of [
      [day(420), "work", "Ore registrate"], [day(0, "F"), "absence", "Ferie"],
      [day(60, "P"), "absence", "Ore + Permesso"], [day(0, "RS"), "neutral", "Riposo"],
      [day(20, "AG"), "danger", "Da giustificare"], [day(null), "warning", "Ore non disponibili"],
      [day(), "neutral", "Nessuna ora registrata"],
      [{ ...day(), present: false }, "warning", "Dati mancanti"],
      [{ ...day(), present: false, date: today }, "neutral", "In attesa di dati"],
      [{ ...day(), date: "2026-09-24" }, "future", "Da venire"],
      [{ ...day(0, "F"), date: "2026-09-24" }, "future", "Previsto: Ferie"],
    ] as const) expect(monthlyDayStatus(record, today)).toEqual({ tone, label });
  });
  it("highlights meaningful values and does not mark weekends or missing values as absence", () => {
    const record = day(420, "F"); record.values[4] = 60;
    expect(monthlyCellTone(record, 8, today)).toBe("work");
    expect(monthlyCellTone(record, 4, today)).toBe("extra");
    expect(monthlyCellTone(record, 12, today)).toBe("absence");
    expect(monthlyCellTone(record, 0, today)).toBe("quiet");
    expect(monthlyCellTone({ ...record, weekend: true }, 0, today)).toBe("weekend");
    expect(monthlyCellTone({ ...record, present: false }, 0, today)).toBe("missing");
    expect(monthlyCellTone({ ...record, date: "2026-09-24" }, 8, today)).toBe("future");
    expect(monthlyCellTone(day(), 12, today)).toBe("quiet");
    record.values[10] = "M"; expect(monthlyCellTone(record, 10, today)).toBe("quiet");
    record.values[9] = 10; expect(monthlyCellTone(record, 9, today)).toBe("work");
  });
  it("expands codes without changing quantities, zeroes or unavailable values", () => {
    expect(monthlyDisplayCell("F", 12)).toBe("Ferie");
    expect(monthlyDisplayCell("M", 10)).toBe("Montana");
    for (let row = 0; row < 13; row++) {
      for (const value of [null, 0, 90, "CUSTOM"]) {
        if (row === 12 && typeof value === "string") continue;
        expect(monthlyDisplayCell(value, row)).toBe(monthlyCell(value, row));
      }
    }
  });
});
