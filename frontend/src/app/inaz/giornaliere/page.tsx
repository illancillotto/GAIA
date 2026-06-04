"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { ProtectedPage } from "@/components/app/protected-page";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/table/data-table";
import { getCurrentUser, listInazCollaborators, listInazDailyRecords, updateInazDailyRecord } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
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
  overrideStraordinario: string;
  overrideMpe: string;
  manualNote: string;
};

function currentMonthValue(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function monthBounds(monthValue: string): { start: string; end: string } {
  const [yearString, monthString] = monthValue.split("-");
  const year = Number(yearString);
  const month = Number(monthString);
  const start = `${yearString}-${monthString}-01`;
  const end = `${yearString}-${monthString}-${String(new Date(year, month, 0).getDate()).padStart(2, "0")}`;
  return { start, end };
}

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

function summarizeMap(values: Record<string, string>): string {
  const entries = Object.entries(values);
  if (entries.length === 0) return "—";
  return entries
    .slice(0, 3)
    .map(([label, value]) => `${label}: ${value}`)
    .join(" · ");
}

async function listAllDailyRecords(token: string, params: { dateFrom: string; dateTo: string; collaboratorId?: string; q?: string; applicationUserId?: number }) {
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

export default function InazGiornalierePage() {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [records, setRecords] = useState<InazDailyRecord[]>([]);
  const [collaborators, setCollaborators] = useState<InazCollaborator[]>([]);
  const [selectedMonth, setSelectedMonth] = useState(currentMonthValue());
  const [selectedCollaboratorId, setSelectedCollaboratorId] = useState("");
  const [search, setSearch] = useState("");
  const [onlyAnomalies, setOnlyAnomalies] = useState(false);
  const [onlyExtra, setOnlyExtra] = useState(false);
  const [selectedRecordId, setSelectedRecordId] = useState("");
  const [editor, setEditor] = useState<DailyEditForm | null>(null);
  const [isSaving, setIsSaving] = useState(false);
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
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento giornaliere"));
  }, []);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    const { start, end } = monthBounds(selectedMonth);
    listAllDailyRecords(token, { dateFrom: start, dateTo: end })
      .then((dailyItems) => {
        setRecords(dailyItems);
        setSelectedRecordId("");
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento giornaliere"));
  }, [selectedMonth]);

  const collaboratorMap = useMemo(() => new Map(collaborators.map((item) => [item.id, item])), [collaborators]);
  const mappedCollaboratorCount = useMemo(
    () => collaborators.filter((item) => item.application_user_id != null).length,
    [collaborators],
  );

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
          company: collaborator?.company_label ?? collaborator?.company_code ?? "—",
          scheduleCode: record.schedule_code ?? "—",
          programmedSchedule: record.detail_programmed_schedule ?? "—",
          status: record.detail_status ?? record.stato ?? "—",
          timeSlots: record.detail_time_slots ?? "—",
          ordinaryMinutes: record.ordinary_minutes,
          absenceMinutes: record.absence_minutes,
          effectiveExtraMinutes: effectiveExtra,
          kmValue: record.km_value,
          specialDay: Boolean(record.special_day),
          hasAnomalies: record.detail_anomalies.length > 0 || Boolean(record.detail_error),
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
      const matchesExtra = !onlyExtra || row.effectiveExtraMinutes > 0;
      return matchesCollaborator && matchesSearch && matchesAnomalies && matchesExtra;
    });
  }, [rows, search, selectedCollaboratorId, onlyAnomalies, onlyExtra]);

  const selectedRecord = useMemo(() => {
    const explicit = records.find((record) => record.id === selectedRecordId);
    if (explicit) {
      return explicit;
    }
    return filteredRows.length > 0 ? records.find((record) => record.id === filteredRows[0]?.id) ?? null : null;
  }, [records, selectedRecordId, filteredRows]);

  useEffect(() => {
    if (!selectedRecord) {
      setEditor(null);
      return;
    }
    setEditor({
      kmValue: selectedRecord.km_value != null ? String(selectedRecord.km_value) : "",
      overrideStraordinario: formatMinutesInput(selectedRecord.override_straordinario_minutes),
      overrideMpe: formatMinutesInput(selectedRecord.override_mpe_minutes),
      manualNote: selectedRecord.manual_note ?? "",
    });
  }, [selectedRecord]);

  const canEdit = Boolean(currentUser);
  const totalExtraRows = useMemo(() => rows.filter((row) => row.effectiveExtraMinutes > 0).length, [rows]);
  const totalAnomalyRows = useMemo(() => rows.filter((row) => row.hasAnomalies).length, [rows]);
  const totalKm = useMemo(() => rows.reduce((sum, row) => sum + (row.kmValue ?? 0), 0), [rows]);

  async function handleSave() {
    const token = getStoredAccessToken();
    if (!token || !selectedRecord || !editor) return;
    setIsSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateInazDailyRecord(token, selectedRecord.id, {
        km_value: editor.kmValue.trim() ? Number(editor.kmValue) : null,
        override_straordinario_minutes: parseMinutesInput(editor.overrideStraordinario),
        override_mpe_minutes: parseMinutesInput(editor.overrideMpe),
        manual_note: editor.manualNote.trim() || null,
      });
      setRecords((current) => current.map((item) => (item.id === updated.id ? updated : item)));
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
        header: "Ordinarie",
        accessorKey: "ordinaryMinutes",
        cell: ({ row }) => formatHours(row.original.ordinaryMinutes),
      },
      {
        header: "Extra",
        accessorKey: "effectiveExtraMinutes",
        cell: ({ row }) => (
          <span className={row.original.effectiveExtraMinutes > 0 ? "font-medium text-emerald-700" : "text-gray-500"}>
            {formatHours(row.original.effectiveExtraMinutes)}
          </span>
        ),
      },
      {
        header: "KM",
        accessorKey: "kmValue",
        cell: ({ row }) => row.original.kmValue ?? "—",
      },
    ],
    [],
  );

  return (
    <ProtectedPage title="Giornaliere Inaz" description="Consultazione e rettifica giornaliere collaboratori." breadcrumb="Inaz" requiredModule="inaz">
      <div className="space-y-6">
        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        {success ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div> : null}

        {currentUser?.role === "admin" || currentUser?.role === "super_admin" ? (
          mappedCollaboratorCount === 0 ? (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              Nessun collaboratore e ancora mappato a un utente GAIA. La schermata funziona per controllo centralizzato, ma per i capi settore serve completare il mapping da <Link className="font-medium underline" href="/inaz/collaboratori">Collaboratori</Link>.
            </div>
          ) : null
        ) : null}

        <section className="grid gap-4 xl:grid-cols-4">
          <div className="rounded-2xl border border-gray-100 bg-white p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Collaboratori</p>
            <p className="mt-2 text-2xl font-semibold text-gray-900">{collaborators.length}</p>
            <p className="text-xs text-gray-500">perimetro corrente</p>
          </div>
          <div className="rounded-2xl border border-gray-100 bg-white p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Giornate caricate</p>
            <p className="mt-2 text-2xl font-semibold text-gray-900">{records.length}</p>
            <p className="text-xs text-gray-500">mese selezionato</p>
          </div>
          <div className="rounded-2xl border border-gray-100 bg-white p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Anomalie</p>
            <p className="mt-2 text-2xl font-semibold text-red-700">{totalAnomalyRows}</p>
            <p className="text-xs text-gray-500">giornate con alert</p>
          </div>
          <div className="rounded-2xl border border-gray-100 bg-white p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-gray-400">KM inseriti</p>
            <p className="mt-2 text-2xl font-semibold text-gray-900">{totalKm}</p>
            <p className="text-xs text-gray-500">totale mese</p>
          </div>
        </section>

        <article className="panel-card">
          <div className="mb-4">
            <p className="section-title">Filtri giornaliere</p>
            <p className="section-copy">Ricerca rapida per collaboratore, stato giornata, orario Inaz, anomalie, straordinari o riepilogo del dettaglio giorno.</p>
          </div>
          <div className="grid gap-4 lg:grid-cols-4">
            <label className="block text-sm font-medium text-gray-700">
              Mese operativo
              <input className="form-control mt-1" type="month" value={selectedMonth} onChange={(event) => setSelectedMonth(event.target.value)} />
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
            <div className="grid gap-3 sm:grid-cols-2 lg:pt-7">
              <label className="flex items-center gap-2 rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700">
                <input checked={onlyAnomalies} onChange={(event) => setOnlyAnomalies(event.target.checked)} type="checkbox" />
                Solo anomalie
              </label>
              <label className="flex items-center gap-2 rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700">
                <input checked={onlyExtra} onChange={(event) => setOnlyExtra(event.target.checked)} type="checkbox" />
                Solo extra
              </label>
            </div>
          </div>
        </article>

        <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <article className="panel-card">
            <div className="mb-4 flex items-center justify-between gap-4">
              <div>
                <p className="section-title">Tabella giornaliere</p>
                <p className="section-copy">Clicca una riga per aprire il pannello operativo della giornata. Il perimetro e quello del responsabile della sync, non del mapping del singolo dipendente.</p>
              </div>
              <div className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
                {filteredRows.length} righe · {totalExtraRows} con extra
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

                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Orario Inaz</p>
                    <p className="mt-2 text-sm font-semibold text-gray-900">{selectedRecord.detail_programmed_schedule ?? selectedRecord.schedule_code ?? "—"}</p>
                    <p className="mt-1 text-xs text-gray-500">{selectedRecord.detail_time_slots ?? "Fasce non disponibili"}</p>
                  </div>
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Totali rapidi</p>
                    <div className="mt-2 space-y-1 text-sm text-gray-700">
                      <p>Ordinarie: <span className="font-medium text-gray-900">{formatHours(selectedRecord.ordinary_minutes)}</span></p>
                      <p>Assenza: <span className="font-medium text-gray-900">{formatHours(selectedRecord.absence_minutes)}</span></p>
                      <p>Extra effettivi: <span className="font-medium text-emerald-700">{formatHours(selectedRecord.effective_extra_minutes)}</span></p>
                    </div>
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
                    <p className="section-copy">Qui modifichi solo i campi necessari per l’operativita: KM carburante, straordinario, maggior presenza e nota.</p>
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    <label className="block text-sm font-medium text-gray-700">
                      KM carburante
                      <input className="form-control mt-1" value={editor.kmValue} onChange={(event) => setEditor((current) => current ? { ...current, kmValue: event.target.value } : current)} placeholder="Es. 24" />
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
                    <button
                      className="btn-secondary"
                      type="button"
                      onClick={() =>
                        setEditor({
                          kmValue: selectedRecord.km_value != null ? String(selectedRecord.km_value) : "",
                          overrideStraordinario: formatMinutesInput(selectedRecord.override_straordinario_minutes),
                          overrideMpe: formatMinutesInput(selectedRecord.override_mpe_minutes),
                          manualNote: selectedRecord.manual_note ?? "",
                        })
                      }
                    >
                      Ripristina
                    </button>
                  </div>
                </div>

                <div className="grid gap-4 xl:grid-cols-2">
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                    <p className="section-title">Riepilogo giornata</p>
                    <div className="mt-3 space-y-2 text-sm text-gray-700">
                      {Object.entries(selectedRecord.detail_day_summary).length > 0 ? (
                        Object.entries(selectedRecord.detail_day_summary).map(([label, value]) => (
                          <div key={label} className="flex items-center justify-between gap-3">
                            <span>{label}</span>
                            <span className="font-medium text-gray-900">{value}</span>
                          </div>
                        ))
                      ) : (
                        <p className="text-sm text-gray-500">Nessun riepilogo disponibile.</p>
                      )}
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
                </div>

                <div className="flex flex-wrap gap-3">
                  <Link className="btn-secondary" href={`/inaz/collaboratori/${selectedRecord.collaborator_id}`}>
                    Apri dettaglio collaboratore
                  </Link>
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-6 py-10 text-center text-sm text-gray-500">
                Seleziona una giornata dalla tabella per aprire il pannello operativo con anomalie, straordinari, KM e note.
              </div>
            )}
          </article>
        </section>
      </div>
    </ProtectedPage>
  );
}
