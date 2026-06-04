"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { ProtectedPage } from "@/components/app/protected-page";
import { DataTable } from "@/components/table/data-table";
import { Badge } from "@/components/ui/badge";
import { getCurrentUser, listAllApplicationUsers, listAllInazCollaborators, listInazDailyRecords, mapInazCollaboratorApplicationUser } from "@/lib/api";
import {
  INAZ_COLLABORATOR_DETAIL_UPDATED_MESSAGE,
  scoreInazCollaboratorUserMatch,
  usersForInazCollaboratorMappingSorted,
} from "@/lib/inaz-collaborator-mapping";
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
  suggestedUserId: number | null;
  suggestedUserLabel: string;
  suggestionConfidence: "high" | "medium" | "low" | "none";
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

function buildSuggestedLabel(user: ApplicationUser | null): string {
  if (!user) return "Nessun suggerimento";
  const identity = user.full_name?.trim() || user.username;
  return `${identity} · ${user.email}`;
}

export default function InazCollaboratoriPage() {
  const [collaborators, setCollaborators] = useState<InazCollaborator[]>([]);
  const [records, setRecords] = useState<InazDailyRecord[]>([]);
  const [users, setUsers] = useState<ApplicationUser[]>([]);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [search, setSearch] = useState("");
  const [mappedOnly, setMappedOnly] = useState<"all" | "mapped" | "unmapped">("all");
  const [selectedMappings, setSelectedMappings] = useState<Record<string, string>>({});
  const [selectedCollaborator, setSelectedCollaborator] = useState<CollaboratorRow | null>(null);
  const [detailModalDirty, setDetailModalDirty] = useState(false);
  const [refreshingList, setRefreshingList] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const applyCollaboratorsPageData = useCallback(
    (collaboratorItems: InazCollaborator[], recordItems: InazDailyRecord[], userItems: ApplicationUser[]) => {
      setCollaborators(collaboratorItems);
      setRecords(recordItems);
      setUsers(userItems);
      setSelectedMappings((current) => {
        const next = { ...current };
        for (const collaborator of collaboratorItems) {
          if (collaborator.application_user_id != null) {
            next[collaborator.id] = String(collaborator.application_user_id);
          }
        }
        return next;
      });
    },
    [],
  );

  const reloadCollaboratorsPageData = useCallback(async () => {
    const token = getStoredAccessToken();
    if (!token) return;

    const { start, end } = currentMonthBounds();
    const sessionUser = currentUser ?? (await getCurrentUser(token));
    if (!currentUser) {
      setCurrentUser(sessionUser);
    }
    const [collaboratorItems, recordResponse, userItems] = await Promise.all([
      listAllInazCollaborators(token),
      listInazDailyRecords(token, { dateFrom: start, dateTo: end, page: 1, pageSize: 200 }),
      sessionUser.role === "admin" || sessionUser.role === "super_admin"
        ? listAllApplicationUsers(token)
        : Promise.resolve([] as ApplicationUser[]),
    ]);
    applyCollaboratorsPageData(collaboratorItems, recordResponse.items, userItems);
  }, [applyCollaboratorsPageData, currentUser]);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    getCurrentUser(token)
      .then((sessionUser) => {
        setCurrentUser(sessionUser);
        const { start, end } = currentMonthBounds();
        return Promise.all([
          listAllInazCollaborators(token),
          listInazDailyRecords(token, { dateFrom: start, dateTo: end, page: 1, pageSize: 200 }),
          sessionUser.role === "admin" || sessionUser.role === "super_admin"
            ? listAllApplicationUsers(token)
            : Promise.resolve([] as ApplicationUser[]),
        ]).then(([collaboratorItems, recordResponse, userItems]) => {
          applyCollaboratorsPageData(collaboratorItems, recordResponse.items, userItems);
        });
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento collaboratori"));
  }, [applyCollaboratorsPageData]);

  useEffect(() => {
    if (!selectedCollaborator) return;

    function onMessage(event: MessageEvent) {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type !== INAZ_COLLABORATOR_DETAIL_UPDATED_MESSAGE) return;
      setDetailModalDirty(true);
    }

    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [selectedCollaborator]);

  async function closeDetailModal() {
    if (detailModalDirty) {
      setRefreshingList(true);
      try {
        await reloadCollaboratorsPageData();
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore aggiornamento elenco collaboratori");
      } finally {
        setRefreshingList(false);
      }
    }
    setSelectedCollaborator(null);
    setDetailModalDirty(false);
  }

  function openDetailModal(row: CollaboratorRow) {
    setDetailModalDirty(false);
    setSelectedCollaborator(row);
  }

  const userMap = useMemo(() => new Map(users.map((user) => [user.id, user])), [users]);
  const suggestionsByCollaborator = useMemo(() => {
    const suggestions = new Map<string, { userId: number | null; score: number; confidence: "high" | "medium" | "low" | "none" }>();

    for (const collaborator of collaborators) {
      const candidateUsers = usersForInazCollaboratorMappingSorted(collaborator, users, collaborators, collaborator.id);
      let bestUser: ApplicationUser | null = null;
      let bestScore = 0;
      for (const user of candidateUsers) {
        const score = scoreInazCollaboratorUserMatch(collaborator, user);
        if (score > bestScore) {
          bestScore = score;
          bestUser = user;
        }
      }

      const confidence: "high" | "medium" | "low" | "none" =
        bestScore >= 120 ? "high" : bestScore >= 70 ? "medium" : bestScore >= 35 ? "low" : "none";

      suggestions.set(collaborator.id, {
        userId: bestUser && confidence !== "none" ? bestUser.id : null,
        score: bestScore,
        confidence,
      });
    }

    return suggestions;
  }, [collaborators, users]);

  useEffect(() => {
    if (users.length === 0 || collaborators.length === 0) return;
    setSelectedMappings((current) => {
      const next = { ...current };
      let changed = false;
      for (const collaborator of collaborators) {
        if (collaborator.application_user_id != null || next[collaborator.id]) {
          continue;
        }
        const suggestion = suggestionsByCollaborator.get(collaborator.id);
        if (suggestion?.userId != null) {
          next[collaborator.id] = String(suggestion.userId);
          changed = true;
        }
      }
      return changed ? next : current;
    });
  }, [collaborators, users, suggestionsByCollaborator]);
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
          suggestedUserId: suggestionsByCollaborator.get(item.id)?.userId ?? null,
          suggestedUserLabel: buildSuggestedLabel(userMap.get(suggestionsByCollaborator.get(item.id)?.userId ?? -1) ?? null),
          suggestionConfidence: suggestionsByCollaborator.get(item.id)?.confidence ?? "none",
        };
      }),
    [collaborators, userMap, recordsByCollaborator, suggestionsByCollaborator],
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
    if (!token) {
      setError("Sessione scaduta. Effettua di nuovo l'accesso.");
      return;
    }
    const selectedValue = selectedMappings[collaboratorId]?.trim() ?? "";
    const nextUserId = selectedValue === "" ? null : Number(selectedValue);
    if (selectedValue !== "" && !Number.isFinite(nextUserId)) {
      setError("Seleziona un utente GAIA valido.");
      return;
    }
    const collaborator = collaborators.find((item) => item.id === collaboratorId);
    const currentValue = collaborator?.application_user_id == null ? "" : String(collaborator.application_user_id);
    if (selectedValue === currentValue) {
      setError(null);
      return;
    }
    try {
      const mapped = await mapInazCollaboratorApplicationUser(token, collaboratorId, nextUserId);
      setCollaborators((current) => current.map((item) => (item.id === collaboratorId ? mapped : item)));
      setError(null);
    } catch (mapError) {
      setError(mapError instanceof Error ? mapError.message : "Errore mapping collaboratore");
    }
  }

  async function handleApplySuggestedMappings() {
    const token = getStoredAccessToken();
    if (!token) return;
    try {
      const pending = filteredRows.filter((row) => !row.mapped && row.suggestedUserId != null);
      for (const row of pending) {
        const mapped = await mapInazCollaboratorApplicationUser(token, row.id, row.suggestedUserId);
        setCollaborators((current) => current.map((item) => (item.id === row.id ? mapped : item)));
      }
    } catch (mapError) {
      setError(mapError instanceof Error ? mapError.message : "Errore applicazione mapping suggeriti");
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
      {
        header: "Suggerito",
        accessorKey: "suggestedUserLabel",
        cell: ({ row }) =>
          row.original.suggestionConfidence === "none" ? (
            <span className="text-sm text-gray-400">Nessuno</span>
          ) : (
            <div className="space-y-1">
              <p className="text-sm font-medium text-gray-900">{row.original.suggestedUserLabel}</p>
              <Badge variant={row.original.suggestionConfidence === "high" ? "success" : row.original.suggestionConfidence === "medium" ? "warning" : "neutral"}>
                {row.original.suggestionConfidence === "high" ? "Alta" : row.original.suggestionConfidence === "medium" ? "Media" : "Bassa"}
              </Badge>
            </div>
          ),
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
              <input className="form-control mt-1" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Es. NIEDDU, 1854, Oristano" />
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
            <p className="section-copy">Vista estesa di anagrafica, mapping, suggerimento automatico e volume giornaliere del mese. Apri il dettaglio per KM, straordinari e cartellino completo.</p>
          </div>
          <DataTable
            data={filteredRows}
            columns={columns}
            initialPageSize={20}
            onRowClick={(row) => openDetailModal(row)}
          />
        </article>

        {canEditMapping ? (
          <article className="panel-card">
            <div className="mb-4">
              <p className="section-title">Aggiorna mapping GAIA</p>
              <p className="section-copy">Seleziona un utente GAIA per i collaboratori che richiedono collegamento. Il sistema precompila un suggerimento basato su nome completo, username ed email.</p>
            </div>
            <div className="mb-4 flex flex-wrap items-center gap-3">
              <button className="btn-secondary" type="button" onClick={() => void handleApplySuggestedMappings()}>
                Applica suggeriti
              </button>
              <p className="text-sm text-gray-500">
                Vengono applicati solo i collaboratori non ancora mappati con un suggerimento disponibile.
              </p>
            </div>
            <div className="space-y-3">
              {filteredRows.map((row) => (
                <div key={row.id} className="grid gap-3 rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 lg:grid-cols-[1fr_320px_120px] lg:items-center">
                  <div>
                    <p className="font-medium text-gray-900">{row.name}</p>
                    <p className="text-xs text-gray-500">Matricola {row.employeeCode} · {row.company}</p>
                    {row.suggestionConfidence !== "none" ? (
                      <p className="mt-1 text-xs text-emerald-700">
                        Suggerito: {row.suggestedUserLabel} ({row.suggestionConfidence === "high" ? "confidenza alta" : row.suggestionConfidence === "medium" ? "confidenza media" : "confidenza bassa"})
                      </p>
                    ) : null}
                  </div>
                  <select
                    className="form-control"
                    value={selectedMappings[row.id] ?? String(collaborators.find((item) => item.id === row.id)?.application_user_id ?? "")}
                    onChange={(event) => setSelectedMappings((current) => ({ ...current, [row.id]: event.target.value }))}
                  >
                    <option value="">Nessun mapping</option>
                    {(() => {
                      const rowCollaborator = collaborators.find((item) => item.id === row.id);
                      return rowCollaborator
                        ? usersForInazCollaboratorMappingSorted(rowCollaborator, users, collaborators, row.id)
                        : [];
                    })().map((user) => (
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

        {selectedCollaborator ? (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4 py-6"
            onClick={() => void closeDetailModal()}
          >
            <div
              className="flex h-[90vh] w-full max-w-7xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
              onClick={(event) => event.stopPropagation()}
            >
              <div className="flex items-center justify-between gap-4 border-b border-gray-100 px-6 py-4">
                <div className="min-w-0">
                  <p className="section-title">Dettaglio collaboratore Inaz</p>
                  <p className="mt-1 truncate text-sm text-gray-500">
                    {selectedCollaborator.name} · Matricola {selectedCollaborator.employeeCode} · {selectedCollaborator.company}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <Link className="btn-secondary" href={`/inaz/collaboratori/${selectedCollaborator.id}`} target="_blank">
                    Apri pagina completa
                  </Link>
                  <button className="btn-secondary" type="button" onClick={() => void closeDetailModal()} disabled={refreshingList}>
                    {refreshingList ? "Aggiornamento..." : "Chiudi"}
                  </button>
                </div>
              </div>
              <div className="min-h-0 flex-1 bg-[#f7faf7] p-4">
                <iframe
                  className="h-full w-full rounded-2xl border border-gray-200 bg-white"
                  src={`/inaz/collaboratori/${selectedCollaborator.id}?embedded=1`}
                  title={`Dettaglio collaboratore ${selectedCollaborator.name}`}
                />
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </ProtectedPage>
  );
}
