"use client";

import Link from "next/link";
import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { ProtectedPage } from "@/components/app/protected-page";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/table/data-table";
import {
  getCurrentUser,
  getPresenzeAnomalyMonthSummary,
  getPresenzeDailyRecord,
  listPresenzeAnomalyRecords,
  listPresenzeCollaborators,
  updatePresenzeDailyRecord,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import {
  currentMonthValue,
  monthBounds,
  monthLabel,
  previousMonthValue,
  shouldAutoLoadPreviousMonth,
  summarizeMonthsWithAnomalies,
  type MonthAnomalySummary,
} from "@/lib/presenze-anomaly-months";
import type { CurrentUser, PresenzeAnomalyListItem, PresenzeCollaborator, PresenzeDailyRecord } from "@/types/api";

type DailyEditForm = {
  kmValue: string;
  trasfertaMinutes: string;
  trasfertaMontano: boolean;
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

export default function PresenzeAnomaliePage() {
  const calendarMonth = useMemo(() => currentMonthValue(), []);
  const initialFallbackApplied = useRef(false);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [records, setRecords] = useState<PresenzeAnomalyListItem[]>([]);
  const [collaborators, setCollaborators] = useState<PresenzeCollaborator[]>([]);
  const [selectedMonth, setSelectedMonth] = useState(calendarMonth);
  const [monthsWithAnomalies, setMonthsWithAnomalies] = useState<MonthAnomalySummary[]>([]);
  const [isScanningMonths, setIsScanningMonths] = useState(false);
  const [hasScannedMonths, setHasScannedMonths] = useState(false);
  const [autoFallbackFromMonth, setAutoFallbackFromMonth] = useState<string | null>(null);
  const [selectedCollaboratorId, setSelectedCollaboratorId] = useState("");
  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search.trim());
  const [onlyAnomalies, setOnlyAnomalies] = useState(true);
  const [onlyRequests, setOnlyRequests] = useState(false);
  const [selectedRecordId, setSelectedRecordId] = useState("");
  const [recordDetails, setRecordDetails] = useState<Record<string, PresenzeDailyRecord>>({});
  const [editor, setEditor] = useState<DailyEditForm | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingRows, setIsLoadingRows] = useState(false);
  const [isLoadingRecordDetail, setIsLoadingRecordDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    getCurrentUser(token)
      .then(async (sessionUser) => {
        setCurrentUser(sessionUser);
        const collaboratorResponse = await listPresenzeCollaborators(token, { page: 1, pageSize: 200 });
        setCollaborators(collaboratorResponse.items);
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento anomalie"));
  }, []);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    const { start, end } = monthBounds(selectedMonth);
    setIsLoadingRows(true);
    setError(null);
    listPresenzeAnomalyRecords(token, {
      dateFrom: start,
      dateTo: end,
      collaboratorId: selectedCollaboratorId || undefined,
      q: deferredSearch || undefined,
      onlyAnomalies,
      onlyRequests,
      page: 1,
      pageSize: 5000,
    })
      .then((response) => {
        const anomalyCount = response.items.filter((item) => item.has_anomalies).length;
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
        setRecords(response.items);
        setRecordDetails({});
        setSelectedRecordId("");
        setMonthsWithAnomalies((current) =>
          summarizeMonthsWithAnomalies([
            ...current.filter((entry) => entry.month !== selectedMonth),
            { month: selectedMonth, count: anomalyCount },
          ]),
        );
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento anomalie"))
      .finally(() => setIsLoadingRows(false));
  }, [calendarMonth, deferredSearch, onlyAnomalies, onlyRequests, selectedCollaboratorId, selectedMonth]);

  async function handleScanMonths() {
    const token = getStoredAccessToken();
    if (!token) return;
    setIsScanningMonths(true);
    setError(null);
    try {
      const response = await getPresenzeAnomalyMonthSummary(token, {
        months: MONTHS_TO_SCAN,
        anchorMonth: calendarMonth,
        collaboratorId: selectedCollaboratorId || undefined,
      });
      setMonthsWithAnomalies(summarizeMonthsWithAnomalies(response.items));
      setHasScannedMonths(true);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore scansione mesi con anomalie");
    } finally {
      setIsScanningMonths(false);
    }
  }

  const collaboratorMap = useMemo(() => new Map(collaborators.map((item) => [item.id, item])), [collaborators]);

  const selectedRecord = useMemo(() => {
    const explicit = selectedRecordId ? (recordDetails[selectedRecordId] ?? null) : null;
    if (explicit) {
      return explicit;
    }
    if (!selectedRecordId) return null;
    return null;
  }, [recordDetails, selectedRecordId]);

  const selectedRow = useMemo(
    () => (selectedRecordId ? records.find((record) => record.id === selectedRecordId) ?? null : null),
    [records, selectedRecordId],
  );

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
  const otherMonthsWithAnomalies = useMemo(
    () => monthsWithAnomalies.filter((entry) => entry.month !== selectedMonth),
    [monthsWithAnomalies, selectedMonth],
  );
  const showMonthNavigation = Boolean(autoFallbackFromMonth) || otherMonthsWithAnomalies.length > 0 || isScanningMonths || hasScannedMonths;
  const totalAnomalyRows = useMemo(() => records.filter((row) => row.has_anomalies).length, [records]);
  const totalRequestRows = useMemo(() => records.filter((row) => row.has_requests).length, [records]);
  const totalSpecialRows = useMemo(() => records.filter((row) => row.special_day).length, [records]);

  async function handleSave() {
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
      });
      setRecords((current) =>
        current.map((item) =>
          item.id === updated.id
            ? {
                ...item,
                km_value: updated.km_value,
              }
            : item,
        ),
      );
      setRecordDetails((current) => ({ ...current, [updated.id]: updated }));
      setSuccess(`Giornata ${updated.work_date} aggiornata.`);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Errore salvataggio giornaliera");
    } finally {
      setIsSaving(false);
    }
  }

  const columns = useMemo<ColumnDef<PresenzeAnomalyListItem>[]>(
    () => [
      { header: "Data", accessorKey: "work_date" },
      {
        header: "Collaboratore",
        accessorKey: "collaborator_name",
        cell: ({ row }) => (
          <div>
            <p className="font-medium text-gray-900">{row.original.collaborator_name}</p>
            <p className="text-xs text-gray-500">
              {row.original.collaborator_code} · {row.original.company}
            </p>
          </div>
        ),
      },
      {
        header: "Stato",
        accessorKey: "status",
        cell: ({ row }) => (
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={row.original.has_anomalies ? "danger" : row.original.special_day ? "warning" : "neutral"}>
              {row.original.status ?? "—"}
            </Badge>
            {row.original.has_requests ? <Badge variant="neutral">richieste</Badge> : null}
            {row.original.special_day ? <Badge variant="warning">speciale</Badge> : null}
          </div>
        ),
      },
      { header: "Orario", accessorKey: "programmed_schedule" },
      {
        header: "Evidenze",
        accessorKey: "evidenze",
        cell: ({ row }) => <span className="text-sm text-gray-600">{row.original.evidenze ?? "—"}</span>,
      },
    ],
    [],
  );

  return (
    <ProtectedPage title="Analisi anomalie giornaliere" description="Giornate con anomalie, richieste o eventi speciali da gestire." breadcrumb="Giornaliere" requiredModule="presenze">
      <div className="space-y-6">
        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        {success ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div> : null}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-gray-500">
            Questa schermata raccoglie le giornate che richiedono una verifica. Per la consultazione mensile a matrice usa{" "}
            <Link className="font-medium text-gray-900 underline" href="/presenze/giornaliere">Giornaliere</Link>.
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
            {!isScanningMonths && !hasScannedMonths ? (
              <div className={autoFallbackFromMonth || monthsWithAnomalies.length > 0 ? "mt-3" : undefined}>
                <button type="button" className="btn-secondary" onClick={() => void handleScanMonths()}>
                  Cerca anomalie negli ultimi {MONTHS_TO_SCAN} mesi
                </button>
              </div>
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
            <p className="section-copy">Filtri applicati lato backend: mese, collaboratore, testo, anomalie e richieste.</p>
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
                <p className="section-copy">Lista light caricata dal backend dedicato alle anomalie.</p>
              </div>
              <div className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
                {isLoadingRows ? "Caricamento..." : `${records.length} righe`}
              </div>
            </div>
            <DataTable data={records} columns={columns} initialPageSize={20} onRowClick={(row) => setSelectedRecordId(row.id)} />
          </article>

          <article className="panel-card">
            {selectedRecord && editor ? (
              <div className="space-y-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="section-title">{selectedRecord.work_date}</p>
                    <p className="section-copy">
                      {selectedRow?.collaborator_name ?? collaboratorMap.get(selectedRecord.collaborator_id)?.name ?? selectedRecord.collaborator_id} ·{" "}
                      {selectedRecord.detail_programmed_schedule ?? selectedRecord.schedule_code ?? "Orario non disponibile"}
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
                    <p className="section-copy">Modifica i campi necessari per l’operativita: KM carburante, trasferta, straordinario, maggior presenza e nota.</p>
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    <label className="block text-sm font-medium text-gray-700">
                      KM carburante
                      <input className="form-control mt-1" value={editor.kmValue} onChange={(event) => setEditor((current) => current ? { ...current, kmValue: event.target.value } : current)} placeholder="Es. 24" />
                    </label>
                    <div className="block text-sm font-medium text-gray-700">
                      Trasferta
                      <input className="form-control mt-1" value={editor.trasfertaMinutes} onChange={(event) => setEditor((current) => current ? { ...current, trasfertaMinutes: event.target.value } : current)} placeholder="HH:MM oppure minuti" />
                      <label className="mt-2 flex items-center gap-2 text-sm font-medium text-gray-700">
                        <input
                          type="checkbox"
                          checked={editor.trasfertaMontano}
                          onChange={(event) =>
                            setEditor((current) =>
                              current ? { ...current, trasfertaMontano: event.target.checked } : current,
                            )
                          }
                          aria-label="Comune montano"
                        />
                        <span>Comune montano</span>
                      </label>
                    </div>
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
                      <p className="font-medium text-gray-900">Valori letti</p>
                      <p className="mt-2">Straordinario: {formatHours(selectedRecord.straordinario_minutes)}</p>
                      <p>Maggior presenza: {formatHours(selectedRecord.mpe_minutes)}</p>
                      <p>KM registrati: {selectedRecord.km_value ?? "—"}</p>
                      <p>Trasferta: {formatTrasfertaDisplay(selectedRecord.trasferta_minutes, selectedRecord.trasferta_montano)}</p>
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
                  <Link className="btn-secondary" href={`/presenze/collaboratori/${selectedRecord.collaborator_id}`}>
                    Apri dettaglio collaboratore
                  </Link>
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-6 py-10 text-center text-sm text-gray-500">
                {isLoadingRows ? "Caricamento anomalie..." : "Seleziona una giornata per aprire il pannello operativo."}
              </div>
            )}
          </article>
        </section>
      </div>
    </ProtectedPage>
  );
}
