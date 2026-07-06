"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { ProtectedPage } from "@/components/app/protected-page";
import { DataTable } from "@/components/table/data-table";
import { Badge } from "@/components/ui/badge";
import {
  getCurrentUser,
  listAllApplicationUsers,
  listAllPresenzeCollaborators,
  listPresenzeDailyRecords,
  mapPresenzeCollaboratorApplicationUser,
  updatePresenzeCollaboratorContractProfile,
} from "@/lib/api";
import {
  PRESENZE_COLLABORATOR_DETAIL_UPDATED_MESSAGE,
  scorePresenzeCollaboratorUserMatch,
  usersForPresenzeCollaboratorMappingSorted,
} from "@/lib/presenze-collaborator-mapping";
import { getStoredAccessToken } from "@/lib/auth";
import type { ApplicationUser, CurrentUser, PresenzeCollaborator, PresenzeDailyRecord } from "@/types/api";

type CollaboratorRow = {
  id: string;
  employeeCode: string;
  internalCode: string;
  name: string;
  birthDate: string;
  contractKind: PresenzeCollaborator["contract_kind"];
  contractSummary: string;
  operaiGroupCode: PresenzeCollaborator["operai_group"];
  operaiGroup: string;
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

type ContractWizardSelection = "unset" | "operaio_agrario" | "operaio_catasto_magazzino" | "impiegato" | "quadro" | "altro";

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

function formatOperaiGroup(group: PresenzeCollaborator["operai_group"]): string {
  if (group === "agrario") return "Agrario";
  if (group === "catasto_magazzino") return "Catasto / magazzino";
  return "—";
}

function formatContractKind(value: PresenzeCollaborator["contract_kind"]): string {
  if (value === "impiegato") return "Impiegato";
  if (value === "quadro") return "Quadro";
  if (value === "altro") return "Altro";
  return "Non impostato";
}

function formatContractSummary(contractKind: PresenzeCollaborator["contract_kind"], operaiGroup: PresenzeCollaborator["operai_group"]): string {
  if (contractKind === "operaio") {
    if (operaiGroup === "agrario") return "Operaio agrario";
    if (operaiGroup === "catasto_magazzino") return "Operaio catasto / magazzino";
    return "Operaio da completare";
  }
  return formatContractKind(contractKind);
}

function contractBadgeVariant(
  contractKind: PresenzeCollaborator["contract_kind"],
  operaiGroup: PresenzeCollaborator["operai_group"],
): "success" | "info" | "warning" | "neutral" {
  if (contractKind === "operaio") return operaiGroup === "agrario" ? "success" : operaiGroup === "catasto_magazzino" ? "info" : "warning";
  if (contractKind === "impiegato" || contractKind === "quadro") return "neutral";
  return "warning";
}

function contractWizardSelectionForCollaborator(collaborator: PresenzeCollaborator): ContractWizardSelection {
  if (collaborator.contract_kind === "operaio") {
    if (collaborator.operai_group === "agrario") return "operaio_agrario";
    if (collaborator.operai_group === "catasto_magazzino") return "operaio_catasto_magazzino";
    return "unset";
  }
  if (collaborator.contract_kind === "impiegato") return "impiegato";
  if (collaborator.contract_kind === "quadro") return "quadro";
  if (collaborator.contract_kind === "altro") return "altro";
  return "unset";
}

function isContractProfileIncomplete(collaborator: PresenzeCollaborator): boolean {
  if (!collaborator.contract_kind) return true;
  if (collaborator.contract_kind === "operaio" && !collaborator.operai_group) return true;
  return false;
}

function payloadFromContractWizardSelection(selection: ContractWizardSelection, collaborator: PresenzeCollaborator) {
  if (selection === "operaio_agrario") {
    return { contract_kind: "operaio" as const, operai_group: "agrario" as const, standard_daily_minutes: 420 };
  }
  if (selection === "operaio_catasto_magazzino") {
    return { contract_kind: "operaio" as const, operai_group: "catasto_magazzino" as const, standard_daily_minutes: 420 };
  }
  if (selection === "impiegato") {
    return { contract_kind: "impiegato" as const, operai_group: null, standard_daily_minutes: collaborator.standard_daily_minutes ?? 385 };
  }
  if (selection === "quadro") {
    return { contract_kind: "quadro" as const, operai_group: null, standard_daily_minutes: collaborator.standard_daily_minutes };
  }
  if (selection === "altro") {
    return { contract_kind: "altro" as const, operai_group: null, standard_daily_minutes: collaborator.standard_daily_minutes };
  }
  return { contract_kind: null, operai_group: null, standard_daily_minutes: collaborator.standard_daily_minutes };
}

export default function PresenzeCollaboratoriPage() {
  const [collaborators, setCollaborators] = useState<PresenzeCollaborator[]>([]);
  const [records, setRecords] = useState<PresenzeDailyRecord[]>([]);
  const [users, setUsers] = useState<ApplicationUser[]>([]);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [search, setSearch] = useState("");
  const [mappedOnly, setMappedOnly] = useState<"all" | "mapped" | "unmapped">("all");
  const [operaiGroupFilter, setOperaiGroupFilter] = useState<"all" | "agrario" | "catasto_magazzino" | "unset">("all");
  const [selectedMappings, setSelectedMappings] = useState<Record<string, string>>({});
  const [selectedCollaborator, setSelectedCollaborator] = useState<CollaboratorRow | null>(null);
  const [detailModalDirty, setDetailModalDirty] = useState(false);
  const [refreshingList, setRefreshingList] = useState(false);
  const [contractWizardOpen, setContractWizardOpen] = useState(false);
  const [contractWizardSaving, setContractWizardSaving] = useState(false);
  const [contractSelections, setContractSelections] = useState<Record<string, ContractWizardSelection>>({});
  const [error, setError] = useState<string | null>(null);

  const applyCollaboratorsPageData = useCallback(
    (collaboratorItems: PresenzeCollaborator[], recordItems: PresenzeDailyRecord[], userItems: ApplicationUser[]) => {
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
      setContractSelections((current) => {
        const next = { ...current };
        for (const collaborator of collaboratorItems) {
          next[collaborator.id] = contractWizardSelectionForCollaborator(collaborator);
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
    const sessionUser = await getCurrentUser(token);
    setCurrentUser(sessionUser);
    const [collaboratorItems, recordResponse, userItems] = await Promise.all([
      listAllPresenzeCollaborators(token),
      listPresenzeDailyRecords(token, { dateFrom: start, dateTo: end, page: 1, pageSize: 200 }),
      sessionUser.role === "admin" || sessionUser.role === "super_admin"
        ? listAllApplicationUsers(token)
        : Promise.resolve([] as ApplicationUser[]),
    ]);
    applyCollaboratorsPageData(collaboratorItems, recordResponse.items, userItems);
  }, [applyCollaboratorsPageData]);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    getCurrentUser(token)
      .then((sessionUser) => {
        setCurrentUser(sessionUser);
        const { start, end } = currentMonthBounds();
        return Promise.all([
          listAllPresenzeCollaborators(token),
          listPresenzeDailyRecords(token, { dateFrom: start, dateTo: end, page: 1, pageSize: 200 }),
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
      if (event.data?.type !== PRESENZE_COLLABORATOR_DETAIL_UPDATED_MESSAGE) return;
      setDetailModalDirty(true);
      setRefreshingList(true);
      void reloadCollaboratorsPageData()
        .then(() => {
          setDetailModalDirty(false);
          setError(null);
        })
        .catch((loadError) => {
          setError(loadError instanceof Error ? loadError.message : "Errore aggiornamento elenco collaboratori");
        })
        .finally(() => {
          setRefreshingList(false);
        });
    }

    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [reloadCollaboratorsPageData, selectedCollaborator]);

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
      const candidateUsers = usersForPresenzeCollaboratorMappingSorted(collaborator, users, collaborators, collaborator.id);
      let bestUser: ApplicationUser | null = null;
      let bestScore = 0;
      for (const user of candidateUsers) {
        const score = scorePresenzeCollaboratorUserMatch(collaborator, user);
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
    const grouped = new Map<string, PresenzeDailyRecord[]>();
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
        const suggestion = suggestionsByCollaborator.get(item.id)!;
        return {
          id: item.id,
          employeeCode: item.employee_code,
          internalCode: item.kint ?? item.kkint ?? "—",
          name: item.name,
          birthDate: item.birth_date ?? "—",
          contractKind: item.contract_kind,
          contractSummary: formatContractSummary(item.contract_kind, item.operai_group),
          operaiGroupCode: item.operai_group,
          operaiGroup: formatOperaiGroup(item.operai_group),
          lastSeen: item.last_seen_at ?? "—",
          active: item.is_active,
          dailyRows: collaboratorRecords.length,
          ordinaryHours: formatHours(ordinaryMinutes),
          extraHours: formatHours(extraMinutes),
          mapped: item.application_user_id != null,
          mappedUser: item.application_user_id != null ? userMap.get(item.application_user_id)?.username ?? `#${item.application_user_id}` : "—",
          suggestedUserId: suggestion.userId,
          suggestedUserLabel: buildSuggestedLabel(userMap.get(suggestion.userId ?? -1) ?? null),
          suggestionConfidence: suggestion.confidence,
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
      const operaiGroupMatches =
        operaiGroupFilter === "all" ||
        (operaiGroupFilter === "unset" && row.operaiGroupCode == null) ||
        row.operaiGroupCode === operaiGroupFilter;
      const searchFilter =
        !normalizedSearch ||
        [row.employeeCode, row.internalCode, row.name, row.birthDate, row.contractSummary, row.operaiGroup, row.mappedUser, row.lastSeen].some((value) =>
          value.toLowerCase().includes(normalizedSearch),
        );
      return mappingFilter && operaiGroupMatches && searchFilter;
    });
  }, [rows, search, mappedOnly, operaiGroupFilter]);

  const collaboratorsNeedingContractReview = useMemo(
    () => collaborators.filter((item) => isContractProfileIncomplete(item)),
    [collaborators],
  );

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
      const mapped = await mapPresenzeCollaboratorApplicationUser(token, collaboratorId, nextUserId);
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
        const mapped = await mapPresenzeCollaboratorApplicationUser(token, row.id, row.suggestedUserId);
        setCollaborators((current) => current.map((item) => (item.id === row.id ? mapped : item)));
      }
    } catch (mapError) {
      setError(mapError instanceof Error ? mapError.message : "Errore applicazione mapping suggeriti");
    }
  }

  async function handleSaveContractWizard() {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione scaduta. Effettua di nuovo l'accesso.");
      return;
    }
    setContractWizardSaving(true);
    try {
      for (const collaborator of collaboratorsNeedingContractReview) {
        const selection = contractSelections[collaborator.id]!;
        const payload = payloadFromContractWizardSelection(selection, collaborator);
        const sameContract = (collaborator.contract_kind ?? null) === payload.contract_kind;
        const sameGroup = (collaborator.operai_group ?? null) === payload.operai_group;
        const sameMinutes = (collaborator.standard_daily_minutes ?? null) === (payload.standard_daily_minutes ?? null);
        if (sameContract && sameGroup && sameMinutes) {
          continue;
        }
        const updated = await updatePresenzeCollaboratorContractProfile(token, collaborator.id, payload);
        setCollaborators((current) => current.map((item) => (item.id === collaborator.id ? updated : item)));
      }
      setError(null);
      setContractWizardOpen(false);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Errore salvataggio profili contrattuali");
    } finally {
      setContractWizardSaving(false);
    }
  }

  const canEditMapping = currentUser?.role === "admin" || currentUser?.role === "super_admin";

  const columns = useMemo<ColumnDef<CollaboratorRow>[]>(
    () => [
      { header: "Matricola", accessorKey: "employeeCode" },
      { header: "Codice giornaliere", accessorKey: "internalCode" },
      { header: "Nome", accessorKey: "name" },
      {
        header: "Contratto / gruppo",
        accessorKey: "contractSummary",
        cell: ({ row }) => (
          <Badge
            variant={contractBadgeVariant(row.original.contractKind, row.original.operaiGroupCode)}
            className="rounded-lg"
          >
            {row.original.contractSummary}
          </Badge>
        ),
      },
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
    <ProtectedPage title="Collaboratori" description="Lista collaboratori importati dalle giornaliere." breadcrumb="Giornaliere" requiredModule="presenze">
      <div className="space-y-6">
        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}

        <article className="panel-card">
          <div className="mb-4">
            <p className="section-title">Filtri collaboratori</p>
            <p className="section-copy">Ricerca per matricola, nome o contratto e gestisci mapping e profili anagrafici Presenze.</p>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
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
            <label className="block text-sm font-medium text-gray-700">
              Gruppo operai
              <select className="form-control mt-1" value={operaiGroupFilter} onChange={(event) => setOperaiGroupFilter(event.target.value as typeof operaiGroupFilter)}>
                <option value="all">Tutti</option>
                <option value="agrario">Agrario</option>
                <option value="catasto_magazzino">Catasto / magazzino</option>
                <option value="unset">Non impostato</option>
              </select>
            </label>
          </div>
        </article>

        <article className="panel-card">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
            <p className="section-title">Elenco collaboratori</p>
            <p className="section-copy">Vista estesa di anagrafica, mapping, suggerimento automatico e volume giornaliere del mese. Apri il dettaglio per KM, straordinari e cartellino completo.</p>
            </div>
            <button className="btn-primary shrink-0 self-start" type="button" onClick={() => setContractWizardOpen(true)}>
              Wizard contratti{collaboratorsNeedingContractReview.length > 0 ? ` (${collaboratorsNeedingContractReview.length})` : ""}
            </button>
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
                    <p className="text-xs text-gray-500">Matricola {row.employeeCode} · {row.contractSummary}</p>
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
                    {usersForPresenzeCollaboratorMappingSorted(
                      collaborators.find((item) => item.id === row.id)!,
                      users,
                      collaborators,
                      row.id,
                    ).map((user) => (
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

        {contractWizardOpen ? (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4 py-6"
            onClick={() => !contractWizardSaving && setContractWizardOpen(false)}
          >
            <div
              className="flex h-[90vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
              onClick={(event) => event.stopPropagation()}
            >
              <div className="flex items-center justify-between gap-4 border-b border-gray-100 px-6 py-4">
                <div className="min-w-0">
                  <p className="section-title">Wizard profili contrattuali</p>
                  <p className="mt-1 text-sm text-gray-500">
                    Completa rapidamente il contratto dei collaboratori. Per gli operai e obbligatorio distinguere agrario da catasto / magazzino.
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <button className="btn-secondary" type="button" onClick={() => setContractWizardOpen(false)} disabled={contractWizardSaving}>
                    Chiudi
                  </button>
                  <button className="btn-primary" type="button" onClick={() => void handleSaveContractWizard()} disabled={contractWizardSaving}>
                    {contractWizardSaving ? "Salvataggio..." : "Salva profili"}
                  </button>
                </div>
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto bg-[#f7faf7] p-4">
                {collaboratorsNeedingContractReview.length === 0 ? (
                  <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                    Tutti i collaboratori hanno gia un profilo contrattuale coerente.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {collaboratorsNeedingContractReview.map((collaborator) => (
                      <div key={collaborator.id} className="grid gap-3 rounded-2xl border border-gray-100 bg-white px-4 py-4 lg:grid-cols-[1.2fr_220px_220px_220px] lg:items-center">
                        <div>
                          <p className="font-medium text-gray-900">{collaborator.name}</p>
                          <p className="text-xs text-gray-500">
                            Matricola {collaborator.employee_code} · Codice giornaliere {collaborator.kint ?? collaborator.kkint ?? "—"}
                          </p>
                          <p className="mt-1 text-xs text-amber-700">
                            Attuale: {formatContractSummary(collaborator.contract_kind, collaborator.operai_group)} · standard{" "}
                            {collaborator.standard_daily_minutes != null ? `${collaborator.standard_daily_minutes} min` : "non impostato"}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Scelta wizard</p>
                          <select
                            className="form-control mt-1"
                            aria-label={`Contratto ${collaborator.name}`}
                            value={contractSelections[collaborator.id]!}
                            onChange={(event) =>
                              setContractSelections((current) => ({
                                ...current,
                                [collaborator.id]: event.target.value as ContractWizardSelection,
                              }))
                            }
                          >
                            <option value="unset">Non impostato</option>
                            <option value="operaio_agrario">Operaio agrario</option>
                            <option value="operaio_catasto_magazzino">Operaio catasto / magazzino</option>
                            <option value="impiegato">Impiegato</option>
                            <option value="quadro">Quadro</option>
                            <option value="altro">Altro</option>
                          </select>
                        </div>
                        <div>
                          <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Esito</p>
                          <div className="mt-1">
                            {(() => {
                              const previewSelection = contractSelections[collaborator.id]!;
                              const preview = payloadFromContractWizardSelection(previewSelection, collaborator);
                              return (
                                <Badge variant={contractBadgeVariant(preview.contract_kind, preview.operai_group)}>
                                  {formatContractSummary(preview.contract_kind, preview.operai_group)}
                                </Badge>
                              );
                            })()}
                          </div>
                        </div>
                        <div>
                          <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Standard</p>
                          <p className="mt-2 text-sm font-medium text-gray-900">
                            {(() => {
                              const previewSelection = contractSelections[collaborator.id]!;
                              const preview = payloadFromContractWizardSelection(previewSelection, collaborator);
                              return preview.standard_daily_minutes != null ? `${preview.standard_daily_minutes} min` : "Non impostato";
                            })()}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
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
                  <p className="section-title">Dettaglio collaboratore</p>
                  <p className="mt-1 truncate text-sm text-gray-500">
                    {selectedCollaborator.name} · Matricola {selectedCollaborator.employeeCode} · {selectedCollaborator.contractSummary}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <Link className="btn-secondary" href={`/presenze/collaboratori/${selectedCollaborator.id}`} target="_blank">
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
                  src={`/presenze/collaboratori/${selectedCollaborator.id}?embedded=1`}
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
