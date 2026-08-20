import type { PresenzeDailyRecord } from "@/types/api";

export type CellKind = "anomaly" | "analysis" | "special" | "ferie" | "permesso" | "malattia" | "absence" | "worked" | "rest";

export type DailyMatrixDayColumn = {
  iso: string;
  day: number;
  weekday: string;
  isWeekend: boolean;
  isToday: boolean;
};

export const CELL_TONE: Record<CellKind, string> = {
  anomaly: "bg-red-50 text-red-700 ring-1 ring-inset ring-red-200 hover:bg-red-100",
  analysis: "bg-amber-50 text-amber-800 ring-1 ring-inset ring-amber-200 hover:bg-amber-100",
  special: "bg-violet-50 text-violet-700 ring-1 ring-inset ring-violet-200 hover:bg-violet-100",
  ferie: "bg-teal-50 text-teal-800 ring-1 ring-inset ring-teal-200 hover:bg-teal-100",
  permesso: "bg-sky-50 text-sky-800 ring-1 ring-inset ring-sky-200 hover:bg-sky-100",
  malattia: "bg-gray-100 text-gray-700 ring-1 ring-inset ring-gray-200 hover:bg-gray-200",
  absence: "bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-200 hover:bg-sky-100",
  worked: "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-100 hover:bg-emerald-100",
  rest: "bg-gray-50 text-gray-300 hover:bg-gray-100",
};

export const MODAL_ROW_TONE: Record<CellKind, string> = {
  anomaly: "bg-red-50/90 text-red-900 ring-1 ring-inset ring-red-100 hover:bg-red-100",
  analysis: "bg-amber-50/90 text-amber-900 ring-1 ring-inset ring-amber-100 hover:bg-amber-100",
  special: "bg-violet-50/90 text-violet-900 ring-1 ring-inset ring-violet-100 hover:bg-violet-100",
  ferie: "bg-teal-50/90 text-teal-900 ring-1 ring-inset ring-teal-100 hover:bg-teal-100",
  permesso: "bg-sky-50/90 text-sky-900 ring-1 ring-inset ring-sky-100 hover:bg-sky-100",
  malattia: "bg-gray-100 text-gray-800 ring-1 ring-inset ring-gray-200 hover:bg-gray-200",
  absence: "bg-sky-50/90 text-sky-900 ring-1 ring-inset ring-sky-100 hover:bg-sky-100",
  worked: "bg-emerald-50/90 text-emerald-900 ring-1 ring-inset ring-emerald-100 hover:bg-emerald-100",
  rest: "bg-gray-50 text-gray-500 ring-1 ring-inset ring-gray-100 hover:bg-gray-100",
};

export function formatHoursCompact(minutes: number | null | undefined): string {
  if (!minutes) return "0";
  const value = minutes / 60;
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function formatHours(minutes: number): string {
  return `${(minutes / 60).toFixed(2)} h`;
}

export function effectiveExtraMinutes(record: PresenzeDailyRecord): number {
  return (
    record.effective_extra_minutes ??
    (record.effective_straordinario_minutes ?? record.straordinario_minutes ?? 0) +
      (record.effective_mpe_minutes ?? record.mpe_minutes ?? 0)
  );
}

export function effectiveOrdinaryMinutes(record: PresenzeDailyRecord): number {
  if (
    record.operational_formula_code &&
    record.operational_expected_minutes != null &&
    record.operational_worked_minutes != null
  ) {
    return Math.min(record.operational_worked_minutes, record.operational_expected_minutes);
  }
  return record.ordinary_minutes ?? 0;
}

export function hasWorkedTime(record: PresenzeDailyRecord): boolean {
  if ((record.operational_worked_minutes ?? 0) > 0) return true;
  if (effectiveOrdinaryMinutes(record) > 0) return true;
  return record.punches.some((punch) => Boolean(punch.entry_time || punch.exit_time));
}

export function isUnworkedHolidayRecord(record: PresenzeDailyRecord): boolean {
  return Boolean(record.special_day) && !hasWorkedTime(record);
}

export function classifyDailyMatrixCell(record: PresenzeDailyRecord): CellKind {
  if (record.operational_status === "blocking") return "anomaly";
  if (record.operational_status === "in_analysis") return "analysis";
  if (record.operational_status === "unknown" && (record.detail_anomalies.length > 0 || record.detail_error)) return "anomaly";
  if (record.special_day) return "special";
  if (record.resolved_absence_cause === "ferie") return "ferie";
  if (record.resolved_absence_cause === "permesso") return "permesso";
  if (record.resolved_absence_cause === "malattia") return "malattia";
  if ((record.ordinary_minutes ?? 0) > 0) return "worked";
  if ((record.absence_minutes ?? 0) > 0) return "absence";
  return "rest";
}

export function dailyMatrixCellPrimaryLabel(record: PresenzeDailyRecord, kind: CellKind, column: DailyMatrixDayColumn): string {
  if (kind === "special" && isUnworkedHolidayRecord(record)) {
    return "Fest";
  }
  if (kind === "worked" || kind === "special") {
    const ordinaryMinutes = effectiveOrdinaryMinutes(record);
    const label = formatHoursCompact(ordinaryMinutes || record.teo_minutes);
    return column.weekday === "DOM" && label === "0" ? "🌿" : label;
  }
  if (kind === "ferie") return "Fer";
  if (kind === "permesso") return "Perm";
  if (kind === "malattia") return "Mal";
  if (kind === "analysis") {
    if (record.resolved_absence_cause === "permesso") return "Perm";
    if (record.resolved_absence_cause === "ferie") return "Fer";
    if (record.resolved_absence_cause === "malattia") return "Mal";
    if (record.detail_requests.length > 0 || record.request_description) return "Rich";
    return "Anom";
  }
  if (kind === "absence" || kind === "anomaly") {
    const status = (record.detail_status ?? record.stato ?? "").trim().toLowerCase();
    if (status.includes("perm")) return "Perm";
    if (status.includes("fer")) return "Fer";
    if (status.includes("anom")) return "Anom";
    if (status.includes("malatt")) return "Mal";
    if (status.includes("rich")) return "Rich";
    if (status && !status.includes("gior") && !status.includes("regol")) {
      return status.length > 4 ? status.slice(0, 4) : status;
    }
    if (kind === "anomaly") return "Anom";
    return formatHoursCompact(record.absence_minutes ?? record.justified_minutes);
  }
  return "·";
}

export function absenceSummaryMinutes(record: PresenzeDailyRecord): number {
  return record.absence_minutes ?? record.justified_minutes ?? 0;
}

export function formatRequestDescription(value: string | null | undefined): string {
  if (!value) return "—";
  if (value.includes(" - ")) {
    const [, right] = value.split(" - ", 2);
    if (right?.trim()) return right.trim();
  }
  return value;
}

export function authorizedPunchDirection(record: PresenzeDailyRecord): "E" | "U" | null {
  if ((record.request_status ?? "").toUpperCase() !== "ACC" || !record.request_description) return null;
  const description = formatRequestDescription(record.request_description);
  if (/\bE\b/i.test(description)) return "E";
  if (/\bU\b/i.test(description)) return "U";
  return null;
}

export function authorizedPunchLabel(record: PresenzeDailyRecord): string | null {
  const directionCode = authorizedPunchDirection(record);
  const direction = directionCode === "E" ? "entrata" : directionCode === "U" ? "uscita" : null;
  if (!direction) return null;
  const author = record.request_authorized_by?.trim();
  return author ? "Timbratura di " + direction + " autorizzata da " + author : "Timbratura di " + direction + " autorizzata";
}

export function dailyMatrixCellSecondaryLabel(record: PresenzeDailyRecord, kind: CellKind): string | null {
  const extra = effectiveExtraMinutes(record);
  const absence = absenceSummaryMinutes(record);
  const missing = record.operational_missing_minutes ?? 0;

  if (kind === "special" && isUnworkedHolidayRecord(record)) {
    return null;
  }
  if (kind === "worked" || kind === "special") {
    if (authorizedPunchLabel(record)) return "Valid.";
    if (extra > 0) return `+${formatHoursCompact(extra)}h`;
    if ((record.trasferta_minutes ?? 0) > 0) return `T ${formatHoursCompact(record.trasferta_minutes)}h`;
    if ((record.km_value ?? 0) > 0) return `KM ${record.km_value}`;
    return record.detail_requests.length > 0 ? "Rich." : null;
  }
  if (kind === "ferie" || kind === "permesso" || kind === "malattia" || kind === "absence") {
    return absence > 0 ? `${formatHoursCompact(absence)}h` : null;
  }
  if (kind === "analysis" || kind === "anomaly") {
    if (missing > 0) return `-${formatHoursCompact(missing)}h`;
    if (absence > 0) return `${formatHoursCompact(absence)}h`;
    return record.detail_requests.length > 0 ? "Rich." : null;
  }
  return null;
}

export function dailyMatrixCellTooltipLabel(record: PresenzeDailyRecord): string {
  const inazStatus = record.detail_status ?? record.stato ?? "n/d";
  const authorizedLabel = authorizedPunchLabel(record);
  if (record.operational_status === "ok" && authorizedLabel) return "GAIA: giornata quadrata · " + authorizedLabel;
  if (record.operational_status === "ok") return "GAIA: giornata quadrata";
  if (record.operational_status === "in_analysis") return "GAIA: in analisi · INAZ: " + inazStatus;
  if (record.operational_status === "blocking") {
    const missing = record.operational_missing_minutes > 0 ? " · mancanti " + formatHours(record.operational_missing_minutes) : "";
    return "GAIA: da sistemare" + missing + " · INAZ: " + inazStatus;
  }
  return inazStatus;
}
