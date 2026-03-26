"use client";

import Link from "next/link";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { ProtectedPage } from "@/components/app/protected-page";
import { UserDetailPanel } from "@/components/app/user-detail-panel";
import { DataTable } from "@/components/table/data-table";
import { TableFilters } from "@/components/table/table-filters";
import { Avatar } from "@/components/ui/avatar";
import { MetricCard } from "@/components/ui/metric-card";
import { PermissionBadge, type PermissionLevel } from "@/components/ui/permission-badge";
import { Badge } from "@/components/ui/badge";
import { getEffectivePermissions, getNasGroups, getNasUsersForUsersSection } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { getAnomalousPermissions } from "@/lib/permissions";
import { getPermissionLevel } from "@/lib/presentation";
import type { EffectivePermission, NasGroup, NasUser } from "@/types/api";

type ActivityFilter = "all" | "active" | "inactive";

type UserRow = {
  id: number;
  username: string;
  fullName: string;
  sourceUid: string;
  isActive: boolean;
  groupNames: string[];
  groupSummary: string;
  accessibleShares: number;
  maxPermission: PermissionLevel;
  hasMultiSourceAnomaly: boolean;
  anomalyCount: number;
  lastSeenSnapshotId: number | null;
};

export default function UsersPage() {
  const [users, setUsers] = useState<NasUser[]>([]);
  const [groups, setGroups] = useState<NasGroup[]>([]);
  const [permissions, setPermissions] = useState<EffectivePermission[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [activityFilter, setActivityFilter] = useState<ActivityFilter>("all");
  const [groupFilter, setGroupFilter] = useState("all");
  const [pageSize, setPageSize] = useState<10 | 30 | 100>(30);

  const deferredSearchTerm = useDeferredValue(searchTerm);

  useEffect(() => {
    if (selectedUserId == null) return;

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setSelectedUserId(null);
      }
    }

    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleEscape);

    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleEscape);
    };
  }, [selectedUserId]);

  useEffect(() => {
    async function loadUsers() {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        const [userItems, groupItems, permissionItems] = await Promise.all([
          getNasUsersForUsersSection(token),
          getNasGroups(token),
          getEffectivePermissions(token),
        ]);
        setUsers(userItems);
        setGroups(groupItems);
        setPermissions(permissionItems);
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento utenti");
      }
    }

    void loadUsers();
  }, []);

  const rows = useMemo<UserRow[]>(() => {
    const permissionByUser = permissions.reduce<Map<number, EffectivePermission[]>>((map, permission) => {
      const current = map.get(permission.nas_user_id) ?? [];
      current.push(permission);
      map.set(permission.nas_user_id, current);
      return map;
    }, new Map());

    return users.map((user) => {
      const userPermissions = permissionByUser.get(user.id) ?? [];
      const anomalousPermissions = getAnomalousPermissions(userPermissions);
      const anomalyCount = anomalousPermissions.length;
      const hasMultiSourceAnomaly = anomalyCount > 0;
      const groupNames = groups
        .filter((group) =>
          userPermissions.some((permission) =>
            permission.source_summary.includes(`group:${group.name}:`),
          ),
        )
        .map((group) => group.name)
        .sort((left, right) => left.localeCompare(right, "it"));
      const maxPermission = userPermissions.reduce<PermissionLevel>((current, permission) => {
        const level = getPermissionLevel(permission);
        const rank = { none: 0, read: 1, rw: 2, deny: 3 };
        return rank[level] > rank[current] ? level : current;
      }, "none");

      return {
        id: user.id,
        username: user.username,
        fullName: user.full_name ?? "Nome non disponibile",
        sourceUid: user.source_uid ?? "—",
        isActive: user.is_active,
        groupNames,
        groupSummary: groupNames.length > 0 ? groupNames.join(", ") : "Nessun gruppo dedotto",
        accessibleShares: new Set(
          userPermissions.filter((permission) => permission.can_read || permission.can_write).map((item) => item.share_id),
        ).size,
        maxPermission,
        hasMultiSourceAnomaly,
        anomalyCount,
        lastSeenSnapshotId: user.last_seen_snapshot_id,
      };
    });
  }, [users, groups, permissions]);

  const availableGroupOptions = useMemo(
    () =>
      [...new Set(rows.flatMap((row) => row.groupNames))]
        .sort((left, right) => left.localeCompare(right, "it")),
    [rows],
  );

  const filteredRows = useMemo(() => {
    const normalizedSearch = deferredSearchTerm.trim().toLowerCase();

    return rows.filter((row) => {
      if (activityFilter === "active" && !row.isActive) return false;
      if (activityFilter === "inactive" && row.isActive) return false;
      if (groupFilter !== "all" && !row.groupNames.includes(groupFilter)) return false;

      if (!normalizedSearch) return true;

      return [row.username, row.fullName, row.sourceUid].some((value) =>
        value.toLowerCase().includes(normalizedSearch),
      );
    });
  }, [rows, deferredSearchTerm, activityFilter, groupFilter]);

  const visibleRows = useMemo(
    () => filteredRows.slice(0, pageSize),
    [filteredRows, pageSize],
  );

  const columns = useMemo<ColumnDef<UserRow>[]>(
    () => [
      {
        header: "Utente NAS",
        accessorKey: "username",
        cell: ({ row }) => (
          <div className="flex items-center gap-3">
            <Avatar label={row.original.fullName === "Nome non disponibile" ? row.original.username : row.original.fullName} />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-[#1D4E35]">{row.original.username}</p>
              <p className="truncate text-xs text-gray-400">{row.original.fullName}</p>
            </div>
          </div>
        ),
      },
      {
        header: "Gruppi",
        accessorKey: "groupSummary",
        cell: ({ row }) => <span className="text-sm text-gray-600">{row.original.groupSummary}</span>,
      },
      {
        header: "Cartelle accessibili",
        accessorKey: "accessibleShares",
        cell: ({ row }) => <span className="text-sm font-medium text-gray-800">{row.original.accessibleShares}</span>,
      },
      {
        header: "Permesso massimo",
        accessorKey: "maxPermission",
        cell: ({ row }) => (
          <div className="flex items-center gap-1.5">
            <PermissionBadge level={row.original.maxPermission} />
            {row.original.hasMultiSourceAnomaly ? (
              <span
                title={`Permessi da ${row.original.anomalyCount} ${row.original.anomalyCount === 1 ? "cartella derivano" : "cartelle derivano"} da gruppi multipli. Aprire il dettaglio per analizzare le origini.`}
                className="inline-flex h-4 w-4 cursor-help items-center justify-center rounded-full bg-amber-100 text-xs font-medium text-amber-700 hover:bg-amber-200"
              >
                !
              </span>
            ) : null}
          </div>
        ),
      },
      {
        header: "Stato",
        accessorKey: "isActive",
        cell: ({ row }) => (
          <Badge variant={row.original.isActive ? "success" : "neutral"}>
            {row.original.isActive ? "Attivo" : "Inattivo"}
          </Badge>
        ),
      },
    ],
    [],
  );

  return (
    <ProtectedPage
      title="Utenti NAS"
      description="Vista amministrativa degli utenti sincronizzati con ricerca, stato operativo e accessi calcolati."
      breadcrumb="NAS Control"
      requiredSection="accessi.users"
    >
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <div className="surface-grid">
        <MetricCard label="Utenti NAS" value={users.length} sub="Account sincronizzati dall’ultimo snapshot" />
        <MetricCard label="Utenti attivi" value={users.filter((user) => user.is_active).length} sub="Account abilitati lato NAS" variant="success" />
        <MetricCard label="Con accessi" value={rows.filter((row) => row.accessibleShares > 0).length} sub="Utenti con almeno una cartella raggiungibile" />
        <MetricCard label="Con snapshot" value={users.filter((user) => user.last_seen_snapshot_id != null).length} sub="Record visti in sincronizzazione" />
      </div>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Filtri operativi</p>
          <p className="section-copy">Ricerca su username, nome completo e UID con filtro su stato account e gruppi dedotti.</p>
        </div>
        <TableFilters>
          <label className="text-sm font-medium text-gray-700">
            Cerca
            <input
              className="form-control mt-1"
              type="text"
              placeholder="Es. svc_naap, Mario, 1090"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
          </label>
          <label className="text-sm font-medium text-gray-700">
            Stato
            <select
              className="form-control mt-1"
              value={activityFilter}
              onChange={(event) => setActivityFilter(event.target.value as ActivityFilter)}
            >
              <option value="all">Tutti</option>
              <option value="active">Solo attivi</option>
              <option value="inactive">Solo inattivi</option>
            </select>
          </label>
          <label className="text-sm font-medium text-gray-700">
            Gruppo
            <select
              className="form-control mt-1"
              value={groupFilter}
              onChange={(event) => setGroupFilter(event.target.value)}
            >
              <option value="all">Tutti i gruppi</option>
              {availableGroupOptions.map((groupName) => (
                <option key={groupName} value={groupName}>
                  {groupName}
                </option>
              ))}
            </select>
          </label>
        </TableFilters>
      </article>

      <article className="panel-card overflow-hidden p-0">
        <div className="flex items-start justify-between gap-4 border-b border-gray-100 px-5 py-4">
          <div>
            <p className="section-title">Utenti sincronizzati</p>
            <p className="section-copy">La riga apre il dettaglio utente in modal con permessi, review e attività.</p>
          </div>
          <label className="text-sm font-medium text-gray-700">
            Mostra
            <select
              className="form-control mt-1 min-w-24"
              value={pageSize}
              onChange={(event) => setPageSize(Number(event.target.value) as 10 | 30 | 100)}
            >
              <option value={10}>10</option>
              <option value={30}>30</option>
              <option value={100}>100</option>
            </select>
          </label>
        </div>
        <DataTable
          data={visibleRows}
          columns={columns}
          emptyTitle="Nessun utente trovato"
          emptyDescription="Nessun utente corrisponde ai filtri selezionati."
          onRowClick={(row) => setSelectedUserId(row.id)}
        />
      </article>

      {selectedUserId != null ? (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-[#0E1712]/50 p-4 backdrop-blur-sm md:p-8">
          <button
            aria-label="Chiudi dettaglio utente"
            className="absolute inset-0 cursor-default"
            onClick={() => setSelectedUserId(null)}
            type="button"
          />
          <div className="relative z-10 max-h-[calc(100vh-2rem)] w-full max-w-5xl overflow-y-auto rounded-[28px] border border-gray-200 bg-[#F6F7F2] p-4 shadow-[0_30px_80px_rgba(15,25,19,0.18)] md:max-h-[calc(100vh-4rem)] md:p-6">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-gray-400">Dettaglio utente</p>
                <h3 className="mt-1 text-xl font-medium text-gray-900">Vista rapida operativa</h3>
              </div>
              <div className="flex items-center gap-3">
                <Link className="text-sm font-medium text-[#1D4E35]" href={`/nas-control/users/${selectedUserId}`}>
                  Apri pagina completa
                </Link>
                <button className="btn-secondary" onClick={() => setSelectedUserId(null)} type="button">
                  Chiudi
                </button>
              </div>
            </div>

            <UserDetailPanel userId={selectedUserId} compact onClose={() => setSelectedUserId(null)} />
          </div>
        </div>
      ) : null}
    </ProtectedPage>
  );
}
