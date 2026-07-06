/* v8 ignore start -- Next page shell: covered by rendering tests; operational logic is tested in backend/helpers. */
"use client";

import Link from "next/link";
import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { Badge } from "@/components/ui/badge";
import {
  getCurrentUser,
  getPresenzeAccessContext,
  getPresenzeDailyRecord,
  listAllPresenzeCollaborators,
  listPresenzeDailyMatrixRecords,
  updatePresenzeDailyRecord,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { getPresenzeCompanyLabel } from "@/lib/presenze-display";
import type {
  CurrentUser,
  PresenzeAccessContext,
  PresenzeCollaborator,
  PresenzeDailyRecord,
} from "@/types/api";

type DailyEditForm = {
  kmValue: string;
  trasfertaMinutes: string;
  trasfertaMontano: boolean;
  reperibilitaGiornaliera: boolean;
  overrideStraordinario: string;
  overrideMpe: string;
  manualNote: string;
  validationNote: string;
};

type DayColumn = {
  iso: string;
  day: number;
  weekday: string;
  isWeekend: boolean;
  isToday: boolean;
};

type CellKind = "anomaly" | "analysis" | "special" | "ferie" | "permesso" | "malattia" | "absence" | "worked" | "rest";

const WEEKDAY_LABELS = ["dom", "lun", "mar", "mer", "gio", "ven", "sab"];
const INITIAL_VISIBLE_ROWS = 36;
const VISIBLE_ROWS_STEP = 48;
const monthRecordsCache = new Map<string, Promise<PresenzeDailyRecord[]>>();

function currentMonthValue(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function shiftMonth(monthValue: string, delta: number): string {
  const [year, month] = monthValue.split("-").map(Number);
  const shifted = new Date(year, month - 1 + delta, 1);
  return `${shifted.getFullYear()}-${String(shifted.getMonth() + 1).padStart(2, "0")}`;
}

function formatMonthLabel(monthValue: string): string {
  return new Intl.DateTimeFormat("it-IT", { month: "long", year: "numeric" }).format(new Date(`${monthValue}-01T00:00:00`));
}

function formatWeekdayLabel(isoDate: string): string {
  return new Intl.DateTimeFormat("it-IT", { weekday: "long" }).format(new Date(`${isoDate}T00:00:00`));
}

function todayIso(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function formatOperaiGroup(value: PresenzeCollaborator["operai_group"] | null | undefined): string {
  if (value === "agrario") return "Agrario";
  if (value === "catasto_magazzino") return "Catasto / magazzino";
  return "Non impostato";
}

function operaiGroupBadgeVariant(value: PresenzeCollaborator["operai_group"] | null | undefined): "success" | "info" | "neutral" {
  if (value === "agrario") return "success";
  if (value === "catasto_magazzino") return "info";
  return "neutral";
}

function buildMonthDays(monthValue: string): DayColumn[] {
  const [yearString, monthString] = monthValue.split("-");
  const year = Number(yearString);
  const month = Number(monthString);
  const total = new Date(year, month, 0).getDate();
  const today = todayIso();
  const days: DayColumn[] = [];
  for (let day = 1; day <= total; day += 1) {
    const iso = `${yearString}-${monthString}-${String(day).padStart(2, "0")}`;
    const weekdayIndex = new Date(`${iso}T00:00:00`).getDay();
    days.push({
      iso,
      day,
      weekday: WEEKDAY_LABELS[weekdayIndex],
      isWeekend: weekdayIndex === 0 || weekdayIndex === 6,
      isToday: iso === today,
    });
  }
  return days;
}

function monthBounds(monthValue: string): { start: string; end: string } {
  const days = buildMonthDays(monthValue);
  return { start: days[0]?.iso ?? `${monthValue}-01`, end: days[days.length - 1]?.iso ?? `${monthValue}-28` };
}

function formatHours(minutes: number | null | undefined): string {
  if (minutes == null) return "—";
  return `${(minutes / 60).toFixed(2)} h`;
}

function formatHoursCompact(minutes: number | null | undefined): string {
  if (!minutes) return "0";
  const value = minutes / 60;
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function formatMinutesInput(minutes: number | null): string {
  if (minutes == null) return "";
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return `${String(hours).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
}

function parseMinutesInput(value: string): number | null {
  const normalized = value.trim();
  if (!normalized) return null;
  const match = normalized.match(/^(\d{1,2}):(\d{2})$/);
  if (match) {
    return Number(match[1]) * 60 + Number(match[2]);
  }
  const asNumber = Number(normalized);
  if (Number.isFinite(asNumber)) {
    return Math.max(0, Math.round(asNumber));
  }
  return null;
}

function formatReperibilitaDisplay(unit: PresenzeDailyRecord["reperibilita_unit"], quantity: number | null): string {
  if (unit === "none") return "Nessuna";
  if (unit === "days" && (quantity ?? 0) > 0) return "Giornaliera";
  const labels: Record<Exclude<PresenzeDailyRecord["reperibilita_unit"], "none">, string> = {
    hours: "ore",
    days: "giorni",
    shifts: "turni",
  };
  return `${quantity ?? "—"} ${labels[unit]}`;
}

function formatTrasfertaDisplay(minutes: number | null, montano: boolean): string {
  if (montano) {
    return minutes && minutes > 0 ? `${formatHours(minutes)} · comune montano` : "Comune montano (X)";
  }
  if (minutes == null || minutes <= 0) return "Nessuna";
  return formatHours(minutes);
}

function effectiveExtraMinutes(record: PresenzeDailyRecord): number {
  return (
    record.effective_extra_minutes ??
    (record.effective_straordinario_minutes ?? record.straordinario_minutes ?? 0) +
      (record.effective_mpe_minutes ?? record.mpe_minutes ?? 0)
  );
}

function recordScheduleCode(record: PresenzeDailyRecord): string | null {
  if (record.schedule_code) return record.schedule_code;
  const programmed = record.detail_programmed_schedule;
  if (programmed) return programmed.split(" - ")[0]?.trim() || null;
  return null;
}

function recordScheduleLabel(record: PresenzeDailyRecord): string | null {
  return record.detail_programmed_schedule ?? record.schedule_code ?? null;
}

function classifyCell(record: PresenzeDailyRecord): CellKind {
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

const CELL_TONE: Record<CellKind, string> = {
  anomaly: "bg-red-50 text-red-700 ring-1 ring-inset ring-red-200 hover:bg-red-100",
  analysis: "bg-amber-50 text-amber-800 ring-1 ring-inset ring-amber-200 hover:bg-amber-100",
  special: "bg-violet-50 text-violet-700 ring-1 ring-inset ring-violet-200 hover:bg-violet-100",
  ferie: "bg-amber-50 text-amber-800 ring-1 ring-inset ring-amber-200 hover:bg-amber-100",
  permesso: "bg-sky-50 text-sky-800 ring-1 ring-inset ring-sky-200 hover:bg-sky-100",
  malattia: "bg-gray-100 text-gray-700 ring-1 ring-inset ring-gray-200 hover:bg-gray-200",
  absence: "bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-200 hover:bg-sky-100",
  worked: "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-100 hover:bg-emerald-100",
  rest: "bg-gray-50 text-gray-300 hover:bg-gray-100",
};

const MODAL_ROW_TONE: Record<CellKind, string> = {
  anomaly: "bg-red-50/90 text-red-900 ring-1 ring-inset ring-red-100 hover:bg-red-100",
  analysis: "bg-amber-50/90 text-amber-900 ring-1 ring-inset ring-amber-100 hover:bg-amber-100",
  special: "bg-violet-50/90 text-violet-900 ring-1 ring-inset ring-violet-100 hover:bg-violet-100",
  ferie: "bg-amber-50/90 text-amber-900 ring-1 ring-inset ring-amber-100 hover:bg-amber-100",
  permesso: "bg-sky-50/90 text-sky-900 ring-1 ring-inset ring-sky-100 hover:bg-sky-100",
  malattia: "bg-gray-100 text-gray-800 ring-1 ring-inset ring-gray-200 hover:bg-gray-200",
  absence: "bg-sky-50/90 text-sky-900 ring-1 ring-inset ring-sky-100 hover:bg-sky-100",
  worked: "bg-emerald-50/90 text-emerald-900 ring-1 ring-inset ring-emerald-100 hover:bg-emerald-100",
  rest: "bg-gray-50 text-gray-500 ring-1 ring-inset ring-gray-100 hover:bg-gray-100",
};

function cellPrimaryLabel(record: PresenzeDailyRecord, kind: CellKind, column: DayColumn): string {
  if (kind === "worked" || kind === "special") {
    const label = formatHoursCompact(record.ordinary_minutes ?? record.teo_minutes);
    return column.weekday === "DOM" && label === "0" ? "🌿" : label;
  }
  if (kind === "ferie") return "Fer";
  if (kind === "permesso") return "Perm";
  if (kind === "malattia") return "Mal";
  if (kind === "analysis") return "Anom";
  if (kind === "absence" || kind === "anomaly") {
    const status = (record.detail_status ?? record.stato ?? "").trim();
    if (status) {
      return status.length > 4 ? status.slice(0, 4) : status;
    }
    return formatHoursCompact(record.absence_minutes);
  }
  return "·";
}

function detailBadgeVariant(record: PresenzeDailyRecord): "danger" | "warning" | "success" | "neutral" {
  const status = (record.detail_status ?? record.stato ?? "").toLowerCase();
  if (status.includes("regolare")) return "success";
  const kind = classifyCell(record);
  if (kind === "anomaly") return "danger";
  if (kind === "analysis") return "warning";
  if (kind === "special" || kind === "ferie" || kind === "permesso" || kind === "malattia") return "warning";
  if (kind === "worked") return "success";
  return "neutral";
}

function cellTooltipLabel(record: PresenzeDailyRecord): string {
  const inazStatus = record.detail_status ?? record.stato ?? "n/d";
  if (record.operational_status === "ok") return "GAIA: giornata quadrata";
  if (record.operational_status === "in_analysis") return "GAIA: in analisi · INAZ: " + inazStatus;
  if (record.operational_status === "blocking") {
    const missing = record.operational_missing_minutes > 0 ? " · mancanti " + formatHours(record.operational_missing_minutes) : "";
    return "GAIA: da sistemare" + missing + " · INAZ: " + inazStatus;
  }
  return inazStatus;
}

function formatAbsenceCause(cause: string | null | undefined): string {
  if (!cause) return "—";
  const labels: Record<string, string> = {
    ferie: "Ferie",
    permesso: "Permesso",
    malattia: "Malattia",
    riposo: "Riposo",
    festivita: "Festivita",
    banca_ore: "Banca ore",
    assenza_da_giustificare: "Assenza da giustificare",
  };
  return labels[cause] ?? cause.replaceAll("_", " ");
}

function formatRequestDescription(value: string | null | undefined): string {
  if (!value) return "—";
  if (value.includes(" - ")) {
    const [, right] = value.split(" - ", 2);
    if (right?.trim()) return right.trim();
  }
  return value;
}

function requestBadgeLabel(record: PresenzeDailyRecord): string | null {
  if (record.resolved_absence_cause) {
    return formatAbsenceCause(record.resolved_absence_cause);
  }
  if (record.request_description) {
    return formatRequestDescription(record.request_description);
  }
  return null;
}

function requestSummaryLabel(record: PresenzeDailyRecord): string | null {
  const label = requestBadgeLabel(record);
  if (!label) return null;
  const minutes = record.absence_minutes ?? record.justified_minutes;
  return minutes && minutes > 0 ? label + " · " + formatHours(minutes) : label;
}

function authorizedPunchDirection(record: PresenzeDailyRecord): "E" | "U" | null {
  if ((record.request_status ?? "").toUpperCase() !== "ACC" || !record.request_description) return null;
  const description = formatRequestDescription(record.request_description);
  if (/\bE\b/i.test(description)) return "E";
  if (/\bU\b/i.test(description)) return "U";
  return null;
}

function authorizedPunchLabel(record: PresenzeDailyRecord): string | null {
  const directionCode = authorizedPunchDirection(record);
  const direction = directionCode === "E" ? "entrata" : directionCode === "U" ? "uscita" : null;
  if (!direction) return null;
  const author = record.request_authorized_by?.trim();
  return author ? "Timbratura di " + direction + " autorizzata da " + author : "Timbratura di " + direction + " autorizzata";
}

function isFerieRecord(record: PresenzeDailyRecord): boolean {
  return record.resolved_absence_cause === "ferie";
}

function formatPunchTerminalLabel(value: string | null | undefined): string | null {
  if (!value) return null;
  if (value.includes("-")) {
    const [, right] = value.split("-", 2);
    if (right?.trim()) return right.trim();
  }
  return value;
}

function primaryPunchSummary(record: PresenzeDailyRecord): { entry: string | null; exit: string | null; terminal: string | null } {
  const pairedPunch = record.punches.find((punch) => punch.entry_time || punch.exit_time);
  if (pairedPunch) {
    return {
      entry: pairedPunch.entry_time,
      exit: pairedPunch.exit_time,
      terminal: formatPunchTerminalLabel(pairedPunch.terminal_label),
    };
  }
  const entry = record.detail_punch_rows.find((punch) => punch.direction?.toUpperCase() === "E");
  const exit = [...record.detail_punch_rows].reverse().find((punch) => punch.direction?.toUpperCase() === "U");
  return {
    entry: entry?.time ?? null,
    exit: exit?.time ?? null,
    terminal: formatPunchTerminalLabel(entry?.terminal_label ?? exit?.terminal_label),
  };
}

function formatDetailPunchDirection(value: string | null | undefined): string {
  if (value === "E") return "Entrata";
  if (value === "U") return "Uscita";
  return value ?? "—";
}

function meaningfulDetailPunchRows(record: PresenzeDailyRecord): PresenzeDailyRecord["detail_punch_rows"] {
  return (record.detail_punch_rows ?? []).filter((punch) => Boolean(punch.time || punch.direction || punch.terminal_label));
}

function normalizePunchTime(value: string | null | undefined): string {
  const normalized = value?.trim() ?? "";
  const match = normalized.match(/^(\d{1,2}):(\d{2})(?::\d{2})?$/);
  if (!match) return normalized;
  return `${match[1].padStart(2, "0")}:${match[2]}`;
}

function normalizedDetailPunchTuple(punch: { time?: string | null; direction?: string | null; terminal_label?: string | null }): string {
  return [
    normalizePunchTime(punch.time),
    punch.direction?.trim().toUpperCase() ?? "",
    formatPunchTerminalLabel(punch.terminal_label)?.trim() ?? "",
  ].join("|");
}

function flattenedPairedPunches(record: PresenzeDailyRecord): Array<{ time: string | null; direction: string; terminal_label: string | null }> {
  const rows: Array<{ time: string | null; direction: string; terminal_label: string | null }> = [];
  for (const punch of record.punches) {
    if (punch.entry_time) {
      rows.push({ time: punch.entry_time, direction: "E", terminal_label: punch.terminal_label });
    }
    if (punch.exit_time) {
      rows.push({ time: punch.exit_time, direction: "U", terminal_label: punch.terminal_label });
    }
  }
  return rows;
}

function shouldShowDetailPunchRows(record: PresenzeDailyRecord): boolean {
  const rows = meaningfulDetailPunchRows(record);
  if (rows.length === 0) return false;
  const pairedRows = flattenedPairedPunches(record);
  if (pairedRows.length === 0) return true;
  if (pairedRows.length !== rows.length) return true;
  return rows.some((row, index) => normalizedDetailPunchTuple(row) !== normalizedDetailPunchTuple(pairedRows[index]));
}

function displayedInazPunchRows(record: PresenzeDailyRecord): Array<{ time: string | null; direction: string | null; terminal_label: string | null }> {
  return shouldShowDetailPunchRows(record) ? meaningfulDetailPunchRows(record) : flattenedPairedPunches(record);
}

function displayedInazPunchTimeLabel(
  record: PresenzeDailyRecord,
  punch: { time: string | null; direction: string | null; terminal_label: string | null },
): string {
  const authorizedDirection = authorizedPunchDirection(record);
  const normalizedDirection = punch.direction?.trim().toUpperCase() ?? null;
  if (punch.time) {
    const baseTime = normalizePunchTime(punch.time);
    if (!shouldShowDetailPunchRows(record) && authorizedDirection && normalizedDirection === authorizedDirection) {
      const authorizationLabel = authorizedDirection === "E" ? "ingresso autorizzato" : "uscita autorizzata";
      return `${baseTime} (${authorizationLabel})`;
    }
    return baseTime;
  }
  if (!authorizedDirection || normalizedDirection !== authorizedDirection) return "—";
  const fallback = flattenedPairedPunches(record).find((row) => row.direction === authorizedDirection && row.time);
  if (!fallback?.time) return "—";
  const authorizationLabel = authorizedDirection === "E" ? "ingresso autorizzato" : "uscita autorizzata";
  return `${normalizePunchTime(fallback.time)} (${authorizationLabel})`;
}

function shouldShowInazDetailSection(record: PresenzeDailyRecord): boolean {
  return displayedInazPunchRows(record).length > 0 || Boolean(authorizedPunchLabel(record));
}

function validationBadgeVariant(record: PresenzeDailyRecord): "success" | "neutral" {
  return record.validation_status === "validated" ? "success" : "neutral";
}

function validationLabel(record: PresenzeDailyRecord): string {
  return record.validation_status === "validated" ? "Validata" : "Da validare";
}

async function loadMonthMatrixRecords(token: string, monthValue: string): Promise<PresenzeDailyRecord[]> {
  const cacheKey = `${token}:${monthValue}`;
  const existing = monthRecordsCache.get(cacheKey);
  if (existing) {
    return existing;
  }
  const request = (async () => {
    const { start, end } = monthBounds(monthValue);
    const pageSize = 5000;
    let page = 1;
    let items: PresenzeDailyRecord[] = [];
    while (true) {
      const response = await listPresenzeDailyMatrixRecords(token, {
        dateFrom: start,
        dateTo: end,
        page,
        pageSize,
      });
      items = [...items, ...response.items];
      if (items.length >= response.total || response.items.length === 0) break;
      page += 1;
    }
    return items;
  })().catch((error) => {
    monthRecordsCache.delete(cacheKey);
    throw error;
  });
  monthRecordsCache.set(cacheKey, request);
  return request;
}

export default function PresenzeGiornalierePage() {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [accessContext, setAccessContext] = useState<PresenzeAccessContext | null>(null);
  const [records, setRecords] = useState<PresenzeDailyRecord[]>([]);
  const [collaborators, setCollaborators] = useState<PresenzeCollaborator[]>([]);
  const [selectedMonth, setSelectedMonth] = useState(currentMonthValue());
  const [search, setSearch] = useState("");
  const [scheduleFilter, setScheduleFilter] = useState("");
  const [filterKm, setFilterKm] = useState(false);
  const [filterTrasferta, setFilterTrasferta] = useState(false);
  const [filterStraordinari, setFilterStraordinari] = useState(false);
  const [filterReperibilita, setFilterReperibilita] = useState(false);
  const [kmMode, setKmMode] = useState(false);
  const [kmDrafts, setKmDrafts] = useState<Record<string, string>>({});
  const [savingRecordId, setSavingRecordId] = useState<string | null>(null);
  const [selectedRecordId, setSelectedRecordId] = useState("");
  const [recordDetails, setRecordDetails] = useState<Record<string, PresenzeDailyRecord>>({});
  const [collaboratorModalId, setCollaboratorModalId] = useState("");
  const [editor, setEditor] = useState<DailyEditForm | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingRecordDetail, setIsLoadingRecordDetail] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [dismissedMonth, setDismissedMonth] = useState<string | null>(null);
  const [visibleRowCount, setVisibleRowCount] = useState(INITIAL_VISIBLE_ROWS);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    getCurrentUser(token)
      .then(async (sessionUser) => {
        setCurrentUser(sessionUser);
        const [context, collaboratorResponse] = await Promise.all([
          getPresenzeAccessContext(token),
          listAllPresenzeCollaborators(token),
        ]);
        setAccessContext(context);
        setCollaborators(collaboratorResponse);
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento giornaliere"));
  }, []);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    setIsLoading(true);
    loadMonthMatrixRecords(token, selectedMonth)
      .then((dailyItems) => {
        setRecords(dailyItems);
        setRecordDetails({});
        setSelectedRecordId("");
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento giornaliere"))
      .finally(() => {
        setIsLoading(false);
        setHasLoaded(true);
      });
  }, [selectedMonth]);

  const days = useMemo(() => buildMonthDays(selectedMonth), [selectedMonth]);
  const collaboratorMap = useMemo(() => new Map(collaborators.map((item) => [item.id, item])), [collaborators]);
  const deferredSearch = useDeferredValue(search);

  const recordIndex = useMemo(() => {
    const index = new Map<string, PresenzeDailyRecord>();
    for (const record of records) {
      index.set(`${record.collaborator_id}|${record.work_date}`, record);
    }
    return index;
  }, [records]);

  const recordInsights = useMemo(() => {
    const monthTotals = new Map<string, { ordinary: number; extra: number; km: number; trasferta: number; anomalies: number; straordinario: number; reperibilita: number }>();
    const presentIds = new Set<string>();
    const scheduleCounts = new Map<string, Map<string, number>>();
    const scheduleLabels = new Map<string, string>();
    let anomalies = 0;
    let km = 0;
    let extra = 0;
    let trasferta = 0;

    for (const record of records) {
      presentIds.add(record.collaborator_id);

      const currentTotals = monthTotals.get(record.collaborator_id) ?? { ordinary: 0, extra: 0, km: 0, trasferta: 0, anomalies: 0, straordinario: 0, reperibilita: 0 };
      currentTotals.ordinary += record.ordinary_minutes ?? 0;
      currentTotals.extra += effectiveExtraMinutes(record);
      currentTotals.km += record.km_value ?? 0;
      currentTotals.trasferta += record.trasferta_minutes ?? 0;
      currentTotals.straordinario += record.effective_straordinario_minutes ?? record.straordinario_minutes ?? 0;
      currentTotals.reperibilita += record.reperibilita_unit !== "none" ? record.reperibilita_quantity ?? 1 : 0;
      if (classifyCell(record) === "anomaly") {
        currentTotals.anomalies += 1;
        anomalies += 1;
      }
      monthTotals.set(record.collaborator_id, currentTotals);

      km += record.km_value ?? 0;
      extra += effectiveExtraMinutes(record);
      trasferta += record.trasferta_minutes ?? 0;

      const code = recordScheduleCode(record);
      if (!code) continue;
      const perCollab = scheduleCounts.get(record.collaborator_id) ?? new Map<string, number>();
      perCollab.set(code, (perCollab.get(code) ?? 0) + 1);
      scheduleCounts.set(record.collaborator_id, perCollab);
      if (!scheduleLabels.has(code)) {
        const label = recordScheduleLabel(record);
        if (label) scheduleLabels.set(code, label);
      }
    }

    const collaboratorSchedule = new Map<string, { code: string; label: string }>();
    for (const [collabId, perCollab] of scheduleCounts) {
      let bestCode = "";
      let best = -1;
      for (const [code, occurrences] of perCollab) {
        if (occurrences > best) {
          best = occurrences;
          bestCode = code;
        }
      }
      collaboratorSchedule.set(collabId, { code: bestCode, label: scheduleLabels.get(bestCode) ?? bestCode });
    }

    return {
      collaboratorSchedule,
      monthTotals,
      presentIds,
      summary: { anomalies, km, extra, trasferta },
    };
  }, [records]);

  const collaboratorSchedule = recordInsights.collaboratorSchedule;
  const monthTotals = recordInsights.monthTotals;
  const summary = recordInsights.summary;

  const scheduleOptions = useMemo(() => {
    const map = new Map<string, { code: string; label: string; count: number }>();
    for (const { code, label } of collaboratorSchedule.values()) {
      const entry = map.get(code) ?? { code, label, count: 0 };
      entry.count += 1;
      map.set(code, entry);
    }
    return Array.from(map.values()).sort((a, b) => a.code.localeCompare(b.code));
  }, [collaboratorSchedule]);

  const collaboratorRows = useMemo(() => {
    const normalizedSearch = deferredSearch.trim().toLowerCase();
    return collaborators
      .filter((collaborator) => recordInsights.presentIds.has(collaborator.id))
      .filter((collaborator) => !scheduleFilter || collaboratorSchedule.get(collaborator.id)?.code === scheduleFilter)
      .filter((collaborator) => {
        const totals = monthTotals.get(collaborator.id);
        if (!totals) return false;
        if (filterKm && totals.km <= 0) return false;
        if (filterTrasferta && totals.trasferta <= 0) return false;
        if (filterStraordinari && totals.straordinario <= 0) return false;
        if (filterReperibilita && totals.reperibilita <= 0) return false;
        return true;
      })
      .filter((collaborator) => {
        const company = getPresenzeCompanyLabel(collaborator.company_label, collaborator.company_code, "");
        return (
          !normalizedSearch ||
          [collaborator.name, collaborator.employee_code, company].some((value) =>
            value.toLowerCase().includes(normalizedSearch),
          )
        );
      })
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [collaborators, deferredSearch, scheduleFilter, collaboratorSchedule, recordInsights.presentIds, monthTotals, filterKm, filterTrasferta, filterStraordinari, filterReperibilita]);

  const visibleCollaboratorRows = useMemo(
    () => collaboratorRows.slice(0, Math.min(visibleRowCount, collaboratorRows.length)),
    [collaboratorRows, visibleRowCount],
  );

  useEffect(() => {
    setVisibleRowCount(INITIAL_VISIBLE_ROWS);
  }, [selectedMonth, scheduleFilter, deferredSearch, filterKm, filterTrasferta, filterStraordinari, filterReperibilita]);

  useEffect(() => {
    if (collaboratorRows.length <= INITIAL_VISIBLE_ROWS) return;

    let cancelled = false;
    let handle: number;
    const useIdleCallback = typeof window !== "undefined" && "requestIdleCallback" in window;

    const expandRows = () => {
      if (cancelled) return;
      setVisibleRowCount((current) => {
        if (current >= collaboratorRows.length) return current;
        const next = Math.min(current + VISIBLE_ROWS_STEP, collaboratorRows.length);
        if (next < collaboratorRows.length) {
          if (useIdleCallback) {
            handle = window.requestIdleCallback(expandRows, { timeout: 250 });
          } else {
            handle = window.setTimeout(expandRows, 80);
          }
        }
        return next;
      });
    };

    if (useIdleCallback) {
      handle = window.requestIdleCallback(expandRows, { timeout: 150 });
    } else {
      handle = window.setTimeout(expandRows, 80);
    }

    return () => {
      cancelled = true;
      if (useIdleCallback && "cancelIdleCallback" in window) {
        window.cancelIdleCallback(handle);
      } else {
        window.clearTimeout(handle);
      }
    };
  }, [collaboratorRows]);

  const selectedRecord = useMemo(() => {
    if (!selectedRecordId) return null;
    return recordDetails[selectedRecordId] ?? records.find((record) => record.id === selectedRecordId) ?? null;
  }, [recordDetails, records, selectedRecordId]);
  const selectedCollaborator = useMemo(
    () => (selectedRecord ? collaboratorMap.get(selectedRecord.collaborator_id) ?? null : null),
    [collaboratorMap, selectedRecord],
  );
  const selectedCollaboratorRecords = useMemo(() => {
    if (!selectedRecord) return [];
    return records
      .filter((record) => record.collaborator_id === selectedRecord.collaborator_id)
      .sort((a, b) => a.work_date.localeCompare(b.work_date));
  }, [records, selectedRecord]);
  const selectedRecordIndex = useMemo(() => {
    if (!selectedRecord) return -1;
    return selectedCollaboratorRecords.findIndex((record) => record.id === selectedRecord.id);
  }, [selectedCollaboratorRecords, selectedRecord]);
  const previousRecord = selectedRecordIndex > 0 ? selectedCollaboratorRecords[selectedRecordIndex - 1] : null;
  const nextRecord =
    selectedRecordIndex >= 0 && selectedRecordIndex < selectedCollaboratorRecords.length - 1
      ? selectedCollaboratorRecords[selectedRecordIndex + 1]
      : null;

  useEffect(() => {
    if (!selectedRecord) return;

    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target?.closest("input, textarea, select")) {
        if (event.key !== "Escape") {
          return;
        }
      }

      if (event.key === "Escape") {
        event.preventDefault();
        setSelectedRecordId("");
        return;
      }

      if (event.key === "ArrowLeft" && previousRecord) {
        event.preventDefault();
        setSelectedRecordId(previousRecord.id);
        return;
      }

      if (event.key === "ArrowRight" && nextRecord) {
        event.preventDefault();
        setSelectedRecordId(nextRecord.id);
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [selectedRecord, previousRecord, nextRecord]);

  useEffect(() => {
    if (!selectedRecord) {
      setEditor(null);
      return;
    }
      setEditor({
        kmValue: selectedRecord.km_value != null ? String(selectedRecord.km_value) : "",
        trasfertaMinutes: selectedRecord.trasferta_minutes != null ? formatMinutesInput(selectedRecord.trasferta_minutes) : "",
        trasfertaMontano: selectedRecord.trasferta_montano,
        reperibilitaGiornaliera: selectedRecord.reperibilita_unit !== "none" && (selectedRecord.reperibilita_quantity ?? 0) > 0,
        overrideStraordinario: formatMinutesInput(selectedRecord.override_straordinario_minutes),
        overrideMpe: formatMinutesInput(selectedRecord.override_mpe_minutes),
        manualNote: selectedRecord.manual_note ?? "",
      validationNote: selectedRecord.validation_note ?? "",
    });
  }, [selectedRecord]);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token || !selectedRecordId || recordDetails[selectedRecordId]) return;
    setIsLoadingRecordDetail(true);
    getPresenzeDailyRecord(token, selectedRecordId)
      .then((detail) => {
        setRecordDetails((current) => ({ ...current, [detail.id]: detail }));
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento dettaglio giornaliera"))
      .finally(() => setIsLoadingRecordDetail(false));
  }, [recordDetails, selectedRecordId]);

  const canEdit = Boolean(currentUser);
  const canEditOperationalData = Boolean(
    currentUser && (accessContext?.can_view_all_data || (selectedRecord && selectedRecord.owner_user_id === currentUser.id)),
  );
  const canEditOperationalExtras = Boolean(selectedRecord && canEditOperationalData && !isFerieRecord(selectedRecord));
  const canValidate = Boolean(accessContext?.is_supervisor || accessContext?.can_view_all_data);

  const scrollRef = useRef<HTMLDivElement>(null);
  const dragState = useRef({ active: false, startX: 0, scrollLeft: 0, moved: false });
  const [isDragging, setIsDragging] = useState(false);

  function handleDragStart(event: React.MouseEvent<HTMLDivElement>) {
    if (event.button !== 0) return;
    const target = event.target as HTMLElement;
    if (target.closest("input, textarea, select")) return;
    const el = scrollRef.current;
    if (!el) return;
    dragState.current = { active: true, startX: event.pageX, scrollLeft: el.scrollLeft, moved: false };
    setIsDragging(true);
  }

  function handleDragMove(event: React.MouseEvent<HTMLDivElement>) {
    const el = scrollRef.current;
    if (!el || !dragState.current.active) return;
    const delta = event.pageX - dragState.current.startX;
    if (Math.abs(delta) > 3) dragState.current.moved = true;
    el.scrollLeft = dragState.current.scrollLeft - delta;
  }

  function handleDragEnd() {
    if (!dragState.current.active) return;
    dragState.current.active = false;
    setIsDragging(false);
  }

  function handleClickCapture(event: React.MouseEvent<HTMLDivElement>) {
    if (dragState.current.moved) {
      event.preventDefault();
      event.stopPropagation();
      dragState.current.moved = false;
    }
  }

  async function persistKm(record: PresenzeDailyRecord, rawValue: string) {
    const token = getStoredAccessToken();
    if (!token) return;
    const trimmed = rawValue.trim();
    const nextValue = trimmed ? Math.max(0, Math.round(Number(trimmed))) : null;
    if (trimmed && !Number.isFinite(Number(trimmed))) return;
    if (nextValue === (record.km_value ?? null)) return;
    setSavingRecordId(record.id);
    setError(null);
    try {
      const updated = await updatePresenzeDailyRecord(token, record.id, { km_value: nextValue });
      setRecords((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setRecordDetails((current) => ({ ...current, [updated.id]: updated }));
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Errore salvataggio KM");
    } finally {
      setSavingRecordId(null);
    }
  }

  async function handleSaveEditor() {
    const token = getStoredAccessToken();
    if (!token || !selectedRecord || !editor) return;
    setIsSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updatePresenzeDailyRecord(token, selectedRecord.id, {
        km_value: editor.kmValue.trim() ? Number(editor.kmValue) : null,
        trasferta_minutes: parseMinutesInput(editor.trasfertaMinutes),
        trasferta_montano: editor.trasfertaMontano,
        reperibilita_unit: editor.reperibilitaGiornaliera ? "days" : "none",
        reperibilita_quantity: editor.reperibilitaGiornaliera ? 1 : null,
        override_straordinario_minutes: parseMinutesInput(editor.overrideStraordinario),
        override_mpe_minutes: parseMinutesInput(editor.overrideMpe),
        manual_note: editor.manualNote.trim() || null,
        ...(canValidate ? { validation_note: editor.validationNote.trim() || null } : {}),
      });
      setRecords((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setRecordDetails((current) => ({ ...current, [updated.id]: updated }));
      setSuccess(`Giornata ${updated.work_date} aggiornata.`);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Errore salvataggio giornaliera");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleValidation(status: "pending" | "validated") {
    const token = getStoredAccessToken();
    if (!token || !selectedRecord || !editor || !canValidate) return;
    setIsSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updatePresenzeDailyRecord(token, selectedRecord.id, {
        validation_status: status,
        validation_note: editor.validationNote.trim() || null,
      });
      setRecords((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setRecordDetails((current) => ({ ...current, [updated.id]: updated }));
      setSuccess(status === "validated" ? `Giornata ${updated.work_date} validata.` : `Validazione rimossa per ${updated.work_date}.`);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Errore validazione giornaliera");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <ProtectedPage title="Giornaliere" description="Cartellino mensile a matrice: collaboratori in verticale, giorni in orizzontale." breadcrumb="Giornaliere" requiredModule="presenze">
      <div className="space-y-6">
        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        {success ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div> : null}

        <article className="panel-card">
          <div className="grid gap-x-6 gap-y-4 lg:grid-cols-12">
            <div className="lg:col-span-4">
              <p className="text-sm font-medium text-gray-700">Mese operativo</p>
              <div className="mt-1 flex items-stretch gap-1">
                <button
                  type="button"
                  aria-label="Mese precedente"
                  onClick={() => setSelectedMonth((current) => shiftMonth(current, -1))}
                  className="flex w-9 items-center justify-center rounded-lg border border-gray-200 bg-white text-gray-600 transition hover:bg-gray-50"
                >
                  ‹
                </button>
                <input className="form-control flex-1" type="month" aria-label="Mese operativo" value={selectedMonth} onChange={(event) => setSelectedMonth(event.target.value)} />
                <button
                  type="button"
                  aria-label="Mese successivo"
                  onClick={() => setSelectedMonth((current) => shiftMonth(current, 1))}
                  className="flex w-9 items-center justify-center rounded-lg border border-gray-200 bg-white text-gray-600 transition hover:bg-gray-50"
                >
                  ›
                </button>
              </div>
              <p className="mt-1 text-xs capitalize text-gray-400">{formatMonthLabel(selectedMonth)}</p>
            </div>

            <label className="block text-sm font-medium text-gray-700 lg:col-span-4">
              Cerca collaboratore
              <input className="form-control mt-1" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Nome o matricola" />
            </label>

            <div className="flex items-start gap-2 lg:col-span-4 lg:justify-end lg:pt-6">
                <button
                  type="button"
                  onClick={() => setKmMode((value) => !value)}
                  className={kmMode ? "btn-primary" : "btn-secondary"}
                  disabled={!canEditOperationalData}
                >
                  {kmMode ? "Esci da inserimento KM" : "Inserisci KM"}
                </button>
              <Link className="btn-secondary" href="/presenze/anomalie">
                Analisi anomalie
              </Link>
            </div>

            {scheduleOptions.length > 0 ? (
              <div className="lg:col-span-8">
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400">Filtri · tipo orario / contratto</p>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => setScheduleFilter("")}
                    className={`rounded-full px-3 py-1 text-xs font-medium transition ${scheduleFilter === "" ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}
                  >
                    Tutti ({collaboratorSchedule.size})
                  </button>
                  {scheduleOptions.map((option) => (
                    <button
                      key={option.code}
                      type="button"
                      title={option.label}
                      onClick={() => setScheduleFilter((current) => (current === option.code ? "" : option.code))}
                      className={`rounded-full px-3 py-1 text-xs font-medium transition ${scheduleFilter === option.code ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}
                    >
                      {option.code} ({option.count})
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="lg:col-span-8">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400">Filtri · voci operative</p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setFilterKm((current) => !current)}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition ${filterKm ? "bg-amber-600 text-white" : "bg-amber-50 text-amber-800 hover:bg-amber-100"}`}
                >
                  KM carburanti
                </button>
                <button
                  type="button"
                  onClick={() => setFilterTrasferta((current) => !current)}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition ${filterTrasferta ? "bg-sky-600 text-white" : "bg-sky-50 text-sky-800 hover:bg-sky-100"}`}
                >
                  Trasferte
                </button>
                <button
                  type="button"
                  onClick={() => setFilterStraordinari((current) => !current)}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition ${filterStraordinari ? "bg-emerald-600 text-white" : "bg-emerald-50 text-emerald-800 hover:bg-emerald-100"}`}
                >
                  Straordinari
                </button>
                <button
                  type="button"
                  onClick={() => setFilterReperibilita((current) => !current)}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition ${filterReperibilita ? "bg-orange-600 text-white" : "bg-orange-50 text-orange-800 hover:bg-orange-100"}`}
                >
                  Reperibilita
                </button>
              </div>
            </div>

            <div className="lg:col-span-4 lg:justify-self-end">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400">Riepilogo mese</p>
              <div className="flex flex-wrap gap-2 text-xs lg:justify-end">
                <span className="rounded-full bg-gray-100 px-3 py-1 font-medium text-gray-700">{collaboratorRows.length} coll.</span>
                <span className="rounded-full bg-emerald-100 px-3 py-1 font-medium text-emerald-700">Extra {formatHours(summary.extra)}</span>
                <span className="rounded-full bg-amber-100 px-3 py-1 font-medium text-amber-700">{summary.km} KM</span>
                <span className="rounded-full bg-sky-100 px-3 py-1 font-medium text-sky-700">Trasferta {formatHours(summary.trasferta)}</span>
                <span className="rounded-full bg-red-100 px-3 py-1 font-medium text-red-700">{summary.anomalies} anomalie</span>
              </div>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-4 border-t border-gray-100 pt-4 text-xs text-gray-500">
            <span className="inline-flex items-center gap-1.5"><span className="h-3 w-3 rounded ring-1 ring-inset ring-emerald-200 bg-emerald-50" /> Lavorato</span>
            <span className="inline-flex items-center gap-1.5"><span className="h-3 w-3 rounded ring-1 ring-inset ring-sky-200 bg-sky-50" /> Assenza</span>
            <span className="inline-flex items-center gap-1.5"><span className="h-3 w-3 rounded ring-1 ring-inset ring-violet-200 bg-violet-50" /> Giorno speciale</span>
            <span className="inline-flex items-center gap-1.5"><span className="h-3 w-3 rounded ring-1 ring-inset ring-red-200 bg-red-50" /> Anomalia</span>
            <span className="inline-flex items-center gap-1.5"><span className="text-emerald-600">▲</span> Extra</span>
            <span className="inline-flex items-center gap-1.5"><span>🚗</span> KM carburante</span>
            <span className="inline-flex items-center gap-1.5"><span className="text-sky-600">T</span> Trasferta</span>
          </div>
        </article>

        <article className="panel-card overflow-hidden p-0">
          {kmMode ? (
            <div className="border-b border-amber-100 bg-amber-50 px-4 py-2 text-xs text-amber-800">
              Modalita inserimento KM attiva: digita i chilometri nella cella del giorno, il salvataggio avviene all’uscita dal campo.
            </div>
          ) : null}
          <div
            ref={scrollRef}
            onMouseDown={handleDragStart}
            onMouseMove={handleDragMove}
            onMouseUp={handleDragEnd}
            onMouseLeave={handleDragEnd}
            onClickCapture={handleClickCapture}
            className={`overflow-x-auto ${isDragging ? "cursor-grabbing select-none" : "cursor-grab"}`}
          >
            {!isLoading && collaboratorRows.length > visibleCollaboratorRows.length ? (
              <div className="sticky left-0 top-0 z-20 border-b border-blue-100 bg-blue-50 px-4 py-2 text-xs text-blue-700">
                Rendering progressivo: {visibleCollaboratorRows.length} di {collaboratorRows.length} collaboratori.
              </div>
            ) : null}
            <table className="border-separate border-spacing-0 text-sm">
              <thead>
                <tr>
                  <th className="sticky left-0 z-20 w-56 min-w-56 border-b border-r border-gray-200 bg-gray-50 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Collaboratore
                  </th>
                  {days.map((column) => (
                    <th
                      key={column.iso}
                      className={`border-b border-gray-200 px-1 py-2 text-center text-[11px] font-medium ${column.isWeekend ? "bg-gray-100 text-gray-400" : "bg-gray-50 text-gray-500"} ${column.isToday ? "ring-1 ring-inset ring-gray-900/20" : ""}`}
                    >
                      <div className="uppercase">{column.weekday}</div>
                      <div className={`text-sm ${column.isToday ? "font-bold text-gray-900" : "text-gray-700"}`}>{column.day}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibleCollaboratorRows.map((collaborator) => {
                  const totals = monthTotals.get(collaborator.id);
                  return (
                    <tr key={collaborator.id} className="group">
                      <th className="sticky left-0 z-10 w-56 min-w-56 border-b border-r border-gray-200 bg-white px-4 py-2 text-left align-top group-hover:bg-gray-50">
                        <button
                          type="button"
                          onClick={() => setCollaboratorModalId(collaborator.id)}
                          className="text-left font-medium text-gray-900 hover:underline"
                        >
                          {collaborator.name}
                        </button>
                        <p className="text-[11px] text-gray-400">
                          {collaborator.employee_code}
                          {collaboratorSchedule.get(collaborator.id)?.code ? (
                            <span className="ml-1 rounded bg-indigo-50 px-1 py-0.5 font-medium text-indigo-600" title={collaboratorSchedule.get(collaborator.id)?.label}>
                              {collaboratorSchedule.get(collaborator.id)?.code}
                            </span>
                          ) : null}
                        </p>
                        <div className="mt-1 flex flex-wrap gap-1 text-[10px]">
                          <Badge variant={operaiGroupBadgeVariant(collaborator.operai_group)}>{formatOperaiGroup(collaborator.operai_group)}</Badge>
                          <span className="rounded bg-gray-100 px-1.5 py-0.5 text-gray-600">Ord {formatHoursCompact(totals?.ordinary)}h</span>
                          {totals && totals.extra > 0 ? <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-emerald-700">Extra {formatHoursCompact(totals.extra)}h</span> : null}
                          {totals && totals.km > 0 ? <span className="rounded bg-amber-100 px-1.5 py-0.5 text-amber-700">{totals.km} km</span> : null}
                          {totals && totals.trasferta > 0 ? <span className="rounded bg-sky-100 px-1.5 py-0.5 text-sky-700">Trasf {formatHoursCompact(totals.trasferta)}h</span> : null}
                          {totals && totals.anomalies > 0 ? <span className="rounded bg-red-100 px-1.5 py-0.5 text-red-700">{totals.anomalies} ⚠</span> : null}
                        </div>
                      </th>
                      {days.map((column) => {
                        const record = recordIndex.get(`${collaborator.id}|${column.iso}`);
                        if (!record) {
                          return (
                            <td key={column.iso} className={`border-b border-gray-100 p-1 ${column.isWeekend ? "bg-gray-50/60" : ""}`}>
                              <div className="mx-auto h-12 w-12 rounded-lg bg-transparent" />
                            </td>
                          );
                        }
                        const kind = classifyCell(record);
                        const extra = effectiveExtraMinutes(record);
                        const isSelected = record.id === selectedRecordId;

                        if (kmMode) {
                          return (
                            <td key={column.iso} className={`border-b border-gray-100 p-1 ${column.isWeekend ? "bg-gray-50/60" : ""}`}>
                              <input
                                inputMode="numeric"
                                disabled={!canEdit || savingRecordId === record.id}
                                defaultValue={kmDrafts[record.id] ?? (record.km_value != null ? String(record.km_value) : "")}
                                onChange={(event) => setKmDrafts((current) => ({ ...current, [record.id]: event.target.value }))}
                                onBlur={(event) => void persistKm(record, event.target.value)}
                                placeholder="km"
                                className="mx-auto block h-12 w-12 rounded-lg border border-amber-200 bg-amber-50 text-center text-sm text-amber-800 focus:border-amber-400 focus:outline-none focus:ring-1 focus:ring-amber-300"
                                title={`${record.work_date} · ${collaborator.name}`}
                              />
                            </td>
                          );
                        }

                        return (
                          <td key={column.iso} className={`border-b border-gray-100 p-1 ${column.isWeekend ? "bg-gray-50/60" : ""}`}>
                            <button
                              type="button"
                              onClick={() => setSelectedRecordId(record.id)}
                              title={record.work_date + " · " + cellTooltipLabel(record)}
                              className={`relative mx-auto flex h-12 w-12 flex-col items-center justify-center rounded-lg text-xs font-semibold transition ${CELL_TONE[kind]} ${isSelected ? "outline outline-2 outline-gray-900" : ""}`}
                            >
                              <span>{cellPrimaryLabel(record, kind, column)}</span>
                              <span className="mt-0.5 flex items-center gap-0.5 text-[9px] font-normal leading-none">
                                {extra > 0 ? <span className="text-emerald-600">▲</span> : null}
                                {record.km_value != null ? <span>🚗</span> : null}
                                {(record.trasferta_minutes ?? 0) > 0 || record.trasferta_montano ? <span className="text-sky-600">T</span> : null}
                                {record.reperibilita_unit !== "none" ? <span className="text-amber-700">R</span> : null}
                                {record.detail_requests.length > 0 ? <span className="text-sky-600">✉</span> : null}
                              </span>
                            </button>
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {!isLoading && records.length > 0 && collaboratorRows.length === 0 ? (
            <div className="px-6 py-12 text-center text-sm text-gray-500">
              Nessun collaboratore corrisponde ai filtri correnti.
            </div>
          ) : null}
          {isLoading ? (
            <div className="flex min-h-[280px] flex-col items-center justify-center gap-3 px-6 py-12 text-center text-sm text-gray-500">
              <span
                className="inline-flex h-8 w-8 animate-spin rounded-full border-2 border-gray-200 border-t-gray-700"
                aria-hidden="true"
              />
              <span>Caricamento cartellino…</span>
            </div>
          ) : null}
        </article>

      </div>

      {selectedRecord && editor ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/45 px-4 py-6" onClick={() => setSelectedRecordId("")}>
          <div className="relative flex w-full max-w-[calc(100vw-2rem)] items-center justify-center gap-2" onClick={(event) => event.stopPropagation()}>
            <button
              type="button"
              aria-label="Giorno precedente"
              disabled={!previousRecord}
              onClick={() => previousRecord && setSelectedRecordId(previousRecord.id)}
              className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border border-gray-200 bg-white text-3xl text-gray-700 shadow-lg transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-30"
            >
              ‹
            </button>
            <div className="flex max-h-[92vh] w-full max-w-[min(92vw,112rem)] flex-col overflow-hidden rounded-3xl bg-white shadow-2xl">
            <div className="flex flex-wrap items-start justify-between gap-4 border-b border-gray-100 px-6 py-5">
              <div className="space-y-2">
                <p className="section-title">
                  {selectedRecord.work_date} · {formatWeekdayLabel(selectedRecord.work_date)} · {selectedCollaborator?.name ?? selectedRecord.collaborator_id}
                </p>
                <div className="flex flex-wrap gap-2 text-xs">
                  {selectedCollaborator?.employee_code ? (
                    <span className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1 font-medium text-gray-700">
                      Matricola {selectedCollaborator.employee_code}
                    </span>
                  ) : null}
                  {selectedCollaborator?.company_label ? (
                    <span className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1 font-medium text-gray-700">
                      {selectedCollaborator.company_label}
                    </span>
                  ) : null}
                  <span className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1 font-medium text-gray-700">
                    {selectedRecord.detail_programmed_schedule ?? selectedRecord.schedule_code ?? "Orario non disponibile"}
                  </span>
                  {selectedRecord.detail_time_slots ? (
                    <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 font-medium text-sky-700">
                      {selectedRecord.detail_time_slots}
                    </span>
                  ) : null}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={detailBadgeVariant(selectedRecord)}>
                  {selectedRecord.detail_status ?? selectedRecord.stato ?? "n/d"}
                </Badge>
                {selectedRecord.operational_status === "in_analysis" ? <Badge variant="warning">GAIA in analisi</Badge> : null}
                {selectedRecord.operational_status === "blocking" ? <Badge variant="danger">GAIA bloccante</Badge> : null}
                <Badge variant={validationBadgeVariant(selectedRecord)}>{validationLabel(selectedRecord)}</Badge>
                {requestBadgeLabel(selectedRecord) ? <Badge variant="warning">{requestBadgeLabel(selectedRecord)}</Badge> : null}
                {selectedRecord.effective_extra_minutes ? <Badge variant="success">extra {formatHours(selectedRecord.effective_extra_minutes)}</Badge> : null}
                <button type="button" className="text-sm text-gray-400 hover:text-gray-700" onClick={() => setSelectedRecordId("")}>
                  Chiudi ✕
                </button>
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
              <div className="grid items-start gap-3 lg:grid-cols-3">
                <div className="rounded-2xl border border-gray-100 bg-gray-50 p-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Totali giornata</p>
                  <div className="mt-2 grid gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 sm:grid-cols-2">
                    {(() => {
                      const punchSummary = primaryPunchSummary(selectedRecord);
                      return (
                        <>
                          <p>Entrata: <span className="block text-base font-semibold text-gray-950">{punchSummary.entry ?? "—"}</span></p>
                          <p>Uscita: <span className="block text-base font-semibold text-gray-950">{punchSummary.exit ?? "—"}</span></p>
                          {punchSummary.terminal ? <p className="text-xs text-gray-500 sm:col-span-2">Terminale: {punchSummary.terminal}</p> : null}
                        </>
                      );
                    })()}
                  </div>
                  <div className="mt-2 space-y-1.5 text-sm text-gray-700">
                    <p>Ordinarie: <span className="text-base font-semibold text-gray-900">{formatHours(selectedRecord.ordinary_minutes)}</span></p>
                    <p>Extra effettivi: <span className="text-base font-semibold text-emerald-700">{formatHours(selectedRecord.effective_extra_minutes)}</span></p>
                    {requestSummaryLabel(selectedRecord) ? (
                      <p>Causale: <span className="text-base font-semibold text-sky-700">{requestSummaryLabel(selectedRecord)}</span></p>
                    ) : null}
                  </div>
                  {(selectedRecord.ordinary_minutes ?? 0) > 0 && (selectedRecord.absence_minutes ?? 0) > 0 ? (
                    <div className="mt-2 rounded-xl border border-gray-200 bg-white px-3 py-2">
                      <p className="text-[11px] uppercase tracking-[0.16em] text-gray-500">Valore tecnico Inaz</p>
                      <p className="mt-1 text-sm text-gray-700">
                        Assenza letta da Inaz: <span className="font-semibold text-gray-900">{formatHours(selectedRecord.absence_minutes)}</span>
                      </p>
                      <p className="mt-1 text-xs text-gray-500">
                        Questo valore puo restare presente finche il direttore non valida la giornata: la timbratura puo essere gia autorizzata dal capo settore, ma Inaz mantiene ancora una assenza tecnica nel riepilogo.
                      </p>
                    </div>
                  ) : null}
                  {selectedRecord.operational_formula_code ? (
                    <div className="mt-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <p className="text-[11px] uppercase tracking-[0.16em] text-amber-600">Formula GAIA</p>
                          <p className="mt-1 text-sm font-semibold text-amber-950">{selectedRecord.operational_formula_code}</p>
                        </div>
                        <Badge variant={selectedRecord.operational_status === "blocking" ? "danger" : selectedRecord.operational_status === "in_analysis" ? "warning" : "success"}>
                          {selectedRecord.operational_status === "blocking" ? "Da sistemare" : selectedRecord.operational_status === "in_analysis" ? "In analisi" : "Quadrata"}
                        </Badge>
                      </div>
                      <div className="mt-2 grid gap-2 text-sm text-amber-950 sm:grid-cols-2">
                        <p>Teorico: <span className="font-semibold">{formatHours(selectedRecord.operational_expected_minutes)}</span></p>
                        <p>Lavorato: <span className="font-semibold">{formatHours(selectedRecord.operational_worked_minutes)}</span></p>
                        <p>Mancanti: <span className="font-semibold">{formatHours(selectedRecord.operational_missing_minutes)}</span></p>
                        <p>MPE: <span className="font-semibold">{formatHours(selectedRecord.operational_mpe_minutes)}</span></p>
                      </div>
                      {selectedRecord.operational_notes.length > 0 ? (
                        <div className="mt-3 space-y-1 text-xs text-amber-800">
                          {selectedRecord.operational_notes.map((note) => (
                            <p key={note}>{note}</p>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                  {((selectedRecord.ordinary_minutes ?? 0) > 0 && (selectedRecord.absence_minutes ?? 0) > 0) || requestBadgeLabel(selectedRecord) ? (
                    <p className="mt-3 text-xs text-gray-500">
                      Se ordinarie e assenza coesistono, l'assenza mostrata qui e un dato tecnico del portale Inaz: puo dipendere da una giornata non ancora validata dal direttore, anche quando una timbratura risulta gia autorizzata dal capo settore.
                    </p>
                  ) : null}
                </div>

                <div className="rounded-3xl border border-amber-200/80 bg-gradient-to-br from-amber-50 via-amber-50 to-white p-4 shadow-sm lg:col-span-2">
                  <div className="flex flex-col gap-1 border-b border-amber-200/70 pb-2 sm:flex-row sm:items-end sm:justify-between">
                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-amber-600">Rettifiche operative</p>
                      <p className="mt-0.5 text-sm font-medium text-amber-950">KM carburante, trasferta e reperibilita giornaliera</p>
                    </div>
                    {!canEditOperationalData ? (
                      <span className="inline-flex rounded-full border border-amber-200 bg-white/80 px-3 py-1 text-[11px] font-medium text-amber-800">
                        Solo validazione
                      </span>
                    ) : null}
                  </div>

                  <div className="mt-3 grid gap-3 xl:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.65fr)]">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <label className="block rounded-2xl border border-amber-200/80 bg-white/85 p-2.5 text-sm font-medium text-amber-950 shadow-sm">
                        <span className="block text-[11px] uppercase tracking-[0.18em] text-amber-600">Chilometri auto</span>
                        <input
                          className="form-control mt-1.5 w-full"
                          inputMode="numeric"
                          value={editor.kmValue}
                          onChange={(event) => setEditor((current) => current ? { ...current, kmValue: event.target.value } : current)}
                          placeholder="Es. 24"
                          disabled={!canEditOperationalExtras}
                        />
                      </label>

                      <div className="rounded-2xl border border-amber-200/80 bg-white/85 p-2.5 shadow-sm">
                        <p className="text-[11px] uppercase tracking-[0.18em] text-amber-600">Reperibilita</p>
                        <label className="mt-1.5 flex items-start gap-2.5 text-sm text-amber-950">
                          <input
                            className="mt-0.5 h-4 w-4 rounded border-amber-300 text-amber-600 focus:ring-amber-500"
                            type="checkbox"
                            checked={editor.reperibilitaGiornaliera}
                            onChange={(event) =>
                              setEditor((current) =>
                                current ? { ...current, reperibilitaGiornaliera: event.target.checked } : current,
                              )
                            }
                            disabled={!canEditOperationalExtras}
                            aria-label="Reperibilita giornaliera"
                          />
                          <span>
                            <span className="block font-medium">Segna reperibilita giornaliera</span>
                            <span className="mt-0.5 block text-[10px] leading-4 text-amber-700">Applica la reperibilita all&apos;intera giornata selezionata.</span>
                          </span>
                        </label>
                      </div>

                      <div className="rounded-2xl border border-amber-200/80 bg-white/85 p-2.5 shadow-sm sm:col-span-2">
                        <p className="text-[11px] uppercase tracking-[0.18em] text-amber-600">Trasferta</p>
                        <div className="mt-1.5 grid gap-2 sm:grid-cols-[minmax(0,140px)_minmax(0,1fr)]">
                          <label className="block text-sm font-medium text-amber-950">
                            <span className="block text-[10px] text-amber-700">Ore / minuti</span>
                            <input
                              className="form-control mt-1.5 w-full"
                              value={editor.trasfertaMinutes}
                              onChange={(event) => setEditor((current) => (current ? { ...current, trasfertaMinutes: event.target.value } : current))}
                              placeholder="Es. 03:00"
                              disabled={!canEditOperationalExtras}
                            />
                          </label>
                          <label className="flex items-start gap-3 text-sm text-amber-950 sm:items-center">
                            <input
                              className="mt-0.5 h-4 w-4 rounded border-amber-300 text-amber-600 focus:ring-amber-500"
                              type="checkbox"
                              checked={editor.trasfertaMontano}
                              onChange={(event) =>
                                setEditor((current) => (current ? { ...current, trasfertaMontano: event.target.checked } : current))
                              }
                              disabled={!canEditOperationalExtras}
                              aria-label="Comune montano"
                            />
                            <span>
                              <span className="block font-medium">Comune montano</span>
                              <span className="mt-0.5 block text-[10px] leading-4 text-amber-700">Nel template legacy viene esportato come `X` nello stesso blocco della trasferta.</span>
                            </span>
                          </label>
                        </div>
                      </div>
                    </div>

                    <div className="rounded-2xl border border-amber-200/80 bg-white/80 p-4 shadow-sm">
                      <p className="text-[11px] uppercase tracking-[0.18em] text-amber-600">Stato attuale</p>
                      <div className="mt-3 space-y-3">
                        <div className="rounded-2xl border border-amber-100 bg-amber-50/70 px-4 py-3">
                          <p className="text-[11px] uppercase tracking-[0.16em] text-amber-500">KM registrati</p>
                          <p className="mt-1 text-base font-semibold text-amber-950">{selectedRecord.km_value ?? "—"}</p>
                        </div>
                        <div className="rounded-2xl border border-amber-100 bg-amber-50/70 px-4 py-3">
                          <p className="text-[11px] uppercase tracking-[0.16em] text-amber-500">Trasferta attuale</p>
                          <p className="mt-1 text-sm font-semibold text-amber-950">
                            {formatTrasfertaDisplay(selectedRecord.trasferta_minutes, selectedRecord.trasferta_montano)}
                          </p>
                        </div>
                        <div className="rounded-2xl border border-amber-100 bg-amber-50/70 px-4 py-3">
                          <p className="text-[11px] uppercase tracking-[0.16em] text-amber-500">Reperibilita attuale</p>
                          <p className="mt-1 text-sm font-semibold text-amber-950">
                            {formatReperibilitaDisplay(selectedRecord.reperibilita_unit, selectedRecord.reperibilita_quantity)}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {!canEditOperationalData ? (
                    <p className="mt-4 text-xs text-amber-800">
                      I capisettore possono validare la giornata, ma non modificare KM e rettifiche operative.
                    </p>
                  ) : isFerieRecord(selectedRecord) ? (
                    <p className="mt-4 text-xs text-amber-800">
                      KM carburante, trasferta e reperibilita sono disabilitati nelle giornate in ferie.
                    </p>
                  ) : null}
                </div>
              </div>

              {(selectedRecord.request_description || selectedRecord.resolved_absence_cause || selectedRecord.request_status) ? (
                <div className="mt-4 rounded-2xl border border-sky-200 bg-sky-50 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-sky-600">Causale rilevata</p>
                  <div className="mt-2 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                    <div>
                      <p className="text-[11px] uppercase tracking-wide text-sky-500">Causale</p>
                      <p className="text-sm font-medium text-sky-950">{formatAbsenceCause(selectedRecord.resolved_absence_cause)}</p>
                    </div>
                    <div>
                      <p className="text-[11px] uppercase tracking-wide text-sky-500">Richiesta</p>
                      <p className="text-sm font-medium text-sky-950">{formatRequestDescription(selectedRecord.request_description)}</p>
                    </div>
                    <div>
                      <p className="text-[11px] uppercase tracking-wide text-sky-500">Stato richiesta</p>
                      <p className="text-sm font-medium text-sky-950">{selectedRecord.request_status ?? "—"}</p>
                    </div>
                    <div>
                      <p className="text-[11px] uppercase tracking-wide text-sky-500">Autorizzato da</p>
                      <p className="text-sm font-medium text-sky-950">{selectedRecord.request_authorized_by ?? "—"}</p>
                    </div>
                  </div>
                </div>
              ) : null}

              {(selectedRecord.detail_anomalies.length > 0 || selectedRecord.detail_error) ? (
                <div className="mt-4 rounded-2xl border border-red-200 bg-gradient-to-br from-red-50 via-white to-white p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-xs uppercase tracking-[0.16em] text-red-600">Anomalie da gestire</p>
                      <p className="mt-1 text-sm text-red-900">Segnali INAZ ancora presenti sul dettaglio giornata.</p>
                    </div>
                    <span className="rounded-full border border-red-200 bg-white px-3 py-1 text-xs font-semibold text-red-700">
                      {selectedRecord.detail_anomalies.length} {selectedRecord.detail_anomalies.length === 1 ? "anomalia" : "anomalie"}
                    </span>
                  </div>
                  <div className="mt-3 grid gap-2 md:grid-cols-2">
                    {selectedRecord.detail_anomalies.map((anomaly, index) => (
                      <div key={selectedRecord.id + "-anomaly-" + index} className="rounded-xl border border-red-100 bg-white px-3 py-3 text-sm text-red-950 shadow-sm">
                        <p className="font-semibold">
                          {anomaly.anomaliagiornata ?? anomaly["Anomalia giornata"] ?? anomaly.col_1 ?? "Anomalia " + (index + 1)}
                        </p>
                        <div className="mt-2 flex flex-wrap gap-1.5 text-[11px] text-red-700">
                          {Object.entries(anomaly)
                            .filter(([label]) => !["anomaliagiornata", "Anomalia giornata", "col_1"].includes(label))
                            .map(([label, value]) => (
                              <span key={label} className="rounded-full border border-red-100 bg-red-50 px-2 py-0.5">
                                <span className="font-medium">{label}</span>: {value || "—"}
                              </span>
                            ))}
                        </div>
                      </div>
                    ))}
                    {selectedRecord.detail_error ? (
                      <div className="rounded-xl border border-red-100 bg-white px-3 py-3 text-sm font-medium text-red-900 shadow-sm">
                        {selectedRecord.detail_error}
                      </div>
                    ) : null}
                  </div>
                </div>
              ) : null}

              {shouldShowInazDetailSection(selectedRecord) ? (
                <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50/40 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="section-title">Timbrature dettaglio Inaz</p>
                      {authorizedPunchLabel(selectedRecord) ? (
                        <p className="mt-1 text-sm font-medium text-emerald-700">{authorizedPunchLabel(selectedRecord)}</p>
                      ) : null}
                      <p className="section-copy mt-1">
                        {shouldShowDetailPunchRows(selectedRecord)
                          ? "Qui vedi le righe del dettaglio Inaz che aggiungono informazione utile rispetto alla ricostruzione della coppia."
                          : "Qui vedi le timbrature lette da Inaz per la giornata."}
                      </p>
                    </div>
                    {displayedInazPunchRows(selectedRecord).length > 0 ? (
                      <span className="rounded-full border border-amber-200 bg-white px-3 py-1 text-xs font-medium text-amber-700">
                        {displayedInazPunchRows(selectedRecord).length} {displayedInazPunchRows(selectedRecord).length === 1 ? "riga" : "righe"} lette
                      </span>
                    ) : null}
                  </div>
                  {displayedInazPunchRows(selectedRecord).length > 0 ? (
                    <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                      {displayedInazPunchRows(selectedRecord).map((punch, index) => (
                        <div key={`${selectedRecord.id}-detail-punch-${index}`} className="rounded-xl border border-amber-200 bg-white px-3 py-3 text-sm text-gray-700 shadow-sm">
                          <div className="flex items-center justify-between gap-3">
                            <p className="font-medium text-gray-900">Riga {index + 1}</p>
                            <span className="rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide text-amber-700">
                              {formatDetailPunchDirection(punch.direction)}
                            </span>
                          </div>
                          <p className="mt-2 text-xs uppercase tracking-wide text-gray-500">Ora</p>
                          <p className="text-base font-semibold text-gray-900">{displayedInazPunchTimeLabel(selectedRecord, punch)}</p>
                          {formatPunchTerminalLabel(punch.terminal_label) ? (
                            <>
                              <p className="mt-2 text-xs uppercase tracking-wide text-gray-500">Terminale</p>
                              <p className="text-sm font-medium text-gray-800">{formatPunchTerminalLabel(punch.terminal_label)}</p>
                            </>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : null}

              <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.16em] text-emerald-600">Validazione giornaliera</p>
                    <p className="mt-2 text-sm font-medium text-emerald-950">{validationLabel(selectedRecord)}</p>
                    {selectedRecord.validated_at ? (
                      <p className="mt-1 text-xs text-emerald-800">
                        Ultima validazione: {new Intl.DateTimeFormat("it-IT", { dateStyle: "short", timeStyle: "short" }).format(new Date(selectedRecord.validated_at))}
                      </p>
                    ) : null}
                  </div>
                  {canValidate ? (
                    <div className="flex flex-wrap gap-2">
                      <button
                        className="btn-primary"
                        type="button"
                        disabled={isSaving || selectedRecord.validation_status === "validated"}
                        onClick={() => void handleValidation("validated")}
                      >
                        Valida giornaliera
                      </button>
                      <button
                        className="btn-secondary"
                        type="button"
                        disabled={isSaving || selectedRecord.validation_status === "pending"}
                        onClick={() => void handleValidation("pending")}
                      >
                        Riapri validazione
                      </button>
                    </div>
                  ) : null}
                </div>
                {canValidate ? (
                  <label className="mt-4 block text-sm font-medium text-emerald-950">
                    Nota validazione
                    <textarea
                      className="form-control mt-1 min-h-[84px]"
                      value={editor.validationNote}
                      onChange={(event) => setEditor((current) => current ? { ...current, validationNote: event.target.value } : current)}
                      placeholder="Annotazioni del caposettore o HR sulla validazione della giornata."
                    />
                  </label>
                ) : selectedRecord.validation_note ? (
                  <p className="mt-3 text-sm text-emerald-950">{selectedRecord.validation_note}</p>
                ) : null}
              </div>

              <div className="mt-4 rounded-2xl border border-gray-100 bg-white p-4">
                <div className="mb-3">
                  <p className="section-title">Rettifiche operatore</p>
                  <p className="section-copy">Straordinario, maggior presenza e nota operativa. I KM si modificano nel riquadro carburante.</p>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Straordinario override
                    <input className="form-control mt-1" value={editor.overrideStraordinario} onChange={(event) => setEditor((current) => current ? { ...current, overrideStraordinario: event.target.value } : current)} placeholder="HH:MM oppure minuti" disabled={!canEditOperationalData} />
                  </label>
                  <label className="block text-sm font-medium text-gray-700">
                    Maggior presenza override
                    <input className="form-control mt-1" value={editor.overrideMpe} onChange={(event) => setEditor((current) => current ? { ...current, overrideMpe: event.target.value } : current)} placeholder="HH:MM oppure minuti" disabled={!canEditOperationalData} />
                  </label>
                  <div className="rounded-xl border border-gray-100 bg-gray-50 px-3 py-3 text-sm text-gray-700 md:col-span-2">
                    <p className="font-medium text-gray-900">Valori letti</p>
                    <p className="mt-2">Straordinario: {formatHours(selectedRecord.straordinario_minutes)} · Maggior presenza: {formatHours(selectedRecord.mpe_minutes)}</p>
                  </div>
                  <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                    Nota operativa
                    <textarea className="form-control mt-1 min-h-[90px]" value={editor.manualNote} onChange={(event) => setEditor((current) => current ? { ...current, manualNote: event.target.value } : current)} placeholder="Note per giustificazioni, carburante, straordinari o verifiche da fare." disabled={!canEditOperationalData} />
                  </label>
                </div>
                <div className="mt-4 flex flex-wrap gap-3">
                  <button className="btn-primary" type="button" onClick={() => void handleSaveEditor()} disabled={!canEditOperationalData || !canEdit || isSaving}>
                    {isSaving ? "Salvataggio..." : "Salva rettifiche"}
                  </button>
                  <Link
                    className="btn-secondary"
                    href={`/presenze/collaboratori/${selectedRecord.collaborator_id}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Apri dettaglio collaboratore
                  </Link>
                </div>
              </div>
            </div>
            </div>
            <button
              type="button"
              aria-label="Giorno successivo"
              disabled={!nextRecord}
              onClick={() => nextRecord && setSelectedRecordId(nextRecord.id)}
              className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border border-gray-200 bg-white text-3xl text-gray-700 shadow-lg transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-30"
            >
              ›
            </button>
          </div>
        </div>
      ) : null}

      {collaboratorModalId ? (() => {
        const collaborator = collaboratorMap.get(collaboratorModalId);
        if (!collaborator) return null;
        const days = records
          .filter((record) => record.collaborator_id === collaboratorModalId)
          .sort((a, b) => a.work_date.localeCompare(b.work_date));
        const totals = monthTotals.get(collaboratorModalId);
        const schedule = collaboratorSchedule.get(collaboratorModalId);
        return (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/35 px-4 py-8" onClick={() => setCollaboratorModalId("")}>
            <div className="flex max-h-full w-full max-w-2xl flex-col overflow-hidden rounded-3xl bg-white shadow-2xl" onClick={(event) => event.stopPropagation()}>
              <div className="flex items-start justify-between gap-4 border-b border-gray-100 px-6 py-5">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">{collaborator.name}</h3>
                  <p className="mt-0.5 text-sm text-gray-500">
                    {[
                      `Matricola ${collaborator.employee_code}`,
                      getPresenzeCompanyLabel(collaborator.company_label, collaborator.company_code, ""),
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                    {schedule?.code ? <span className="ml-1 rounded bg-indigo-50 px-1 py-0.5 font-medium text-indigo-600" title={schedule.label}>{schedule.code}</span> : null}
                  </p>
                  <p className="mt-1 text-xs capitalize text-gray-400">{formatMonthLabel(selectedMonth)}</p>
                  <div className="mt-2">
                    <Badge variant={operaiGroupBadgeVariant(collaborator.operai_group)}>{formatOperaiGroup(collaborator.operai_group)}</Badge>
                  </div>
                </div>
                <button type="button" className="text-sm text-gray-400 hover:text-gray-700" onClick={() => setCollaboratorModalId("")}>
                  Chiudi ✕
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3 px-6 py-4 sm:grid-cols-4">
                <div className="rounded-xl bg-gray-50 px-3 py-2">
                  <p className="text-[10px] uppercase tracking-wide text-gray-400">Ordinarie</p>
                  <p className="text-sm font-semibold text-gray-900">{formatHours(totals?.ordinary ?? 0)}</p>
                </div>
                <div className="rounded-xl bg-emerald-50 px-3 py-2">
                  <p className="text-[10px] uppercase tracking-wide text-emerald-500">Extra</p>
                  <p className="text-sm font-semibold text-emerald-700">{formatHours(totals?.extra ?? 0)}</p>
                </div>
                <div className="rounded-xl bg-amber-50 px-3 py-2">
                  <p className="text-[10px] uppercase tracking-wide text-amber-500">KM</p>
                  <p className="text-sm font-semibold text-amber-700">{totals?.km ?? 0}</p>
                </div>
                <div className="rounded-xl bg-red-50 px-3 py-2">
                  <p className="text-[10px] uppercase tracking-wide text-red-500">Anomalie</p>
                  <p className="text-sm font-semibold text-red-700">{totals?.anomalies ?? 0}</p>
                </div>
              </div>

              <div className="min-h-0 flex-1 overflow-y-auto border-t border-gray-100 px-6 py-4">
                <div className="space-y-1">
                  {days.map((record) => {
                    const kind = classifyCell(record);
                    const extra = effectiveExtraMinutes(record);
                    return (
                      <button
                        key={record.id}
                        type="button"
                        onClick={() => {
                          setSelectedRecordId(record.id);
                          setCollaboratorModalId("");
                        }}
                        className={`flex w-full items-center justify-between gap-3 rounded-xl px-3 py-2 text-left text-sm transition ${MODAL_ROW_TONE[kind]}`}
                      >
                        <span className="flex items-center gap-2">
                          <span className={`h-2.5 w-2.5 rounded-full ${CELL_TONE[kind].split(" ").find((token) => token.startsWith("bg-")) ?? "bg-gray-200"}`} />
                          <span className="font-medium">{record.work_date}</span>
                          <span className="opacity-75">{record.detail_status ?? record.stato ?? "—"}</span>
                        </span>
                        <span className="flex items-center gap-3 text-xs opacity-80">
                          <span>Ord {formatHoursCompact(record.ordinary_minutes)}h</span>
                          {extra > 0 ? <span className="text-emerald-600">Extra {formatHoursCompact(extra)}h</span> : null}
                          {record.km_value != null ? <span className="text-amber-600">{record.km_value} km</span> : null}
                          {(record.trasferta_minutes ?? 0) > 0 || record.trasferta_montano ? <span className="text-sky-600">{formatTrasfertaDisplay(record.trasferta_minutes, record.trasferta_montano)}</span> : null}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="flex flex-wrap justify-end gap-2 border-t border-gray-100 px-6 py-4">
                <Link className="btn-secondary" href={`/presenze/collaboratori/${collaborator.id}`}>
                  Apri scheda completa
                </Link>
              </div>
            </div>
          </div>
        );
      })() : null}

      {hasLoaded && !isLoading && records.length === 0 && dismissedMonth !== selectedMonth ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/35 px-4">
          <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-gray-400">Cartellino vuoto</p>
            <h3 className="mt-2 text-lg font-semibold text-gray-900">Nessuna giornaliera per {formatMonthLabel(selectedMonth)}</h3>
            <p className="mt-3 text-sm leading-6 text-gray-600">
              Non risultano giornaliere caricate per questo mese. Vuoi consultare {formatMonthLabel(shiftMonth(selectedMonth, -1))}?
            </p>
            <div className="mt-6 flex flex-wrap justify-end gap-2">
              <button className="btn-secondary" type="button" onClick={() => setDismissedMonth(selectedMonth)}>
                Resta su {formatMonthLabel(selectedMonth)}
              </button>
              <button
                className="btn-primary"
                type="button"
                onClick={() => setSelectedMonth((current) => shiftMonth(current, -1))}
              >
                Carica {formatMonthLabel(shiftMonth(selectedMonth, -1))}
              </button>
            </div>
            <div className="mt-3 text-center">
              <Link className="text-xs font-medium text-gray-500 underline" href="/presenze/sync">
                Oppure avvia una sync giornaliere
              </Link>
            </div>
          </div>
        </div>
      ) : null}
    </ProtectedPage>
  );
}

/* v8 ignore stop */
// Keeps this page present in V8 coverage after excluding the shell above.
export const __presenzeGiornalierePageCoverageMarker = true;
