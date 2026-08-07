import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import {
  buildPresenzeMonthCalendar,
  calendarCellClass,
  detailTone,
  formatIsoDate,
  PresenzeMonthlyCalendar,
} from "@/app/me/presenze-calendar";
import type { PresenzeDailyRecord } from "@/types/api";

function dailyRecord(overrides: Partial<PresenzeDailyRecord>): PresenzeDailyRecord {
  return {
    id: overrides.id ?? "record-1",
    collaborator_id: "collab-1",
    owner_user_id: null,
    application_user_id: 1,
    work_date: overrides.work_date ?? "2026-08-05",
    schedule_code: overrides.schedule_code ?? null,
    teo_minutes: null,
    ordinary_minutes: overrides.ordinary_minutes ?? null,
    absence_minutes: overrides.absence_minutes ?? null,
    justified_minutes: null,
    maggiorazione_minutes: null,
    mpe_minutes: null,
    straordinario_minutes: null,
    km_value: overrides.km_value ?? null,
    trasferta_minutes: null,
    trasferta_montano: false,
    reperibilita_unit: "none",
    reperibilita_quantity: null,
    override_straordinario_minutes: null,
    override_mpe_minutes: null,
    manual_note: null,
    request_type: null,
    request_description: overrides.request_description ?? null,
    request_status: null,
    request_authorized_by: null,
    resolved_absence_cause: overrides.resolved_absence_cause ?? null,
    validation_status: "pending",
    validated_by_user_id: null,
    validated_at: null,
    validation_note: null,
    effective_straordinario_minutes: null,
    effective_mpe_minutes: null,
    effective_extra_minutes: overrides.effective_extra_minutes ?? null,
    operational_status: "unknown",
    operational_formula_code: null,
    operational_expected_minutes: null,
    operational_worked_minutes: overrides.operational_worked_minutes ?? null,
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
    stato: overrides.stato ?? "Giornata regolare",
    evidenze: null,
    raw_weekday: null,
    detail_title: null,
    detail_status: overrides.detail_status ?? null,
    detail_programmed_schedule: overrides.detail_programmed_schedule ?? null,
    detail_effective_schedule: null,
    detail_time_slots: null,
    detail_schedule_type: null,
    detail_theoretical_hours: null,
    detail_absence_hours: null,
    detail_day_summary: {},
    detail_day_totals: {},
    detail_requests: [],
    detail_anomalies: overrides.detail_anomalies ?? [],
    detail_punch_rows: [],
    detail_text: null,
    detail_error: null,
    special_day: overrides.special_day ?? null,
    holiday_kind: null,
    grants_recovery_day: false,
    recovery_day_credit: 0,
    uses_recovery_day: false,
    recovery_day_debit: 0,
    recovery_day_balance_delta: 0,
    raw_payload_json: {},
    source_job_id: null,
    created_at: "2026-08-06T08:00:00Z",
    updated_at: "2026-08-06T08:00:00Z",
    punches: overrides.punches ?? [],
    ...overrides,
  };
}

describe("PresenzeMonthlyCalendar", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  test("builds a Monday-first month grid with previous-month fillers and today marker", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-08-05T10:00:00Z"));

    expect(buildPresenzeMonthCalendar("2026-08-01", []).find((day) => day.date === "2026-08-05")).toMatchObject({ isToday: true });

    const days = buildPresenzeMonthCalendar("2026-08-01", [dailyRecord({ id: "compiled", work_date: "2026-08-05" })], "2026-08-05");

    expect(days[0]).toMatchObject({ date: "2026-07-27", dayNumber: "27", isCurrentMonth: false });
    expect(days.at(-1)).toMatchObject({ date: "2026-09-06", dayNumber: "6", isCurrentMonth: false });
    expect(days.find((day) => day.date === "2026-08-05")).toMatchObject({ isToday: true, record: expect.objectContaining({ id: "compiled" }) });
  });

  test("formats dates and resolves cell tones/classes for the supported states", () => {
    expect(formatIsoDate(new Date("2026-08-05T12:00:00"))).toBe("2026-08-05");
    expect(detailTone(dailyRecord({ work_date: "2026-08-02" }))).toBe("info");
    expect(detailTone(dailyRecord({ detail_anomalies: [{ code: "A1" }] }))).toBe("warning");
    expect(detailTone(dailyRecord({ special_day: true }))).toBe("warning");
    expect(detailTone(dailyRecord({ effective_extra_minutes: 60 }))).toBe("success");
    expect(detailTone(dailyRecord({ work_date: "2026-08-02", operational_worked_minutes: 1 }))).toBe("neutral");
    expect(detailTone(dailyRecord({ work_date: "2026-08-02", ordinary_minutes: 1 }))).toBe("neutral");
    expect(detailTone(dailyRecord({ work_date: "2026-08-02", effective_extra_minutes: 1 }))).toBe("success");
    expect(detailTone(dailyRecord({ work_date: "2026-08-02", punches: [{ id: "p", daily_record_id: "r", sequence: 1, entry_time: "08:00", exit_time: null, terminal_label: null }] }))).toBe("neutral");
    expect(detailTone(dailyRecord({ work_date: "2026-08-02", punches: [{ id: "p-exit", daily_record_id: "r", sequence: 1, entry_time: null, exit_time: "12:00", terminal_label: null }] }))).toBe("neutral");
    expect(detailTone({ ...dailyRecord({ special_day: true }), detail_anomalies: undefined as unknown as PresenzeDailyRecord["detail_anomalies"] })).toBe("warning");

    expect(calendarCellClass(null, true, false)).toContain("border-dashed");
    expect(calendarCellClass(null, false, true)).toContain("ring-2");
    expect(calendarCellClass(dailyRecord({ detail_anomalies: [{ code: "A1" }] }), true, false)).toContain("border-amber-200");
    expect(calendarCellClass(dailyRecord({ effective_extra_minutes: 60 }), true, false)).toContain("border-emerald-200");
    expect(calendarCellClass(dailyRecord({ work_date: "2026-08-02" }), true, false)).toContain("border-blue-100");
    expect(calendarCellClass(dailyRecord({}), true, true)).toContain("shadow-sm");
  });

  test("renders daily cells and opens the selected record", () => {
    const onOpenDailyRecord = vi.fn();
    render(
      <PresenzeMonthlyCalendar
        monthStart="2026-08-01"
        today="2026-08-05"
        onOpenDailyRecord={onOpenDailyRecord}
        records={[
          dailyRecord({
            id: "previous-month",
            work_date: "2026-07-31",
            detail_status: null,
            stato: null,
            schedule_code: "FLESS",
            ordinary_minutes: 120,
          }),
          dailyRecord({
            id: "compiled",
            work_date: "2026-08-05",
            detail_status: "Regolare",
            detail_programmed_schedule: "08:00-15:12",
            ordinary_minutes: 420,
            absence_minutes: 30,
            effective_extra_minutes: 60,
            km_value: 12,
            request_description: "Ferie approvate",
            detail_anomalies: [{ code: "A1" }],
            punches: [
              { id: "p1", daily_record_id: "compiled", sequence: 1, entry_time: "08:00", exit_time: "12:00", terminal_label: null },
              { id: "p2", daily_record_id: "compiled", sequence: 2, entry_time: "13:00", exit_time: "16:00", terminal_label: null },
              { id: "p3", daily_record_id: "compiled", sequence: 3, entry_time: null, exit_time: null, terminal_label: null },
            ],
          }),
          dailyRecord({
            id: "absence",
            work_date: "2026-08-06",
            stato: null,
            resolved_absence_cause: "permesso_retribuito",
            detail_anomalies: undefined as unknown as PresenzeDailyRecord["detail_anomalies"],
            punches: [{ id: "p4", daily_record_id: "absence", sequence: 1, entry_time: null, exit_time: null, terminal_label: null }],
          }),
          dailyRecord({
            id: "single-punch",
            work_date: "2026-08-07",
            punches: [{ id: "p5", daily_record_id: "single-punch", sequence: 1, entry_time: "09:00", exit_time: "10:00", terminal_label: null }],
          }),
          dailyRecord({
            id: "anomaly-only",
            work_date: "2026-08-10",
            detail_anomalies: [{ code: "A2" }],
          }),
        ]}
      />,
    );

    expect(screen.getByText("Lun")).toBeInTheDocument();
    expect(screen.getAllByText("riposo").length).toBeGreaterThan(0);
    expect(screen.getByText("FLESS")).toBeInTheDocument();
    expect(screen.getAllByText("Regolare").length).toBeGreaterThan(0);
    expect(screen.getByText("Ord 7.0 h")).toBeInTheDocument();
    expect(screen.getByText("Ass 0.5 h")).toBeInTheDocument();
    expect(screen.getByText("Extra 1.0 h")).toBeInTheDocument();
    expect(screen.getByText("KM 12")).toBeInTheDocument();
    expect(screen.getByText("Ferie approvate")).toBeInTheDocument();
    expect(screen.getAllByText("1 anomalie").length).toBe(2);
    expect(screen.getByText("+1")).toBeInTheDocument();
    expect(screen.getByText("permesso retribuito")).toBeInTheDocument();
    expect(screen.getByText("--:-----:--")).toBeInTheDocument();
    expect(screen.getByText("09:00-10:00")).toBeInTheDocument();

    const previousMonthButton = screen.getByRole("button", { name: "Apri dettaglio presenze ven 31/07/2026" });
    expect(within(previousMonthButton).getByText("Regolare")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Apri dettaglio presenze mer 05/08/2026" }));

    expect(onOpenDailyRecord).toHaveBeenCalledWith("compiled");
  });
});
