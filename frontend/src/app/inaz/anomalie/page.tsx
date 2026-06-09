"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { ProtectedPage } from "@/components/app/protected-page";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/table/data-table";
import { getCurrentUser, getInazDailyRecord, listInazCollaborators, listInazDailyRecords, updateInazDailyRecord } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { getInazCompanyLabel } from "@/lib/inaz-display";
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
  type MonthAnomalySummary,
} from "@/lib/inaz-anomaly-months";
import type { CurrentUser, InazCollaborator, InazDailyRecord } from "@/types/api";

type DailyRow = {
  id: string;
  workDate: string;
  collaboratorId: string;
  collaborator: string;
  collaboratorCode: string;
  company: string;
  scheduleCode: string;
  programmedSchedule: string;
  status: string;
  timeSlots: string;
  ordinaryMinutes: number | null;
  absenceMinutes: number | null;
  effectiveExtraMinutes: number;
  kmValue: number | null;
  specialDay: boolean;
  hasAnomalies: boolean;
  hasRequests: boolean;
  evidenze: string;
  summary: string;
};

type DailyEditForm = {
  kmValue: string;
  reperibilitaGiornaliera: boolean;
  overrideStraordinario: string;
  overrideMpe: string;
  manualNote: string;
};

const MONTHS_TO_SCAN = 12;

function formatHours(minutes: number | null): string {
  if (minutes == null) return "—";
  return `${(minutes / 60).toFixed(2)} h`;
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

function formatReperibilitaDisplay(unit: InazDailyRecord["reperibilita_unit"], quantity: number | null): string {
  if (unit === "none") return "Nessuna";
  if (unit === "days" && (quantity ?? 0) > 0) return "Giornaliera";
  const labels: Record<Exclude<InazDailyRecord["reperibilita_unit"], "none">, string> = {
    hours: "ore",
    days: "giorni",
    shifts: "turni",
  };
  return `${quantity ?? "—"} ${labels[unit]}`;
}

function summarizeMap(values: Record<string, string>): string {
  const entries = Object.entries(values);
  if (entries.length === 0) return "—";
  return entries
    .slice(0, 3)
    .map(([label, value]) => `${label}: ${value}`)
    .join(" · ");
}

async function listAllDailyRecords(
  token: string,
  params: { dateFrom: string; dateTo: string; collaboratorId?: string; q?: string; applicationUserId?: number; includePunches?: boolean },
) {
  const pageSize = 200;
  let page = 1;
  let items: InazDailyRecord[] = [];
  let total = 0;

  while (true) {
    const response = await listInazDailyRecords(token, { ...params, page, pageSize });
    items = [...items, ...response.items];
    total = response.total;
    if (items.length >= total || response.items.length === 0) {
      return items;
    }
    page += 1;
  }
}

export default function InazAnomaliePage() {
  const calendarMonth = useMemo(() => currentMonthValue(), []);
  const initialFallbackApplied = useRef(false);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [records, setRecords] = useState<InazDailyRecord[]>([]);
  const [collaborators, setCollaborators] = useState<InazCollaborator[]>([]);
  const [selectedMonth, setSelectedMonth] = useState(calendarMonth);
  const [monthsWithAnomalies, setMonthsWithAnomalies] = useState<MonthAnomalySummary[]>([]);
  const [isScanningMonths, setIsScanningMonths] = useState(false);
  const [autoFallbackFromMonth, setAutoFallbackFromMonth] = useState<string | null>(null);
  const [selectedCollaboratorId, setSelectedCollaboratorId] = useState("");
  const [search, setSearch] = useState("");
  const [onlyAnomalies, setOnlyAnomalies] = useState(true);
  const [onlyRequests, setOnlyRequests] = useState(false);
  const [selectedRecordId, setSelectedRecordId] = useState("");
  const [recordDetails, setRecordDetails] = useState<Record<string, InazDailyRecord>>({});
  const [editor, setEditor] = useState<DailyEditForm | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingRecordDetail, setIsLoadingRecordDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    getCurrentUser(token)
      .then(async (sessionUser) => {
        setCurrentUser(sessionUser);
        const collaboratorResponse = await listInazCollaborators(token, { page: 1, pageSize: 200 });
        setCollaborators(collaboratorResponse.items);
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento anomalie"));
  }, []);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    const { start, end } = monthBounds(selectedMonth);
    listAllDailyRecords(token, { dateFrom: start, dateTo: end, includePunches: false })
      .then((dailyItems) => {
        const anomalyCount = countAnomaliesInRecords(dailyItems);
        if (
          shouldAutoLoadPreviousMonth({
            selectedMonth,
            calendarMonth,
            anomalyCount,
            alreadyApplied: initialFallbackApplied.current,
          })
        ) {
          initialFallbackApplied.current = true;
          const previousMonth = previousMonthValue(calendarMonth);
          setAutoFallbackFromMonth(calendarMonth);
          setSelectedMonth(previousMonth);
          return;
        }
        initialFallbackApplied.current = true;
        setRecords(dailyItems);
        setRecordDetails({});
        setSelectedRecordId("");
        setMonthsWithAnomalies((current) =>
          summarizeMonthsWithAnomalies(
            current.map((entry) => (entry.month === selectedMonth ? { month: selectedMonth, count: anomalyCount } : entry)),
          ),
        );
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento anomalie"));
  }, [selectedMonth, calendarMonth]);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    let cancelled = false;
    setIsScanningMonths(true);
    void Promise.all(
      recentMonths(MONTHS_TO_SCAN, calendarMonth).map(async (month) => {
        const { start, end } = monthBounds(month);
        const dailyItems = await listAllDailyRecords(token, { dateFrom: start, dateTo: end, includePunches: false });
        return { month, count: countAnomaliesInRecords(dailyItems) };
      }),
    )
      .then((entries) => {
        if (!cancelled) {
          setMonthsWithAnomalies(summarizeMonthsWithAnomalies(entries));
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Errore scansione mesi con anomalie");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsScanningMonths(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [calendarMonth]);

  const collaboratorMap = useMemo(() => new Map(collaborators.map((item) => [item.id, item])), [collaborators]);

  const rows = useMemo<DailyRow[]>(
    () =>
      records.map((record) => {
        const collaborator = collaboratorMap.get(record.collaborator_id);
        const effectiveExtra = record.effective_extra_minutes ?? (record.effective_straordinario_minutes ?? record.straordinario_minutes ?? 0) + (record.effective_mpe_minutes ?? record.mpe_minutes ?? 0);
        return {
          id: record.id,
          collaboratorId: record.collaborator_id,
          workDate: record.work_date,
          collaborator: collaborator?.name ?? record.collaborator_id,
          collaboratorCode: collaborator?.employee_code ?? "—",
          company: getInazCompanyLabel(collaborator?.company_label, collaborator?.company_code, "—"),
          scheduleCode: record.schedule_code ?? "—",
          programmedSchedule: record.detail_programmed_schedule ?? "—",
          status: record.detail_status ?? record.stato ?? "—",
          timeSlots: record.detail_time_slots ?? "—",
          ordinaryMinutes: record.ordinary_minutes,
          absenceMinutes: record.absence_minutes,
          effectiveExtraMinutes: effectiveExtra,
          kmValue: record.km_value,
          specialDay: Boolean(record.special_day),
          hasAnomalies: recordHasAnomaly(record),
          hasRequests: record.detail_requests.length > 0,
          evidenze: record.evidenze ?? "—",
          summary: summarizeMap(record.detail_day_summary),
        };
      }),
    [records, collaboratorMap],
  );

  const filteredRows = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return rows.filter((row) => {
      const matchesCollaborator = !selectedCollaboratorId || row.collaboratorId === selectedCollaboratorId;
      const matchesSearch =
        !normalizedSearch ||
        [
          row.collaborator,
          row.collaboratorCode,
          row.company,
          row.scheduleCode,
          row.programmedSchedule,
          row.status,
          row.evidenze,
          row.summary,
          row.workDate,
          row.timeSlots,
        ].some((value) => value.toLowerCase().includes(normalizedSearch));
      const matchesAnomalies = !onlyAnomalies || row.hasAnomalies;
      const matchesRequests = !onlyRequests || row.hasRequests;
      return matchesCollaborator && matchesSearch && matchesAnomalies && matchesRequests;
    });
  }, [rows, search, selectedCollaboratorId, onlyAnomalies, onlyRequests]);

  const selectedRecord = useMemo(() => {
    const explicit = selectedRecordId
      ? (recordDetails[selectedRecordId] ?? records.find((record) => record.id === selectedRecordId))
      : null;
    if (explicit) {
      return explicit;
    }
    if (filteredRows.length === 0) return null;
    const fallbackId = filteredRows[0]?.id;
    return (fallbackId ? recordDetails[fallbackId] : null) ?? records.find((record) => record.id === fallbackId) ?? null;
  }, [recordDetails, records, selectedRecordId, filteredRows]);

  useEffect(() => {
    if (!selectedRecord) {
      setEditor(null);
      return;
    }
    setEditor({
      kmValue: selectedRecord.km_value != null ? String(selectedRecord.km_value) : "",
      reperibilitaGiornaliera: selectedRecord.reperibilita_unit !== "none" && (selectedRecord.reperibilita_quantity ?? 0) > 0,
      overrideStraordinario: formatMinutesInput(selectedRecord.override_straordinario_minutes),
      overrideMpe: formatMinutesInput(selectedRecord.override_mpe_minutes),
      manualNote: selectedRecord.manual_note ?? "",
    });
  }, [selectedRecord]);

  useEffect(() => {
    const token = getStoredAccessToken();
    const targetId = selectedRecordId || filteredRows[0]?.id;
    if (!token || !targetId || recordDetails[targetId]) return;
    setIsLoadingRecordDetail(true);
    getInazDailyRecord(token, targetId)
      .then((detail) => {
        setRecordDetails((current) => ({ ...current, [detail.id]: detail }));
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento dettaglio giornaliera"))
      .finally(() => setIsLoadingRecordDetail(false));
  }, [filteredRows, recordDetails, selectedRecordId]);

  const canEdit = Boolean(currentUser);
  const otherMonthsWithAnomalies = useMemo(
    () => monthsWithAnomalies.filter((entry) => entry.month !== selectedMonth),
    [monthsWithAnomalies, selectedMonth],
  );
  const showMonthNavigation = Boolean(autoFallbackFromMonth) || otherMonthsWithAnomalies.length > 0 || isScanningMonths;
  const totalAnomalyRows = useMemo(() => rows.filter((row) => row.hasAnomalies).length, [rows]);
  const totalRequestRows = useMemo(() => rows.filter((row) => row.hasRequests).length, [rows]);
  const totalSpecialRows = useMemo(() => rows.filter((row) => row.specialDay).length, [rows]);

  async function handleSave() {
    const token = getStoredAccessToken();
    if (!token || !selectedRecord || !editor) return;
    setIsSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateInazDailyRecord(token, selectedRecord.id, {
        km_value: editor.kmValue.trim() ? Number(editor.kmValue) : null,
        reperibilita_unit: editor.reperibilitaGiornaliera ? "days" : "none",
        reperibilita_quantity: editor.reperibilitaGiornaliera ? 1 : null,
        override_straordinario_minutes: parseMinutesInput(editor.overrideStraordinario),
        override_mpe_minutes: parseMinutesInput(editor.overrideMpe),
        manual_note: editor.manualNote.trim() || null,
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

  const columns = useMemo<ColumnDef<DailyRow>[]>(
    () => [
      { header: "Data", accessorKey: "workDate" },
      {
        header: "Collaboratore",
        accessorKey: "collaborator",
        cell: ({ row }) => (
          <div>
            <p className="font-medium text-gray-900">{row.original.collaborator}</p>
            <p className="text-xs text-gray-500">
              {row.original.collaboratorCode} · {row.original.company}
            </p>
          </div>
        ),
      },
      {
        header: "Stato",
        accessorKey: "status",
        cell: ({ row }) => (
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={row.original.hasAnomalies ? "danger" : row.original.specialDay ? "warning" : "neutral"}>
              {row.original.status}
            </Badge>
            {row.original.hasRequests ? <Badge variant="neutral">richieste</Badge> : null}
            {row.original.specialDay ? <Badge variant="warning">speciale</Badge> : null}
          </div>
        ),
      },
      { header: "Orario", accessorKey: "programmedSchedule" },
      {
        header: "Evidenze",
        accessorKey: "evidenze",
        cell: ({ row }) => <span className="text-sm text-gray-600">{row.original.evidenze}</span>,
      },
    ],
    [],
  );

  return (
    <ProtectedPage title="Analisi anomalie Inaz" description="Giornate con anomalie, richieste o eventi speciali da gestire." breadcrumb="Inaz" requiredModule="inaz">
      <div className="space-y-6">
        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        {success ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div> : null}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-gray-500">
            Questa schermata raccoglie le giornate che richiedono una verifica. Per la consultazione mensile a matrice usa{" "}
            <Link className="font-medium text-gray-900 underline" href="/inaz/giornaliere">Giornaliere</Link>.
          </p>
        </div>

        {showMonthNavigation ? (
          <article className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4">
            {autoFallbackFromMonth ? (
              <p className="text-sm text-amber-950">
                Nessuna anomalia in <span className="font-medium">{monthLabel(autoFallbackFromMonth)}</span>. Visualizzazione di{" "}
                <span className="font-medium">{monthLabel(selectedMonth)}</span>.
              </p>
            ) : null}
            {otherMonthsWithAnomalies.length > 0 || monthsWithAnomalies.some((entry) => entry.month === selectedMonth) ? (
              <div className={autoFallbackFromMonth ? "mt-3" : undefined}>
                <p className="text-xs font-medium uppercase tracking-[0.16em] text-amber-800">Collegamenti rapidi per mese</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {monthsWithAnomalies.map((entry) => (
                    <button
                      key={entry.month}
                      type="button"
                      className={
                        entry.month === selectedMonth
                          ? "rounded-full bg-amber-900 px-3 py-1.5 text-xs font-medium text-white"
                          : "rounded-full border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-950 hover:bg-amber-100"
                      }
                      onClick={() => {
                        setAutoFallbackFromMonth(null);
                        setSelectedMonth(entry.month);
                      }}
                    >
                      {monthLabel(entry.month)} ({entry.count})
                    </button>
                  ))}
                </div>
              </div>
            ) : isScanningMonths ? (
              <p className="text-sm text-amber-900">Ricerca anomalie nei mesi precedenti…</p>
            ) : null}
          </article>
        ) : null}

        <section className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-2xl border border-gray-100 bg-white p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Anomalie</p>
            <p className="mt-2 text-2xl font-semibold text-red-700">{totalAnomalyRows}</p>
            <p className="text-xs text-gray-500">giornate con alert</p>
          </div>
          <div className="rounded-2xl border border-gray-100 bg-white p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Richieste</p>
            <p className="mt-2 text-2xl font-semibold text-gray-900">{totalRequestRows}</p>
            <p className="text-xs text-gray-500">giornate con richieste</p>
          </div>
          <div className="rounded-2xl border border-gray-100 bg-white p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Giorni speciali</p>
            <p className="mt-2 text-2xl font-semibold text-amber-700">{totalSpecialRows}</p>
            <p className="text-xs text-gray-500">festivi / fuori orario</p>
          </div>
        </section>

        <article className="panel-card">
          <div className="mb-4">
            <p className="section-title">Filtri analisi</p>
            <p className="section-copy">Ricerca rapida per collaboratore, stato giornata, orario Inaz, anomalie o richieste.</p>
          </div>
          <div className="grid gap-4 lg:grid-cols-4">
            <label className="block text-sm font-medium text-gray-700">
              Mese operativo
              <input
                className="form-control mt-1"
                type="month"
                value={selectedMonth}
                onChange={(event) => {
                  setAutoFallbackFromMonth(null);
                  setSelectedMonth(event.target.value);
                }}
              />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Collaboratore
              <select className="form-control mt-1" value={selectedCollaboratorId} onChange={(event) => setSelectedCollaboratorId(event.target.value)}>
                <option value="">Tutti</option>
                {collaborators.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name} ({item.employee_code})
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-medium text-gray-700 lg:col-span-2">
              Cerca
              <input className="form-control mt-1" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Es. Permesso, OPESAB, 2026-05-16, ferie, anomalia" />
            </label>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="flex items-center gap-2 rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700">
                <input checked={onlyAnomalies} onChange={(event) => setOnlyAnomalies(event.target.checked)} type="checkbox" />
                Solo anomalie
              </label>
              <label className="flex items-center gap-2 rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700">
                <input checked={onlyRequests} onChange={(event) => setOnlyRequests(event.target.checked)} type="checkbox" />
                Solo richieste
              </label>
            </div>
          </div>
        </article>

        <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <article className="panel-card">
            <div className="mb-4 flex items-center justify-between gap-4">
              <div>
                <p className="section-title">Giornate da verificare</p>
                <p className="section-copy">Clicca una riga per aprire il pannello operativo della giornata.</p>
              </div>
              <div className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
                {filteredRows.length} righe
              </div>
            </div>
            <DataTable data={filteredRows} columns={columns} initialPageSize={20} onRowClick={(row) => setSelectedRecordId(row.id)} />
          </article>

          <article className="panel-card">
            {selectedRecord && editor ? (
              <div className="space-y-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="section-title">{selectedRecord.work_date}</p>
                    <p className="section-copy">
                      {collaboratorMap.get(selectedRecord.collaborator_id)?.name ?? selectedRecord.collaborator_id} · {selectedRecord.detail_programmed_schedule ?? selectedRecord.schedule_code ?? "Orario non disponibile"}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant={selectedRecord.detail_anomalies.length > 0 || selectedRecord.detail_error ? "danger" : selectedRecord.special_day ? "warning" : "neutral"}>
                      {selectedRecord.detail_status ?? selectedRecord.stato ?? "n/d"}
                    </Badge>
                    {selectedRecord.special_day ? <Badge variant="warning">giorno speciale</Badge> : null}
                    {selectedRecord.effective_extra_minutes ? <Badge variant="success">extra {formatHours(selectedRecord.effective_extra_minutes)}</Badge> : null}
                  </div>
                </div>

                {(selectedRecord.detail_anomalies.length > 0 || selectedRecord.detail_error) ? (
                  <div className="rounded-2xl border border-red-200 bg-red-50 p-4">
                    <p className="section-title text-red-900">Anomalie da gestire</p>
                    <div className="mt-3 space-y-2 text-sm text-red-900">
                      {selectedRecord.detail_anomalies.map((anomaly, index) => (
                        <div key={`${selectedRecord.id}-anomaly-${index}`} className="rounded-xl border border-red-100 bg-white/70 px-3 py-2">
                          {Object.entries(anomaly).map(([label, value]) => (
                            <p key={label}>
                              <span className="font-medium">{label}:</span> {value}
                            </p>
                          ))}
                        </div>
                      ))}
                      {selectedRecord.detail_error ? <p>{selectedRecord.detail_error}</p> : null}
                    </div>
                  </div>
                ) : null}

                <div className="rounded-2xl border border-gray-100 bg-white p-4">
                  <div className="mb-3">
                    <p className="section-title">Rettifiche operatore</p>
                    <p className="section-copy">Modifica i campi necessari per l’operativita: KM carburante, straordinario, maggior presenza e nota.</p>
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    <label className="block text-sm font-medium text-gray-700">
                      KM carburante
                      <input className="form-control mt-1" value={editor.kmValue} onChange={(event) => setEditor((current) => current ? { ...current, kmValue: event.target.value } : current)} placeholder="Es. 24" />
                    </label>
                    <label className="block text-sm font-medium text-gray-700">
                      Reperibilita giornaliera
                      <label className="mt-2 flex items-center gap-2 text-sm font-medium text-gray-700">
                        <input
                          type="checkbox"
                          checked={editor.reperibilitaGiornaliera}
                          onChange={(event) =>
                            setEditor((current) =>
                              current ? { ...current, reperibilitaGiornaliera: event.target.checked } : current,
                            )
                          }
                          aria-label="Reperibilita giornaliera"
                        />
                        <span>Segna reperibilita per l&apos;intera giornata</span>
                      </label>
                    </label>
                    <label className="block text-sm font-medium text-gray-700">
                      Straordinario override
                      <input className="form-control mt-1" value={editor.overrideStraordinario} onChange={(event) => setEditor((current) => current ? { ...current, overrideStraordinario: event.target.value } : current)} placeholder="HH:MM oppure minuti" />
                    </label>
                    <label className="block text-sm font-medium text-gray-700">
                      Maggior presenza override
                      <input className="form-control mt-1" value={editor.overrideMpe} onChange={(event) => setEditor((current) => current ? { ...current, overrideMpe: event.target.value } : current)} placeholder="HH:MM oppure minuti" />
                    </label>
                    <div className="rounded-xl border border-gray-100 bg-gray-50 px-3 py-3 text-sm text-gray-700">
                      <p className="font-medium text-gray-900">Valori Inaz letti</p>
                      <p className="mt-2">Straordinario: {formatHours(selectedRecord.straordinario_minutes)}</p>
                      <p>Maggior presenza: {formatHours(selectedRecord.mpe_minutes)}</p>
                      <p>KM registrati: {selectedRecord.km_value ?? "—"}</p>
                      <p>
                        Reperibilita:{" "}
                        {formatReperibilitaDisplay(selectedRecord.reperibilita_unit, selectedRecord.reperibilita_quantity)}
                      </p>
                    </div>
                    <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                      Nota operativa
                      <textarea className="form-control mt-1 min-h-[110px]" value={editor.manualNote} onChange={(event) => setEditor((current) => current ? { ...current, manualNote: event.target.value } : current)} placeholder="Note per giustificazioni, carburante, straordinari o verifiche da fare." />
                    </label>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <button className="btn-primary" type="button" onClick={() => void handleSave()} disabled={!canEdit || isSaving}>
                      {isSaving ? "Salvataggio..." : "Salva rettifiche"}
                    </button>
                  </div>
                </div>

                <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                  <p className="section-title">Richieste e timbrature</p>
                  <div className="mt-3 space-y-3 text-sm text-gray-700">
                    {selectedRecord.punches.length > 0 ? (
                      <div className="rounded-xl border border-white bg-white px-3 py-2">
                        {selectedRecord.punches.map((punch) => (
                          <p key={punch.id}>
                            Timbratura {punch.sequence}: <span className="font-medium text-gray-900">{punch.entry_time ?? "—"} / {punch.exit_time ?? "—"}</span>
                          </p>
                        ))}
                      </div>
                    ) : isLoadingRecordDetail ? (
                      <p className="text-sm text-gray-500">Caricamento timbrature…</p>
                    ) : null}
                    {selectedRecord.detail_requests.length > 0 ? (
                      selectedRecord.detail_requests.map((request, index) => (
                        <div key={`${selectedRecord.id}-request-${index}`} className="rounded-xl border border-white bg-white px-3 py-2">
                          {Object.entries(request).map(([label, value]) => (
                            <p key={label}>
                              <span className="font-medium text-gray-900">{label}:</span> {value}
                            </p>
                          ))}
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-gray-500">Nessuna richiesta registrata.</p>
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap gap-3">
                  <Link className="btn-secondary" href={`/inaz/collaboratori/${selectedRecord.collaborator_id}`}>
                    Apri dettaglio collaboratore
                  </Link>
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-6 py-10 text-center text-sm text-gray-500">
                Nessuna giornata da verificare con i filtri correnti.
              </div>
            )}
          </article>
        </section>
      </div>
    </ProtectedPage>
  );
}
