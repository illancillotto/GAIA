import { describe, expect, test } from "vitest";

import {
  countAnomaliesInRecords,
  currentMonthValue,
  monthBounds,
  monthLabel,
  previousMonthValue,
  recentMonths,
  recordHasAnomaly,
  shouldAutoLoadPreviousMonth,
  summarizeMonthsWithAnomalies,
} from "@/lib/presenze-anomaly-months";
import type { PresenzeDailyRecord } from "@/types/api";

function makeRecord(anomalies: Array<Record<string, string>>, detailError: string | null = null): PresenzeDailyRecord {
  return {
    id: "record-1",
    collaborator_id: "collab-1",
    owner_user_id: 1,
    application_user_id: null,
    work_date: "2026-05-16",
    schedule_code: null,
    teo_minutes: null,
    ordinary_minutes: null,
    absence_minutes: null,
    justified_minutes: null,
    maggiorazione_minutes: null,
    mpe_minutes: null,
    straordinario_minutes: null,
    km_value: null,
    trasferta_minutes: null,
    trasferta_montano: false,
    reperibilita_unit: "none",
    reperibilita_quantity: null,
    override_straordinario_minutes: null,
    override_mpe_minutes: null,
    manual_note: null,
    request_type: null,
    request_description: null,
    request_status: null,
    request_authorized_by: null,
    resolved_absence_cause: null,
    validation_status: "pending",
    validated_by_user_id: null,
    validated_at: null,
    validation_note: null,
    effective_straordinario_minutes: null,
    effective_mpe_minutes: null,
    effective_extra_minutes: null,
    operational_status: "ok",
    operational_formula_code: null,
    operational_expected_minutes: null,
    operational_worked_minutes: null,
    operational_missing_minutes: 0,
    operational_mpe_minutes: 0,
    operational_notes: [],
    night_minutes: 0,
    festive_minutes: 0,
    festive_night_minutes: 0,
    ordinary_night_minutes: 0,
    overtime_day_minutes: 0,
    overtime_night_minutes: 0,
    overtime_festive_minutes: 0,
    overtime_festive_night_minutes: 0,
    shift_festive_day_minutes: 0,
    shift_night_minutes: 0,
    shift_festive_night_minutes: 0,
    monthly_night_shift_count: 0,
    ordinary_night_bonus_threshold_met: false,
    ordinary_night_bonus_rate: null,
    stato: null,
    evidenze: null,
    raw_weekday: null,
    detail_title: null,
    detail_status: null,
    detail_programmed_schedule: null,
    detail_effective_schedule: null,
    detail_time_slots: null,
    detail_schedule_type: null,
    detail_theoretical_hours: null,
    detail_absence_hours: null,
    detail_day_summary: {},
    detail_day_totals: {},
    detail_requests: [],
    detail_anomalies: anomalies,
    detail_punch_rows: [],
    detail_text: null,
    detail_error: detailError,
    special_day: false,
    holiday_kind: null,
    grants_recovery_day: false,
    recovery_day_credit: 0,
    uses_recovery_day: false,
    recovery_day_debit: 0,
    recovery_day_balance_delta: 0,
    raw_payload_json: {},
    source_job_id: null,
    created_at: "2026-06-04T09:00:00Z",
    updated_at: "2026-06-04T09:00:00Z",
    punches: [],
  };
}

describe("presenze anomaly months", () => {
  test("currentMonthValue and previousMonthValue navigate months", () => {
    expect(currentMonthValue(new Date(2026, 5, 4))).toBe("2026-06");
    expect(previousMonthValue("2026-06")).toBe("2026-05");
    expect(previousMonthValue("2026-01")).toBe("2025-12");
  });

  test("monthBounds returns first and last day", () => {
    expect(monthBounds("2026-02")).toEqual({ start: "2026-02-01", end: "2026-02-28" });
  });

  test("recordHasAnomaly detects anomalies and errors", () => {
    expect(recordHasAnomaly(makeRecord([]))).toBe(false);
    expect(recordHasAnomaly(makeRecord([{ tipo: "mancanza" }]))).toBe(true);
    expect(recordHasAnomaly(makeRecord([], "Errore parsing"))).toBe(true);
    expect(countAnomaliesInRecords([makeRecord([]), makeRecord([{ tipo: "x" }])])).toBe(1);
  });

  test("shouldAutoLoadPreviousMonth only on empty calendar month", () => {
    expect(
      shouldAutoLoadPreviousMonth({
        selectedMonth: "2026-06",
        calendarMonth: "2026-06",
        anomalyCount: 0,
        alreadyApplied: false,
      }),
    ).toBe(true);
    expect(
      shouldAutoLoadPreviousMonth({
        selectedMonth: "2026-06",
        calendarMonth: "2026-06",
        anomalyCount: 2,
        alreadyApplied: false,
      }),
    ).toBe(false);
    expect(
      shouldAutoLoadPreviousMonth({
        selectedMonth: "2026-05",
        calendarMonth: "2026-06",
        anomalyCount: 0,
        alreadyApplied: false,
      }),
    ).toBe(false);
  });

  test("summarizeMonthsWithAnomalies keeps only positive counts", () => {
    expect(
      summarizeMonthsWithAnomalies([
        { month: "2026-04", count: 0 },
        { month: "2026-05", count: 3 },
        { month: "2026-06", count: 1 },
      ]),
    ).toEqual([
      { month: "2026-06", count: 1 },
      { month: "2026-05", count: 3 },
    ]);
  });

  test("recentMonths walks backwards from anchor", () => {
    expect(recentMonths(3, "2026-03")).toEqual(["2026-03", "2026-02", "2026-01"]);
  });

  test("monthLabel uses Italian locale", () => {
    expect(monthLabel("2026-05")).toMatch(/maggio/i);
  });
});
