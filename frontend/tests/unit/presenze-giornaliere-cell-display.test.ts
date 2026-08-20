import { describe, expect, it } from "vitest";

import {
  CELL_TONE,
  MODAL_ROW_TONE,
  absenceSummaryMinutes,
  authorizedPunchDirection,
  authorizedPunchLabel,
  classifyDailyMatrixCell,
  dailyMatrixCellPrimaryLabel,
  dailyMatrixCellSecondaryLabel,
  dailyMatrixCellTooltipLabel,
  effectiveExtraMinutes,
  effectiveOrdinaryMinutes,
  formatHoursCompact,
  formatRequestDescription,
  hasWorkedTime,
  isUnworkedHolidayRecord,
} from "@/lib/presenze-giornaliere-cell-display";
import type { PresenzeDailyRecord } from "@/types/api";

function record(overrides: Partial<PresenzeDailyRecord> = {}): PresenzeDailyRecord {
  return {
    id: "record-1",
    collaborator_id: "collaborator-1",
    work_date: "2026-08-15",
    stato: "",
    source: "manual",
    ordinary_minutes: null,
    extra_minutes: null,
    absence_minutes: null,
    justified_minutes: null,
    teo_minutes: null,
    start_time: null,
    end_time: null,
    motivation: null,
    raw_payload_json: null,
    source_frame_url: null,
    source_hash: null,
    created_at: "2026-08-15T00:00:00Z",
    updated_at: "2026-08-15T00:00:00Z",
    validation_status: null,
    validation_note: null,
    validated_by_user_id: null,
    validated_at: null,
    request_type: null,
    request_description: null,
    request_status: null,
    request_authorized_by: null,
    resolved_absence_cause: null,
    detail_status: null,
    detail_error: null,
    detail_programmed_schedule: null,
    detail_actual_schedule: null,
    detail_summary: [],
    detail_totals: [],
    detail_requests: [],
    detail_anomalies: [],
    detail_punch_rows: [],
    punches: [],
    event_summaries: [],
    ordinary_duration_minutes: null,
    extra_duration_minutes: null,
    operational_status: "unknown",
    operational_status_reason: null,
    operational_expected_minutes: null,
    operational_worked_minutes: null,
    operational_missing_minutes: null,
    operational_extra_minutes: null,
    operational_mpe_minutes: null,
    operational_notes: [],
    operational_formula_code: null,
    effective_extra_minutes: null,
    effective_straordinario_minutes: null,
    effective_mpe_minutes: null,
    straordinario_minutes: null,
    mpe_minutes: null,
    km_value: null,
    trasferta_minutes: null,
    trasferta_montano: false,
    reperibilita_unit: "none",
    reperibilita_quantity: null,
    schedule_code: null,
    special_day: null,
    grants_recovery_day: false,
    recovery_day_credit: null,
    uses_recovery_day: false,
    recovery_day_debit: null,
    recovery_day_balance_delta: null,
    ...overrides,
  } as PresenzeDailyRecord;
}

const monday = { iso: "2026-08-17", day: 17, weekday: "lun", isWeekend: false, isToday: false };
const sunday = { iso: "2026-08-16", day: 16, weekday: "DOM", isWeekend: true, isToday: false };

describe("Presenze daily matrix cell display", () => {
  it("classifies operational and domain states in the existing precedence order", () => {
    expect(classifyDailyMatrixCell(record({ operational_status: "blocking", special_day: "Ferragosto" }))).toBe("anomaly");
    expect(classifyDailyMatrixCell(record({ operational_status: "in_analysis", resolved_absence_cause: "ferie" }))).toBe("analysis");
    expect(classifyDailyMatrixCell(record({ operational_status: "unknown", detail_anomalies: [{ col_1: "anomalia" }] }))).toBe("anomaly");
    expect(classifyDailyMatrixCell(record({ special_day: "Ferragosto", resolved_absence_cause: "ferie" }))).toBe("special");
    expect(classifyDailyMatrixCell(record({ resolved_absence_cause: "ferie" }))).toBe("ferie");
    expect(classifyDailyMatrixCell(record({ resolved_absence_cause: "permesso" }))).toBe("permesso");
    expect(classifyDailyMatrixCell(record({ resolved_absence_cause: "malattia" }))).toBe("malattia");
    expect(classifyDailyMatrixCell(record({ ordinary_minutes: 420, absence_minutes: 60 }))).toBe("worked");
    expect(classifyDailyMatrixCell(record({ absence_minutes: 120 }))).toBe("absence");
    expect(classifyDailyMatrixCell(record())).toBe("rest");
  });

  it("preserves primary labels, including holiday-without-work Fest", () => {
    expect(dailyMatrixCellPrimaryLabel(record({ special_day: "Ferragosto" }), "special", monday)).toBe("Fest");
    expect(dailyMatrixCellPrimaryLabel(record({ special_day: "Domenica", operational_worked_minutes: 1, teo_minutes: 0 }), "special", sunday)).toBe("🌿");
    expect(dailyMatrixCellPrimaryLabel(record({ ordinary_minutes: 450 }), "worked", monday)).toBe("7.5");
    expect(dailyMatrixCellPrimaryLabel(record({ resolved_absence_cause: "ferie" }), "ferie", monday)).toBe("Fer");
    expect(dailyMatrixCellPrimaryLabel(record({ resolved_absence_cause: "permesso" }), "permesso", monday)).toBe("Perm");
    expect(dailyMatrixCellPrimaryLabel(record({ resolved_absence_cause: "malattia" }), "malattia", monday)).toBe("Mal");
    expect(dailyMatrixCellPrimaryLabel(record({ resolved_absence_cause: "ferie", operational_status: "in_analysis" }), "analysis", monday)).toBe("Fer");
    expect(dailyMatrixCellPrimaryLabel(record({ request_description: "Cambio turno" }), "analysis", monday)).toBe("Rich");
    expect(dailyMatrixCellPrimaryLabel(record({ detail_status: "Anomalia" }), "anomaly", monday)).toBe("Anom");
    expect(dailyMatrixCellPrimaryLabel(record({ detail_status: "Permesso approvato" }), "absence", monday)).toBe("Perm");
    expect(dailyMatrixCellPrimaryLabel(record({ detail_status: "abcde" }), "absence", monday)).toBe("abcd");
    expect(dailyMatrixCellPrimaryLabel(record(), "rest", monday)).toBe("·");
  });

  it("preserves secondary labels for extra, trasferta, KM, requests, absences and anomalies", () => {
    expect(dailyMatrixCellSecondaryLabel(record({ effective_extra_minutes: 90 }), "worked")).toBe("+1.5h");
    expect(dailyMatrixCellSecondaryLabel(record({ trasferta_minutes: 120 }), "worked")).toBe("T 2h");
    expect(dailyMatrixCellSecondaryLabel(record({ km_value: 14 }), "worked")).toBe("KM 14");
    expect(dailyMatrixCellSecondaryLabel(record({ detail_requests: [{ tipo: "ACC" }] }), "worked")).toBe("Rich.");
    expect(dailyMatrixCellSecondaryLabel(record({ absence_minutes: 240 }), "ferie")).toBe("4h");
    expect(dailyMatrixCellSecondaryLabel(record({ operational_missing_minutes: 60 }), "anomaly")).toBe("-1h");
    expect(dailyMatrixCellSecondaryLabel(record({ justified_minutes: 120 }), "analysis")).toBe("2h");
    expect(dailyMatrixCellSecondaryLabel(record({ special_day: "Ferragosto" }), "special")).toBeNull();
    expect(dailyMatrixCellSecondaryLabel(record(), "rest")).toBeNull();
  });

  it("shows authorized punch validation before other worked secondary labels", () => {
    expect(
      dailyMatrixCellSecondaryLabel(
        record({
          request_status: "ACC",
          request_description: "Autorizzata timbratura E",
          request_authorized_by: "HR",
          effective_extra_minutes: 60,
        }),
        "worked",
      ),
    ).toBe("Valid.");
  });

  it("covers pure helper fallbacks used by the matrix and detail modal", () => {
    expect(CELL_TONE.anomaly).toContain("bg-red-50");
    expect(MODAL_ROW_TONE.rest).toContain("bg-gray-50");
    expect(formatHoursCompact(null)).toBe("0");
    expect(formatHoursCompact(30)).toBe("0.5");
    expect(formatHoursCompact(120)).toBe("2");
    expect(effectiveExtraMinutes(record({ effective_straordinario_minutes: 30, effective_mpe_minutes: 45 }))).toBe(75);
    expect(effectiveExtraMinutes(record({ straordinario_minutes: 30, mpe_minutes: 15 }))).toBe(45);
    expect(effectiveOrdinaryMinutes(record({ operational_formula_code: "F", operational_expected_minutes: 420, operational_worked_minutes: 480 }))).toBe(420);
    expect(effectiveOrdinaryMinutes(record({ ordinary_minutes: 390 }))).toBe(390);
    expect(hasWorkedTime(record({ punches: [{ entry_time: "08:00", exit_time: null, terminal_label: null }] }))).toBe(true);
    expect(hasWorkedTime(record({ punches: [{ entry_time: null, exit_time: "17:00", terminal_label: null }] }))).toBe(true);
    expect(hasWorkedTime(record({ ordinary_minutes: 60 }))).toBe(true);
    expect(hasWorkedTime(record())).toBe(false);
    expect(isUnworkedHolidayRecord(record({ special_day: "Ferragosto" }))).toBe(true);
    expect(absenceSummaryMinutes(record({ justified_minutes: 90 }))).toBe(90);
    expect(formatRequestDescription(null)).toBe("—");
    expect(formatRequestDescription("ACC - Timbratura E autorizzata")).toBe("Timbratura E autorizzata");
    expect(formatRequestDescription("ACC - ")).toBe("ACC - ");
    expect(formatRequestDescription("Richiesta semplice")).toBe("Richiesta semplice");
    expect(authorizedPunchDirection(record({ request_status: "ACC", request_description: "Timbratura U" }))).toBe("U");
    expect(authorizedPunchDirection(record({ request_status: "ACC", request_description: "Generica" }))).toBeNull();
    expect(authorizedPunchDirection(record({ request_status: "REQ", request_description: "Timbratura E" }))).toBeNull();
    expect(authorizedPunchLabel(record({ request_status: "ACC", request_description: "Timbratura U" }))).toBe("Timbratura di uscita autorizzata");
    expect(dailyMatrixCellTooltipLabel(record({ operational_status: "ok" }))).toBe("GAIA: giornata quadrata");
    expect(dailyMatrixCellTooltipLabel(record({ operational_status: "ok", request_status: "ACC", request_description: "Timbratura E" }))).toBe("GAIA: giornata quadrata · Timbratura di entrata autorizzata");
    expect(dailyMatrixCellTooltipLabel(record({ operational_status: "in_analysis", detail_status: "Da verificare" }))).toBe("GAIA: in analisi · INAZ: Da verificare");
    expect(dailyMatrixCellTooltipLabel(record({ operational_status: "blocking", operational_missing_minutes: 90, detail_status: "Anomalia" }))).toBe("GAIA: da sistemare · mancanti 1.50 h · INAZ: Anomalia");
    expect(dailyMatrixCellTooltipLabel(record({ operational_status: "blocking" }))).toBe("GAIA: da sistemare · INAZ: ");
    expect(dailyMatrixCellTooltipLabel(record({ stato: null as unknown as string }))).toBe("n/d");
    expect(dailyMatrixCellTooltipLabel(record({ detail_status: "Regolare" }))).toBe("Regolare");
  });

  it("covers remaining primary label status and secondary fallback branches", () => {
    expect(dailyMatrixCellPrimaryLabel(record({ resolved_absence_cause: "permesso" }), "analysis", monday)).toBe("Perm");
    expect(dailyMatrixCellPrimaryLabel(record({ resolved_absence_cause: "malattia" }), "analysis", monday)).toBe("Mal");
    expect(dailyMatrixCellPrimaryLabel(record({ detail_requests: [{ tipo: "REQ" }] }), "analysis", monday)).toBe("Rich");
    expect(dailyMatrixCellPrimaryLabel(record(), "analysis", monday)).toBe("Anom");
    expect(dailyMatrixCellPrimaryLabel(record({ detail_status: "Ferie godute" }), "absence", monday)).toBe("Fer");
    expect(dailyMatrixCellPrimaryLabel(record({ detail_status: "Malattia" }), "absence", monday)).toBe("Mal");
    expect(dailyMatrixCellPrimaryLabel(record({ detail_status: "Richiesta" }), "absence", monday)).toBe("Rich");
    expect(dailyMatrixCellPrimaryLabel(record({ detail_status: "Giornata regolare", justified_minutes: 60 }), "absence", monday)).toBe("1");
    expect(dailyMatrixCellPrimaryLabel(record({ detail_status: "abc" }), "absence", monday)).toBe("abc");
    expect(dailyMatrixCellPrimaryLabel(record({ detail_status: null, stato: "Permesso" } as Partial<PresenzeDailyRecord>), "absence", monday)).toBe("Perm");
    expect(dailyMatrixCellPrimaryLabel(record({ detail_status: null, stato: null } as Partial<PresenzeDailyRecord>), "absence", monday)).toBe("0");
    expect(dailyMatrixCellPrimaryLabel(record(), "anomaly", monday)).toBe("Anom");
    expect(dailyMatrixCellSecondaryLabel(record({ detail_requests: [{ tipo: "REQ" }] }), "analysis")).toBe("Rich.");
    expect(dailyMatrixCellSecondaryLabel(record(), "worked")).toBeNull();
    expect(dailyMatrixCellSecondaryLabel(record(), "analysis")).toBeNull();
    expect(dailyMatrixCellSecondaryLabel(record(), "absence")).toBeNull();
  });
});
