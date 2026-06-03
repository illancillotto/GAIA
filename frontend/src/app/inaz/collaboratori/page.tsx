"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { ProtectedPage } from "@/components/app/protected-page";
import { DataTable } from "@/components/table/data-table";
import { Badge } from "@/components/ui/badge";
import { getCurrentUser, listApplicationUsers, listInazCollaborators, listInazDailyRecords, mapInazCollaboratorApplicationUser } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { ApplicationUser, CurrentUser, InazCollaborator, InazDailyRecord } from "@/types/api";

type CollaboratorRow = {
  id: string;
  employeeCode: string;
  internalCode: string;
  name: string;
  company: string;
  birthDate: string;
  lastSeen: string;
  active: boolean;
  dailyRows: number;
  ordinaryHours: string;
  extraHours: string;
  mapped: boolean;
  mappedUser: string;
};

function currentMonthBounds(): { start: string; end: string } {
  const now = new Date();
  const start = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
  const end = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()).padStart(2, "0")}`;
  return { start, end };
}

function formatHours(minutes: number): string {
  return `${(minutes / 60).toFixed(1)} h`;
}

export default function InazCollaboratoriPage() {
  const router = useRouter();
  const [collaborators, setCollaborators] = useState<InazCollaborator[]>([]);
  const [records, setRecords] = useState<InazDailyRecord[]>([]);
  const [users, setUsers] = useState<ApplicationUser[]>([]);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [search, setSearch] = useState("");
  const [mappedOnly, setMappedOnly] = useState<"all" | "mapped" | "unmapped">("all");
  const [selectedMappings, setSelectedMappings] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    getCurrentUser(token)
      .then((sessionUser) => {
        setCurrentUser(sessionUser);
        const { start, end } = currentMonthBounds();
        return Promise.all([
          listInazCollaborators(token, { page: 1, pageSize: 200 }),
          listInazDailyRecords(token, { dateFrom: start, dateTo: end, page: 1, pageSize: 200 }),
          sessionUser.role === "admin" || sessionUser.role === "super_admin"
            ? listApplicationUsers(token)
            : Promise.resolve({ items: [], total: 0 }),
        ]);
      })
      .then(([collaboratorResponse, recordResponse, usersResponse]) => {
        setCollaborators(collaboratorResponse.items);
        setRecords(recordResponse.items);
        setUsers(usersResponse.items);
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento collaboratori"));
  }, []);

  const userMap = useMemo(() => new Map(users.map((user) => [user.id, user])), [users]);
  const recordsByCollaborator = useMemo(() => {
    const grouped = new Map<string, InazDailyRecord[]>();
    for (const record of records) {
      const current = grouped.get(record.collaborator_id) ?? [];
      current.push(record);
      grouped.set(record.collaborator_id, current);
    }
    return grouped;
  }, [records]);

  const rows = useMemo<CollaboratorRow[]>(
    () =>
      collaborators.map((item) => {
        const collaboratorRecords = recordsByCollaborator.get(item.id) ?? [];
        const ordinaryMinutes = collaboratorRecords.reduce((sum, record) => sum + (record.ordinary_minutes ?? 0), 0);
        const extraMinutes = collaboratorRecords.reduce(
          (sum, record) => sum + (record.effective_extra_minutes ?? (record.effective_straordinario_minutes ?? record.straordinario_minutes ?? 0) + (record.effective_mpe_minutes ?? record.mpe_minutes ?? 0)),
          0,
        );
        return {
          id: item.id,
          employeeCode: item.employee_code,
          internalCode: item.kint ?? item.kkint ?? "—",
          name: item.name,
          company: item.company_label ?? item.company_code ?? "—",
          birthDate: item.birth_date ?? "—",
          lastSeen: item.last_seen_at ?? "—",
          active: item.is_active,
          dailyRows: collaboratorRecords.length,
          ordinaryHours: formatHours(ordinaryMinutes),
          extraHours: formatHours(extraMinutes),
          mapped: item.application_user_id != null,
          mappedUser: item.application_user_id != null ? userMap.get(item.application_user_id)?.username ?? `#${item.application_user_id}` : "—",
        };
      }),
    [collaborators, userMap, recordsByCollaborator],
  );

  const filteredRows = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return rows.filter((row) => {
      const mappingFilter =
        mappedOnly === "all" ||
        (mappedOnly === "mapped" && row.mapped) ||
        (mappedOnly === "unmapped" && !row.mapped);
      const searchFilter =
        !normalizedSearch ||
        [row.employeeCode, row.internalCode, row.name, row.company, row.birthDate, row.mappedUser, row.lastSeen].some((value) =>
          value.toLowerCase().includes(normalizedSearch),
        );
      return mappingFilter && searchFilter;
    });
  }, [rows, search, mappedOnly]);

  async function handleMap(collaboratorId: string) {
    const token = getStoredAccessToken();
    if (!token) return;
    const selectedValue = selectedMappings[collaboratorId];
    try {
      const mapped = await mapInazCollaboratorApplicationUser(token, collaboratorId, selectedValue ? Number(selectedValue) : null);
      setCollaborators((current) => current.map((item) => (item.id === collaboratorId ? mapped : item)));
    } catch (mapError) {
      setError(mapError instanceof Error ? mapError.message : "Errore mapping collaboratore");
    }
  }

  const canEditMapping = currentUser?.role === "admin" || currentUser?.role === "super_admin";

  const columns = useMemo<ColumnDef<CollaboratorRow>[]>(
    () => [
      { header: "Matricola", accessorKey: "employeeCode" },
      { header: "Codice Inaz", accessorKey: "internalCode" },
      { header: "Nome", accessorKey: "name" },
      { header: "Azienda", accessorKey: "company" },
      { header: "Nascita", accessorKey: "birthDate" },
      {
        header: "Stato",
        accessorKey: "active",
        cell: ({ row }) => <Badge variant={row.original.active ? "success" : "warning"}>{row.original.active ? "Attivo" : "Inattivo"}</Badge>,
      },
      { header: "Ultimo sync", accessorKey: "lastSeen" },
      { header: "Giornaliere mese", accessorKey: "dailyRows" },
      { header: "Ordinarie", accessorKey: "ordinaryHours" },
      { header: "Extra", accessorKey: "extraHours" },
      {
        header: "Mapping",
        accessorKey: "mapped",
        cell: ({ row }) => <Badge variant={row.original.mapped ? "success" : "warning"}>{row.original.mapped ? "Mappato" : "Da mappare"}</Badge>,
      },
      { header: "Utente GAIA", accessorKey: "mappedUser" },
    ],
    [],
  );

  return (
    <ProtectedPage title="Collaboratori Inaz" description="Lista collaboratori importati da Inaz." breadcrumb="Inaz" requiredModule="inaz">
      <div className="space-y-6">
        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}

        <article className="panel-card">
          <div className="mb-4">
            <p className="section-title">Filtri collaboratori</p>
            <p className="section-copy">Ricerca per matricola, nome o azienda e gestisci il mapping verso utenti GAIA.</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block text-sm font-medium text-gray-700">
              Cerca
              <input className="form-control mt-1" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Es. AMADU, 1854, azienda 53" />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Stato mapping
              <select className="form-control mt-1" value={mappedOnly} onChange={(event) => setMappedOnly(event.target.value as "all" | "mapped" | "unmapped")}>
                <option value="all">Tutti</option>
                <option value="mapped">Solo mappati</option>
                <option value="unmapped">Solo da mappare</option>
              </select>
            </label>
          </div>
        </article>

        <article className="panel-card">
          <div className="mb-4">
            <p className="section-title">Elenco collaboratori</p>
            <p className="section-copy">Vista estesa di anagrafica, mapping, stato operativo e volume giornaliere del mese. Apri il dettaglio per KM, straordinari e cartellino completo.</p>
          </div>
          <DataTable
            data={filteredRows}
            columns={columns}
            initialPageSize={20}
            onRowClick={(row) => router.push(`/inaz/collaboratori/${row.id}`)}
          />
        </article>

        {canEditMapping ? (
          <article className="panel-card">
            <div className="mb-4">
              <p className="section-title">Aggiorna mapping GAIA</p>
              <p className="section-copy">Seleziona un utente GAIA per i collaboratori che richiedono collegamento.</p>
            </div>
            <div className="space-y-3">
              {filteredRows.map((row) => (
                <div key={row.id} className="grid gap-3 rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 lg:grid-cols-[1fr_280px_120px] lg:items-center">
                  <div>
                    <p className="font-medium text-gray-900">{row.name}</p>
                    <p className="text-xs text-gray-500">Matricola {row.employeeCode} · {row.company}</p>
                  </div>
                  <select
                    className="form-control"
                    value={selectedMappings[row.id] ?? String(collaborators.find((item) => item.id === row.id)?.application_user_id ?? "")}
                    onChange={(event) => setSelectedMappings((current) => ({ ...current, [row.id]: event.target.value }))}
                  >
                    <option value="">Nessun mapping</option>
                    {users.map((user) => (
                      <option key={user.id} value={user.id}>
                        {user.username} · {user.email}
                      </option>
                    ))}
                  </select>
                  <button className="btn-primary" type="button" onClick={() => void handleMap(row.id)}>
                    Salva
                  </button>
                </div>
              ))}
            </div>
          </article>
        ) : null}
      </div>
    </ProtectedPage>
  );
}
