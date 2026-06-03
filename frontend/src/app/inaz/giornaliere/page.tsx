"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { ProtectedPage } from "@/components/app/protected-page";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/table/data-table";
import { listInazCollaborators, listInazDailyRecords } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { InazCollaborator, InazDailyRecord } from "@/types/api";

type DailyRow = {
  id: string;
  workDate: string;
  collaboratorId: string;
  collaborator: string;
  scheduleCode: string;
  programmedSchedule: string;
  status: string;
  timeSlots: string;
  ordinary: string;
  absence: string;
  extra: string;
  specialDay: boolean;
  evidenze: string;
  summary: string;
};

function monthBounds(): { start: string; end: string } {
  const now = new Date();
  const start = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
  const end = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()).padStart(2, "0")}`;
  return { start, end };
}

function formatHours(minutes: number | null): string {
  if (minutes == null) return "—";
  return `${(minutes / 60).toFixed(2)} h`;
}

function summarizeMap(values: Record<string, string>): string {
  const entries = Object.entries(values);
  if (entries.length === 0) return "—";
  return entries
    .slice(0, 3)
    .map(([label, value]) => `${label}: ${value}`)
    .join(" · ");
}

export default function InazGiornalierePage() {
  const [records, setRecords] = useState<InazDailyRecord[]>([]);
  const [collaborators, setCollaborators] = useState<InazCollaborator[]>([]);
  const [selectedCollaboratorId, setSelectedCollaboratorId] = useState("");
  const [search, setSearch] = useState("");
  const [selectedRecordId, setSelectedRecordId] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    const { start, end } = monthBounds();
    Promise.all([
      listInazCollaborators(token, { page: 1, pageSize: 200 }),
      listInazDailyRecords(token, { dateFrom: start, dateTo: end, page: 1, pageSize: 200 }),
    ])
      .then(([collaboratorResponse, recordResponse]) => {
        setCollaborators(collaboratorResponse.items);
        setRecords(recordResponse.items);
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento giornaliere"));
  }, []);

  const collaboratorMap = useMemo(() => new Map(collaborators.map((item) => [item.id, item])), [collaborators]);

  const rows = useMemo<DailyRow[]>(
    () =>
      records.map((record) => ({
        id: record.id,
        collaboratorId: record.collaborator_id,
        workDate: record.work_date,
        collaborator: collaboratorMap.get(record.collaborator_id)?.name ?? record.collaborator_id,
        scheduleCode: record.schedule_code ?? "—",
        programmedSchedule: record.detail_programmed_schedule ?? "—",
        status: record.detail_status ?? record.stato ?? "—",
        timeSlots: record.detail_time_slots ?? "—",
        ordinary: formatHours(record.ordinary_minutes),
        absence: formatHours(record.absence_minutes),
        extra: formatHours((record.straordinario_minutes ?? 0) + (record.mpe_minutes ?? 0)),
        specialDay: Boolean(record.special_day),
        evidenze: record.evidenze ?? "—",
        summary: summarizeMap(record.detail_day_summary),
      })),
    [records, collaboratorMap],
  );

  const filteredRows = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return rows.filter((row) => {
      const matchesCollaborator = !selectedCollaboratorId || row.collaboratorId === selectedCollaboratorId;
      const matchesSearch =
        !normalizedSearch ||
        [row.collaborator, row.scheduleCode, row.programmedSchedule, row.status, row.evidenze, row.summary, row.workDate].some((value) =>
          value.toLowerCase().includes(normalizedSearch),
        );
      return matchesCollaborator && matchesSearch;
    });
  }, [rows, search, selectedCollaboratorId]);

  const selectedRecord = useMemo(() => {
    const explicit = records.find((record) => record.id === selectedRecordId);
    if (explicit) {
      return explicit;
    }
    if (filteredRows.length === 1) {
      return records.find((record) => record.id === filteredRows[0]?.id) ?? null;
    }
    return null;
  }, [records, selectedRecordId, filteredRows]);

  const columns = useMemo<ColumnDef<DailyRow>[]>(
    () => [
      { header: "Data", accessorKey: "workDate" },
      {
        header: "Collaboratore",
        accessorKey: "collaborator",
        cell: ({ row }) => (
          <Link className="font-medium text-gray-900 hover:text-emerald-700" href={`/inaz/collaboratori/${row.original.collaboratorId}`}>
            {row.original.collaborator}
          </Link>
        ),
      },
      { header: "Orario Inaz", accessorKey: "programmedSchedule" },
      {
        header: "Stato",
        accessorKey: "status",
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <Badge variant={row.original.specialDay ? "warning" : "neutral"}>{row.original.status}</Badge>
            {row.original.specialDay ? <span className="text-xs text-amber-700">giorno speciale</span> : null}
          </div>
        ),
      },
      { header: "Ordinarie", accessorKey: "ordinary" },
      { header: "Assenza", accessorKey: "absence" },
      { header: "Extra", accessorKey: "extra" },
      { header: "Evidenze", accessorKey: "evidenze" },
    ],
    [],
  );

  return (
    <ProtectedPage title="Giornaliere Inaz" description="Consultazione giornaliere collaboratori." breadcrumb="Inaz" requiredModule="inaz">
      <div className="space-y-6">
        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        <article className="panel-card">
          <div className="mb-4">
            <p className="section-title">Filtri giornaliere</p>
            <p className="section-copy">Ricerca rapida per collaboratore, stato giornata, orario Inaz, evidenze o riepilogo del dettaglio giorno.</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
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
            <label className="block text-sm font-medium text-gray-700">
              Cerca
              <input className="form-control mt-1" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Es. Permesso, OPESAB, 2026-05-16" />
            </label>
          </div>
        </article>

        <article className="panel-card">
          <div className="mb-4">
            <p className="section-title">Tabella giornaliere</p>
            <p className="section-copy">Vista mensile delle righe cartellino importate da Inaz con stato giornata, orario programmato e riepilogo operativo.</p>
          </div>
          <DataTable data={filteredRows} columns={columns} initialPageSize={20} />
        </article>

        {filteredRows.length > 0 ? (
          <article className="panel-card space-y-4">
            <div className="flex flex-wrap gap-2">
              {filteredRows.slice(0, 12).map((row) => (
                <button
                  key={row.id}
                  className={selectedRecord?.id === row.id ? "btn-primary" : "btn-secondary"}
                  type="button"
                  onClick={() => setSelectedRecordId(row.id)}
                >
                  {row.workDate}
                </button>
              ))}
            </div>

            {selectedRecord ? (
              <div className="space-y-4">
                <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <p className="section-title">{selectedRecord.work_date}</p>
                    <p className="section-copy">
                      {collaboratorMap.get(selectedRecord.collaborator_id)?.name ?? selectedRecord.collaborator_id} · {selectedRecord.detail_programmed_schedule ?? selectedRecord.schedule_code ?? "Orario non disponibile"}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant={selectedRecord.special_day ? "warning" : "neutral"}>{selectedRecord.detail_status ?? selectedRecord.stato ?? "n/d"}</Badge>
                    {selectedRecord.detail_schedule_type ? <Badge variant="neutral">{selectedRecord.detail_schedule_type}</Badge> : null}
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Fasce</p>
                    <p className="mt-2 text-sm font-semibold text-gray-900">{selectedRecord.detail_time_slots ?? "—"}</p>
                  </div>
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Ore teoriche</p>
                    <p className="mt-2 text-sm font-semibold text-gray-900">{selectedRecord.detail_theoretical_hours ?? formatHours(selectedRecord.teo_minutes)}</p>
                  </div>
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Ore assenza</p>
                    <p className="mt-2 text-sm font-semibold text-gray-900">{selectedRecord.detail_absence_hours ?? formatHours(selectedRecord.absence_minutes)}</p>
                  </div>
                  <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Evidenze</p>
                    <p className="mt-2 text-sm font-semibold text-gray-900">{selectedRecord.evidenze ?? "—"}</p>
                  </div>
                </div>

                {selectedRecord.punches.length > 0 ? (
                  <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                    {selectedRecord.punches.map((punch) => (
                      <div key={punch.id} className="rounded-xl border border-gray-100 bg-white px-3 py-2 text-sm text-gray-700">
                        Timbratura {punch.sequence}: {punch.entry_time ?? "—"} / {punch.exit_time ?? "—"}
                      </div>
                    ))}
                  </div>
                ) : null}

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
                    <p className="section-title">Totali giornata</p>
                    <div className="mt-3 space-y-2 text-sm text-gray-700">
                      {Object.entries(selectedRecord.detail_day_totals).length > 0 ? (
                        Object.entries(selectedRecord.detail_day_totals).map(([label, value]) => (
                          <div key={label} className="flex items-center justify-between gap-3">
                            <span>{label}</span>
                            <span className="font-medium text-gray-900">{value}</span>
                          </div>
                        ))
                      ) : (
                        <p className="text-sm text-gray-500">Nessun totale disponibile.</p>
                      )}
                    </div>
                  </div>
                </div>

                {(selectedRecord.detail_requests.length > 0 || selectedRecord.detail_anomalies.length > 0 || selectedRecord.detail_error) ? (
                  <div className="grid gap-4 xl:grid-cols-2">
                    <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                      <p className="section-title">Richieste</p>
                      <div className="mt-3 space-y-3 text-sm text-gray-700">
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
                    <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                      <p className="section-title">Anomalie</p>
                      <div className="mt-3 space-y-3 text-sm text-gray-700">
                        {selectedRecord.detail_anomalies.length > 0 ? (
                          selectedRecord.detail_anomalies.map((anomaly, index) => (
                            <div key={`${selectedRecord.id}-anomaly-${index}`} className="rounded-xl border border-white bg-white px-3 py-2">
                              {Object.entries(anomaly).map(([label, value]) => (
                                <p key={label}>
                                  <span className="font-medium text-gray-900">{label}:</span> {value}
                                </p>
                              ))}
                            </div>
                          ))
                        ) : selectedRecord.detail_error ? (
                          <p className="text-sm text-red-600">{selectedRecord.detail_error}</p>
                        ) : (
                          <p className="text-sm text-gray-500">Nessuna anomalia registrata.</p>
                        )}
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            ) : null}
          </article>
        ) : null}
      </div>
    </ProtectedPage>
  );
}
