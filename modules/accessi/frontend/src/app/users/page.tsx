"use client";

import Link from "next/link";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { ProtectedPage } from "@/components/app/protected-page";
import { DataTable } from "@/components/table/data-table";
import { TableFilters } from "@/components/table/table-filters";
import { Avatar } from "@/components/ui/avatar";
import { MetricCard } from "@/components/ui/metric-card";
import { PermissionBadge, type PermissionLevel } from "@/components/ui/permission-badge";
import { Badge } from "@/components/ui/badge";
import { getEffectivePermissions, getNasUsers } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { getPermissionLevel } from "@/lib/presentation";
import type { EffectivePermission, NasUser } from "@/types/api";

type ActivityFilter = "all" | "active" | "inactive";

type UserRow = {
  id: number;
  username: string;
  fullName: string;
  sourceUid: string;
  isActive: boolean;
  groupSummary: string;
  accessibleShares: number;
  maxPermission: PermissionLevel;
  lastSeenSnapshotId: number | null;
};

export default function UsersPage() {
  const [users, setUsers] = useState<NasUser[]>([]);
  const [permissions, setPermissions] = useState<EffectivePermission[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [activityFilter, setActivityFilter] = useState<ActivityFilter>("all");

  const deferredSearchTerm = useDeferredValue(searchTerm);

  useEffect(() => {
    async function loadUsers() {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        const [userItems, permissionItems] = await Promise.all([
          getNasUsers(token),
          getEffectivePermissions(token),
        ]);
        setUsers(userItems);
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
        groupSummary: userPermissions.length > 0 ? "Dominio sincronizzato" : "Nessun permesso",
        accessibleShares: new Set(
          userPermissions.filter((permission) => permission.can_read || permission.can_write).map((item) => item.share_id),
        ).size,
        maxPermission,
        lastSeenSnapshotId: user.last_seen_snapshot_id,
      };
    });
  }, [users, permissions]);

  const filteredRows = useMemo(() => {
    const normalizedSearch = deferredSearchTerm.trim().toLowerCase();

    return rows.filter((row) => {
      if (activityFilter === "active" && !row.isActive) return false;
      if (activityFilter === "inactive" && row.isActive) return false;

      if (!normalizedSearch) return true;

      return [row.username, row.fullName, row.sourceUid].some((value) =>
        value.toLowerCase().includes(normalizedSearch),
      );
    });
  }, [rows, deferredSearchTerm, activityFilter]);

  const columns = useMemo<ColumnDef<UserRow>[]>(
    () => [
      {
        header: "Utente NAS",
        accessorKey: "username",
        cell: ({ row }) => (
          <Link href={`/users/${row.original.id}`} className="flex items-center gap-3">
            <Avatar label={row.original.fullName === "Nome non disponibile" ? row.original.username : row.original.fullName} />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-gray-900">{row.original.username}</p>
              <p className="truncate text-xs text-gray-400">{row.original.fullName}</p>
            </div>
          </Link>
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
        cell: ({ row }) => <PermissionBadge level={row.original.maxPermission} />,
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
      {
        header: "Azione",
        accessorKey: "id",
        cell: ({ row }) => (
          <Link className="text-sm font-medium text-[#1D4E35]" href={`/users/${row.original.id}`}>
            Apri
          </Link>
        ),
      },
    ],
    [],
  );

  return (
    <ProtectedPage
      title="Utenti NAS"
      description="Vista amministrativa degli utenti sincronizzati con ricerca, stato operativo e accessi calcolati."
      breadcrumb="Accessi"
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
          <p className="section-copy">Ricerca su username, nome completo e UID con filtro sullo stato account.</p>
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
        </TableFilters>
      </article>

      <article className="panel-card overflow-hidden p-0">
        <div className="border-b border-gray-100 px-5 py-4">
          <p className="section-title">Utenti sincronizzati</p>
          <p className="section-copy">La riga collega al dettaglio utente con permessi, review e attività.</p>
        </div>
        <DataTable
          data={filteredRows}
          columns={columns}
          emptyTitle="Nessun utente trovato"
          emptyDescription="Nessun utente corrisponde ai filtri selezionati."
        />
      </article>
    </ProtectedPage>
  );
}
