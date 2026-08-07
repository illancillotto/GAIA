import { describe, expect, test, vi } from "vitest";

import {
  currentMonthBounds,
  firstDetailPreview,
  formatAbsenceCause,
  formatContractKind,
  formatDetailEntries,
  formatHours,
  formatMonthRangeLabel,
  formatOperaiGroup,
  formatRequestDescription,
  formatStandardDailyMinutes,
  inferGaiaProfileCode,
  isAssignableGaiaTemplate,
  monthBoundsFromDate,
  operaiGroupBadgeVariant,
  recoveryBadgeLabel,
  requestBadgeLabel,
  sectionSummaryLabel,
  shiftMonthBounds,
  templateDisplayTitle,
  uniqueTemplateInazCodes,
} from "@/lib/presenze-collaboratore-detail-helpers";
import type { PresenzeCollaborator, PresenzeDailyRecord, PresenzeScheduleTemplate } from "@/types/api";

function dailyRecord(overrides: Partial<PresenzeDailyRecord> = {}): PresenzeDailyRecord {
  return {
    id: "record-1",
    collaborator_id: "collab-1",
    owner_user_id: null,
    application_user_id: 1,
    work_date: "2026-08-01",
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
    ...overrides,
  } as PresenzeDailyRecord;
}

describe("presenze collaborator detail helpers", () => {
  test("month helpers compute expected bounds and labels", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-15T12:00:00Z"));

    expect(currentMonthBounds()).toEqual({ start: "2026-08-01", end: "2026-08-31" });
    expect(monthBoundsFromDate("2026-02-10")).toEqual({ start: "2026-02-01", end: "2026-02-28" });
    expect(shiftMonthBounds("2026-08-01", -1)).toEqual({ start: "2026-07-01", end: "2026-07-31" });
    expect(formatMonthRangeLabel("2026-08-01")).toMatch(/agosto 2026/i);

    vi.useRealTimers();
  });

  test("formatters handle null and known values", () => {
    expect(formatHours(null)).toBe("—");
    expect(formatHours(90)).toBe("1.50 h");
    expect(formatStandardDailyMinutes(null)).toBe("—");
    expect(formatStandardDailyMinutes(485)).toBe("8:05");
    expect(formatContractKind("operaio")).toBe("Operaio");
    expect(formatContractKind("custom" as PresenzeCollaborator["contract_kind"])).toBe("custom");
    expect(formatContractKind(null)).toBe("—");
    expect(formatOperaiGroup("agrario")).toBe("Agrario");
    expect(formatOperaiGroup("catasto_magazzino")).toBe("Catasto / magazzino");
    expect(formatOperaiGroup(null)).toBe("Non impostato");
    expect(operaiGroupBadgeVariant("agrario")).toBe("success");
    expect(operaiGroupBadgeVariant("catasto_magazzino")).toBe("info");
    expect(operaiGroupBadgeVariant(undefined)).toBe("neutral");
  });

  test("template helpers expose assignability and labels", () => {
    const template = {
      id: 1,
      code: "OPE0613",
      label: "Template bloccato",
      rules: [{ ordinary_label: "LUN" }, { ordinary_label: "LUN" }],
    } as PresenzeScheduleTemplate;

    expect(isAssignableGaiaTemplate(template)).toBe(false);
    expect(templateDisplayTitle(template)).toBe("Template bloccato");
    expect(templateDisplayTitle({ id: 2, code: "CODE2", label: "", rules: [] } as PresenzeScheduleTemplate)).toBe("CODE2");
    expect(templateDisplayTitle({ id: 3, code: "", label: "", rules: [] } as PresenzeScheduleTemplate)).toBe("Template #3");
    expect(templateDisplayTitle(null)).toBe("Template non disponibile");
    expect(uniqueTemplateInazCodes(null)).toEqual([]);
    expect(uniqueTemplateInazCodes(undefined)).toEqual([]);
    expect(
      uniqueTemplateInazCodes({
        id: 1,
        code: "X",
        label: "X",
        rules: undefined,
      } as PresenzeScheduleTemplate),
    ).toEqual([]);
    expect(
      uniqueTemplateInazCodes({
        id: 1,
        code: "X",
        label: "X",
        rules: [{ ordinary_label: "MAR" }, { ordinary_label: "LUN" }, { ordinary_label: "  " }],
      }),
    ).toEqual(["LUN", "MAR"]);
  });

  test("profile inference and badge labels", () => {
    expect(inferGaiaProfileCode({ operai_group: "agrario" } as PresenzeCollaborator)).toBe("GAIA_OPERAI");
    expect(inferGaiaProfileCode({ contract_kind: "impiegato" } as PresenzeCollaborator)).toBe("GAIA_IMPIEGATI");
    expect(inferGaiaProfileCode({ contract_kind: "operaio" } as PresenzeCollaborator)).toBe("GAIA_OPERAI");
    expect(inferGaiaProfileCode({ contract_kind: "quadro" } as PresenzeCollaborator)).toBe("GAIA_IMPIEGATI");
    expect(inferGaiaProfileCode({ contract_kind: "unknown" as PresenzeCollaborator["contract_kind"] } as PresenzeCollaborator)).toBe("");
    expect(inferGaiaProfileCode(null)).toBe("");

    expect(formatAbsenceCause("ferie")).toBe("Ferie");
    expect(formatAbsenceCause("")).toBe("—");
    expect(formatAbsenceCause("custom_cause")).toBe("custom cause");
    expect(formatRequestDescription("Richiesta semplice")).toBe("Richiesta semplice");
    expect(formatRequestDescription("REQ - Dettaglio richiesta")).toBe("Dettaglio richiesta");
    expect(formatRequestDescription("REQ -   ")).toBe("REQ -   ");
    expect(formatRequestDescription(null)).toBe("—");

    expect(recoveryBadgeLabel(dailyRecord({ grants_recovery_day: true, recovery_day_credit: 1 }))).toBe("Recupero +1");
    expect(recoveryBadgeLabel(dailyRecord({ uses_recovery_day: true, recovery_day_debit: 1 }))).toBe("Recupero -1");
    expect(recoveryBadgeLabel(dailyRecord({ holiday_kind: "ordinary" }))).toBe("Festivita ordinaria");
    expect(recoveryBadgeLabel(dailyRecord({ holiday_kind: "working_override" }))).toBe("Override lavorativo");
    expect(recoveryBadgeLabel(dailyRecord({}))).toBeNull();
    expect(requestBadgeLabel(dailyRecord({ resolved_absence_cause: "permesso" }))).toBe("Permesso");
    expect(requestBadgeLabel(dailyRecord({ request_description: "Richiesta - Permesso ore" }))).toBe("Permesso ore");
    expect(requestBadgeLabel(dailyRecord({}))).toBeNull();
  });

  test("detail preview and section summary helpers", () => {
    expect(formatDetailEntries({ a: "1", b: "2" })).toEqual([
      ["a", "1"],
      ["b", "2"],
    ]);
    expect(firstDetailPreview([{ a: "  " }, { b: "Preview" }])).toBe("Preview");
    expect(firstDetailPreview([])).toBeNull();
    expect(sectionSummaryLabel("Sezione")).toBe("Sezione");
    expect(sectionSummaryLabel("Sezione", { count: 2, preview: "Anteprima", status: "OK" })).toBe(
      "Sezione (OK · Anteprima · 2 voci)",
    );
    expect(sectionSummaryLabel("Sezione", { count: 1 })).toBe("Sezione (1 voce)");
  });
});
