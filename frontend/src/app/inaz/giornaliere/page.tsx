"use client";

import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { ProtectedPage } from "@/components/app/protected-page";
import { DataTable } from "@/components/table/data-table";
import { listInazCollaborators, listInazDailyRecords } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { InazCollaborator, InazDailyRecord } from "@/types/api";

type DailyRow = {
  id: string;
  workDate: string;
  collaborator: string;
  scheduleCode: string;
  ordinary: string;
  absence: string;
  evidenze: string;
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

export default function InazGiornalierePage() {
  const [records, setRecords] = useState<InazDailyRecord[]>([]);
  const [collaborators, setCollaborators] = useState<InazCollaborator[]>([]);
  const [selectedCollaboratorId, setSelectedCollaboratorId] = useState("");
  const [search, setSearch] = useState("");
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
        workDate: record.work_date,
        collaborator: collaboratorMap.get(record.collaborator_id)?.name ?? record.collaborator_id,
        scheduleCode: record.schedule_code ?? "—",
        ordinary: formatHours(record.ordinary_minutes),
        absence: formatHours(record.absence_minutes),
        evidenze: record.evidenze ?? "—",
      })),
    [records, collaboratorMap],
  );

  const filteredRows = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return rows.filter((row) => {
      const matchesCollaborator = !selectedCollaboratorId || records.find((record) => record.id === row.id)?.collaborator_id === selectedCollaboratorId;
      const matchesSearch =
        !normalizedSearch ||
        [row.collaborator, row.scheduleCode, row.evidenze, row.workDate].some((value) => value.toLowerCase().includes(normalizedSearch));
      return matchesCollaborator && matchesSearch;
    });
  }, [rows, search, selectedCollaboratorId, records]);

  const columns = useMemo<ColumnDef<DailyRow>[]>(
    () => [
      { header: "Data", accessorKey: "workDate" },
      { header: "Collaboratore", accessorKey: "collaborator" },
      { header: "Codice orario", accessorKey: "scheduleCode" },
      { header: "Ordinarie", accessorKey: "ordinary" },
      { header: "Assenza", accessorKey: "absence" },
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
            <p className="section-copy">Ricerca rapida per collaboratore, codice orario o evidenze.</p>
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
            <p className="section-copy">Vista mensile delle righe cartellino importate da Inaz.</p>
          </div>
          <DataTable data={filteredRows} columns={columns} initialPageSize={20} />
        </article>
      </div>
    </ProtectedPage>
  );
}
