"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { ProtectedPage } from "@/components/app/protected-page";
import { DataTable } from "@/components/table/data-table";
import { Badge } from "@/components/ui/badge";
import { getCurrentUser, listApplicationUsers, listInazCollaborators, mapInazCollaboratorApplicationUser } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { ApplicationUser, CurrentUser, InazCollaborator } from "@/types/api";

type CollaboratorRow = {
  id: string;
  employeeCode: string;
  name: string;
  company: string;
  birthDate: string;
  mapped: boolean;
  mappedUser: string;
};

export default function InazCollaboratoriPage() {
  const router = useRouter();
  const [collaborators, setCollaborators] = useState<InazCollaborator[]>([]);
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
        return Promise.all([
          listInazCollaborators(token, { page: 1, pageSize: 200 }),
          sessionUser.role === "admin" || sessionUser.role === "super_admin"
            ? listApplicationUsers(token)
            : Promise.resolve({ items: [], total: 0 }),
        ]);
      })
      .then(([collaboratorResponse, usersResponse]) => {
        setCollaborators(collaboratorResponse.items);
        setUsers(usersResponse.items);
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento collaboratori"));
  }, []);

  const userMap = useMemo(() => new Map(users.map((user) => [user.id, user])), [users]);

  const rows = useMemo<CollaboratorRow[]>(
    () =>
      collaborators.map((item) => ({
        id: item.id,
        employeeCode: item.employee_code,
        name: item.name,
        company: item.company_label ?? item.company_code ?? "—",
        birthDate: item.birth_date ?? "—",
        mapped: item.application_user_id != null,
        mappedUser: item.application_user_id != null ? userMap.get(item.application_user_id)?.username ?? `#${item.application_user_id}` : "—",
      })),
    [collaborators, userMap],
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
        [row.employeeCode, row.name, row.company, row.birthDate, row.mappedUser].some((value) => value.toLowerCase().includes(normalizedSearch));
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
      { header: "Nome", accessorKey: "name" },
      { header: "Azienda", accessorKey: "company" },
      { header: "Nascita", accessorKey: "birthDate" },
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
            <p className="section-copy">Apri il dettaglio per calendario e riepilogo eventi. Se sei admin puoi aggiornare il mapping direttamente qui.</p>
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
