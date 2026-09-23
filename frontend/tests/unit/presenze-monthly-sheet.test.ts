import { describe, expect, it } from "vitest";
import { buildMonthlySheet, monthlyNumber, monthlyDuration, monthlyCalendar, monthlyAbsence, monthlyNightReclassification, monthlyBuckets, monthlyCell, monthlyValues, monthlyCounts, monthlyPaidSaturday } from "@/lib/presenze-monthly-sheet";

describe("Giornaliera2", () => {
  it("adds integer minutes, not decimal-looking clock values", () => {
    const report = buildMonthlySheet("2026-08", [3, 4].map(day => ({ work_date: `2026-08-0${day}`, ordinary_minutes: 390, effective_extra_minutes: 40, km_value: 50 })));
    expect(report.totals[8]).toBe(860);
    expect(monthlyCell(report.totals[8]!, 8)).toBe("14:20");
    expect(report.totals[4]).toBe(80);
    expect(report.workedDays).toBe(2);
    expect(report.paidDays).toBe(2);
    expect(report.missingDays).toBe(29);
    expect(report.days[0]!.values[0]).toBeNull();
  });
  it("handles calendars and rejects invalid months and duplicate/outside dates", () => {
    expect(monthlyCalendar("2024-02")).toHaveLength(29);
    expect(monthlyCalendar("2026-02")).toHaveLength(28);
    expect(monthlyCalendar("2026-04")).toHaveLength(30);
    expect(monthlyCalendar("2026-08")[0]!.weekend).toBe(true);
    expect(() => monthlyCalendar("2026-13")).toThrow();
    expect(() => buildMonthlySheet("2026-08", [{ work_date: "2026-09-01" }])).toThrow();
    expect(() => buildMonthlySheet("2026-08", [{ work_date: "2026-08-01" }, { work_date: "2026-08-01" }])).toThrow();
  });
  it("preserves authoritative zero/null, and rejects corrupt numbers", () => {
    expect(monthlyNumber({ a: 0, b: 10 }, "a", "b")).toBe(0);
    expect(monthlyNumber({ a: null, b: 10 }, "a", "b")).toBeNull();
    expect(monthlyNumber({ a: "" }, "a")).toBeNull();
    expect(monthlyNumber({ b: "50" }, "a", "b")).toBe(50);
    expect(monthlyNumber({}, "a")).toBeNull();
    expect(() => monthlyNumber({ a: "NaN" }, "a")).toThrow();
    expect(() => monthlyNumber({ a: -1 }, "a")).toThrow();
    expect(monthlyDuration(65)).toBe("1:05");
    expect(monthlyCell(null, 0)).toBe("—");
    expect(monthlyCell("M", 10)).toBe("M");
    expect(monthlyCell(150, 10)).toBe("2:30");
    expect(monthlyCell(50, 9)).toBe("50");
  });
  it("splits eight categories without double counting night or festive hours", () => {
    const record = { ordinary_minutes: 420, effective_extra_minutes: 80, ordinary_night_minutes: 30, shift_festive_day_minutes: 60, shift_festive_night_minutes: 15, overtime_day_minutes: 20, overtime_festive_minutes: 30, overtime_night_minutes: 10, overtime_festive_night_minutes: 20 };
    expect(monthlyBuckets(record)).toEqual([315, 60, 30, 15, 20, 30, 10, 20]);
    expect(monthlyBuckets({ ordinary_minutes: 420, effective_extra_minutes: 60, special_day: true })).toEqual([0, 420, 0, 0, 0, 60, 0, 0]);
    expect(monthlyBuckets({ ordinary_minutes: 420, effective_extra_minutes: 0, export_special_day: false, special_day: true })[0]).toBe(420);
    expect(() => monthlyBuckets({ ordinary_minutes: 5, ordinary_night_minutes: 10 })).toThrow();
    expect(() => monthlyBuckets({ ordinary_minutes: 420, effective_extra_minutes: 40, overtime_day_minutes: 30 })).toThrow();
    expect(() => monthlyBuckets({ ordinary_night_minutes: 10 })).toThrow();
    expect(monthlyBuckets({ ordinary_minutes: 420, ordinary_night_minutes: 30 })).toEqual([390, 0, 30, 0, 0, 0, 0, 0]);
  });
  it("reclassifies only recognized short early night for operai", () => {
    const record = { contract_kind: "operaio", schedule_code: "OPE0613", detail_punch_rows: [{ entry_time: "05:50", exit_time: "13:00" }] };
    expect(monthlyNightReclassification({}, 10)).toBe(0);
    expect(monthlyNightReclassification(record, 3)).toBe(3);
    expect(monthlyNightReclassification(record, 10)).toBe(10);
    expect(monthlyNightReclassification({ ...record, schedule_code: "OPE0714" }, 10)).toBe(10);
    expect(monthlyNightReclassification({ ...record, schedule_code: "OPE0714", detail_punch_rows: [{ entry_time: "05:50", exit_time: "12:00" }] }, 10)).toBe(0);
    expect(monthlyNightReclassification({ contract_kind: "operaio" }, 10)).toBe(0);
    expect(monthlyNightReclassification({ ...record, detail_punch_rows: undefined }, 10)).toBe(0);
    expect(monthlyNightReclassification({ ...record, detail_punch_rows: [] }, 10)).toBe(0);
    for (const punch of [{}, { entry_time: "bad", exit_time: "13:00" }, { entry_time: "05:50", exit_time: "bad" }, { entry_time: "13:00", exit_time: "05:50" }, { entry_time: "05:50", exit_time: "23:00" }]) {
      expect(monthlyNightReclassification({ ...record, detail_punch_rows: [punch] }, 10)).toBe(0);
    }
    expect(monthlyNightReclassification(record, 20)).toBe(0);
    expect(monthlyNightReclassification({ ...record, detail_punch_rows: [{ entry_time: "06:00", exit_time: "13:00" }] }, 10)).toBe(0);
    expect(monthlyNightReclassification({ ...record, detail_punch_rows: [{ entry_time: "05:00", exit_time: "13:00" }] }, 60)).toBe(0);
  });
  it("shows absences, availability, travel, and missing values", () => {
    expect(monthlyAbsence({ export_absence_code: "AI" })).toBe("AI");
    expect(monthlyAbsence({ request_description: "FERIE - Ferie" })).toBe("F");
    expect(monthlyAbsence({ resolved_absence_cause: "malattia" })).toBe("M");
    expect(monthlyAbsence({ absence_cause: "permesso" })).toBe("P");
    expect(monthlyAbsence({})).toBeNull();
    expect(monthlyValues({})[8]).toBeNull();
    expect(monthlyValues({ ordinary_minutes: null, effective_extra_minutes: 60 })[8]).toBe(60);
    expect(monthlyValues({ ordinary_minutes: 0, schedule_code: "DOM", contract_kind: "operaio" })[12]).toBe("RS");
    expect(monthlyValues({ ordinary_minutes: 420, schedule_code: "DOM", contract_kind: "operaio" })[12]).toBeNull();
    expect(monthlyValues({ reperibilita_unit: "days", reperibilita_quantity: 1, trasferta_montano: true }).slice(10, 12)).toEqual(["M", 1]);
    expect(monthlyValues({ reperibilita_unit: "none", reperibilita_quantity: 1 })[11]).toBe(0);
    expect(monthlyValues({ reperibilita_giornaliera: true })[11]).toBe(1);
    const report = buildMonthlySheet("2026-08", [
      { work_date: "2026-08-01", ordinary_minutes: 0, export_absence_code: "F", justified_minutes: 420 },
      { work_date: "2026-08-02", ordinary_minutes: 0, schedule_code: "DOM", contract_kind: "operaio" },
      { work_date: "2026-08-03", ordinary_minutes: 100, export_absence_code: "P" },
    ]);
    expect(report.totals[12]).toBe(1);
    expect(report.paidDays).toBe(2);
    expect(report.totals[9]).toBeNull();
    expect(buildMonthlySheet("2026-08", [{ work_date: "2026-08-01", trasferta_minutes: 60 }, { work_date: "2026-08-02", trasferta_montano: true }]).totals[10]).toBe(60);
  });
  it("credits the sixth paid day only after five ordinary days totaling 38 hours", () => {
    const records = Array.from({ length: 6 }, (_, i) => ({ work_date: `2026-08-0${i + 3}`, ordinary_minutes: i === 5 ? 0 : 456, contract_kind: "operaio" }));
    expect(buildMonthlySheet("2026-08", records).paidDays).toBe(6);
    expect(buildMonthlySheet("2026-08", records.slice(1)).paidDays).toBe(4);
    expect(buildMonthlySheet("2026-08", records.map(r => ({ ...r, ordinary_minutes: 100 }))).paidDays).toBe(6);
    expect(buildMonthlySheet("2026-08", records.map(r => ({ ...r, contract_kind: "impiegato" }))).paidDays).toBe(5);
    expect(buildMonthlySheet("2026-08", records.map(r => ({ ...r, ordinary_minutes: r.ordinary_minutes / 2 }))).paidDays).toBe(5);
    const missing = records.map(r => ({ ...r, ordinary_minutes: null }));
    expect(buildMonthlySheet("2026-08", missing).paidDays).toBe(0);
    expect(monthlyCounts([], [])).toEqual({ workedDays: 0, paidDays: 0 });
    expect(monthlyPaidSaturday(monthlyCalendar("2026-08")[0]!, [])).toBe(false);
  });
});
