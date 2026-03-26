"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { TableFilters } from "@/components/table/table-filters";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { SearchIcon, UsersIcon } from "@/components/ui/icons";
import { getEffectivePermissions, getNasGroups } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { cn } from "@/lib/cn";
import type { EffectivePermission, NasGroup } from "@/types/api";

type SnapshotFilter = "all" | "with-snapshot" | "without-snapshot";
type GroupScopeFilter = "operational" | "all";

const SYNOLOGY_SERVICE_GROUPS = new Set([
  "myds",
  "payment",
  "http",
  "filestation",
  "hybridsharesystem",
  "postfix",
]);

const SYSTEM_GROUP_NAME_PATTERNS = [
  /^avahi$/i,
  /^bind$/i,
  /^daemon$/i,
  /^dbus$/i,
  /^dovecot$/i,
  /^ftp$/i,
  /^ldap$/i,
  /^log$/i,
  /^lp$/i,
  /^maildrop$/i,
  /^mysql$/i,
  /^nobody$/i,
  /^ntp$/i,
  /^postgres$/i,
  /^python\d*$/i,
  /^root$/i,
  /^rpc$/i,
  /^smmsp$/i,
  /^syno/i,
  /^system$/i,
  /^taskmgr$/i,
  /^tokenmgr$/i,
  /^videodriver$/i,
  /^vmcomm$/i,
  /^wheel$/i,
  /service/i,
  /quickconnect/i,
  /storagemanager/i,
  /oauth/i,
  /securesignin/i,
];

function isSystemGroup(group: NasGroup): boolean {
  const normalizedName = group.name.trim();
  const normalizedDescription = (group.description ?? "").trim().toLowerCase();

  if (
    normalizedDescription.startsWith("system default") ||
    normalizedDescription.includes("default group") ||
    normalizedDescription.includes("web services")
  ) {
    return true;
  }

  return SYSTEM_GROUP_NAME_PATTERNS.some((pattern) => pattern.test(normalizedName));
}

function isSynologyServiceGroup(group: NasGroup): boolean {
  return SYNOLOGY_SERVICE_GROUPS.has(group.name.trim().toLowerCase());
}

export default function GroupsPage() {
  const [groups, setGroups] = useState<NasGroup[]>([]);
  const [permissions, setPermissions] = useState<EffectivePermission[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [snapshotFilter, setSnapshotFilter] = useState<SnapshotFilter>("all");
  const [scopeFilter, setScopeFilter] = useState<GroupScopeFilter>("operational");
  const [showSynologyServiceGroups, setShowSynologyServiceGroups] = useState(false);

  const deferredSearchTerm = useDeferredValue(searchTerm);

  useEffect(() => {
    async function loadGroups() {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        const [groupItems, permissionItems] = await Promise.all([
          getNasGroups(token),
          getEffectivePermissions(token),
        ]);
        setGroups(groupItems);
        setPermissions(permissionItems);
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento gruppi");
      }
    }

    void loadGroups();
  }, []);

  const filteredGroups = useMemo(() => {
    const normalizedSearch = deferredSearchTerm.trim().toLowerCase();

    return groups
      .filter((group) => {
        if (snapshotFilter === "with-snapshot" && group.last_seen_snapshot_id == null) return false;
        if (snapshotFilter === "without-snapshot" && group.last_seen_snapshot_id != null) return false;
        if (scopeFilter === "operational" && isSystemGroup(group)) return false;
        if (!showSynologyServiceGroups && isSynologyServiceGroup(group)) return false;

        if (!normalizedSearch) return true;

        return [group.name, group.description ?? ""].some((value) =>
          value.toLowerCase().includes(normalizedSearch),
        );
      })
      .sort((left, right) => left.name.localeCompare(right.name, "it"));
  }, [groups, deferredSearchTerm, snapshotFilter, scopeFilter, showSynologyServiceGroups]);

  const systemGroupCount = useMemo(
    () => groups.filter((group) => isSystemGroup(group)).length,
    [groups],
  );
  const operationalGroupCount = groups.length - systemGroupCount;
  const permissionStatsByGroup = useMemo(() => {
    const stats = new Map<
      string,
      {
        readOnlyUsers: number;
        writeUsers: number;
        mixedUsers: number;
      }
    >();

    for (const group of groups) {
      const userStates = new Map<number, { hasRead: boolean; hasWrite: boolean }>();

      permissions.forEach((permission) => {
        if (!permission.source_summary.includes(`group:${group.name}:`)) {
          return;
        }

        const current = userStates.get(permission.nas_user_id) ?? { hasRead: false, hasWrite: false };
        if (permission.can_read) {
          current.hasRead = true;
        }
        if (permission.can_write) {
          current.hasWrite = true;
        }
        userStates.set(permission.nas_user_id, current);
      });

      let readOnlyUsers = 0;
      let writeUsers = 0;
      let mixedUsers = 0;

      userStates.forEach((state) => {
        if (state.hasRead && state.hasWrite) {
          mixedUsers += 1;
          return;
        }

        if (state.hasWrite) {
          writeUsers += 1;
          return;
        }

        if (state.hasRead) {
          readOnlyUsers += 1;
        }
      });

      stats.set(group.name, {
        readOnlyUsers,
        writeUsers,
        mixedUsers,
      });
    }

    return stats;
  }, [groups, permissions]);

  return (
    <ProtectedPage
      title="Gruppi NAS"
      description="Vista dei gruppi presenti nel dominio sincronizzato con focus operativo sui gruppi utili all’audit."
      breadcrumb="NAS Control"
    >
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <div className="surface-grid">
        <MetricCard label="Gruppi operativi" value={operationalGroupCount} sub="Gruppi rilevanti per audit e dominio" />
        <MetricCard label="Gruppi di sistema" value={systemGroupCount} sub="Gruppi tecnici o di servizio NAS" variant="warning" />
        <MetricCard label="Con snapshot" value={groups.filter((item) => item.last_seen_snapshot_id != null).length} sub="Visti almeno una volta" />
        <MetricCard label="Con descrizione" value={groups.filter((item) => Boolean(item.description)).length} sub="Gruppi con metadata descrittivi" />
        <MetricCard label="Senza snapshot" value={groups.filter((item) => item.last_seen_snapshot_id == null).length} sub="Da verificare nei cicli sync" />
      </div>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Filtri</p>
          <p className="section-copy">Ricerca su nome e descrizione con filtro snapshot e separazione tra gruppi operativi e tecnici.</p>
        </div>
        <TableFilters>
          <label className="text-sm font-medium text-gray-700">
            Cerca
            <input
              className="form-control mt-1"
              type="text"
              placeholder="Es. administrators, protocollo"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
          </label>
          <label className="text-sm font-medium text-gray-700">
            Snapshot
            <select
              className="form-control mt-1"
              value={snapshotFilter}
              onChange={(event) => setSnapshotFilter(event.target.value as SnapshotFilter)}
            >
              <option value="all">Tutti</option>
              <option value="with-snapshot">Con snapshot</option>
              <option value="without-snapshot">Senza snapshot</option>
            </select>
          </label>
          <label className="text-sm font-medium text-gray-700">
            Tipologia
            <select
              className="form-control mt-1"
              value={scopeFilter}
              onChange={(event) => setScopeFilter(event.target.value as GroupScopeFilter)}
            >
              <option value="operational">Solo gruppi operativi</option>
              <option value="all">Tutti i gruppi</option>
            </select>
          </label>
          <label className="flex items-center gap-3 self-end rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm font-medium text-gray-700">
            <input
              checked={showSynologyServiceGroups}
              className="h-4 w-4 rounded border-gray-300 text-[#1D4E35] focus:ring-[#1D4E35]"
              onChange={(event) => setShowSynologyServiceGroups(event.target.checked)}
              type="checkbox"
            />
            Mostra gruppi Synology
          </label>
        </TableFilters>
      </article>

      {filteredGroups.length === 0 ? (
        <EmptyState
          icon={SearchIcon}
          title="Nessun gruppo trovato"
          description="Nessun gruppo corrisponde ai filtri selezionati."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filteredGroups.map((group) => (
            <article key={group.id} className="panel-card">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#D3EAD4] text-[#1D4E35]">
                  <UsersIcon className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-gray-900">{group.name}</p>
                  <p className="mt-1 text-xs text-gray-400">{group.description ?? "Descrizione non disponibile"}</p>
                  <div className="mt-2">
                    <Badge
                      className={cn(
                        isSystemGroup(group) || isSynologyServiceGroup(group)
                          ? "bg-gray-100 text-gray-500"
                          : "bg-[#EAF3E8] text-[#1D4E35]",
                      )}
                    >
                      {isSynologyServiceGroup(group)
                        ? "Servizio Synology"
                        : isSystemGroup(group)
                          ? "Tecnico / sistema"
                          : "Operativo"}
                    </Badge>
                  </div>
                </div>
                <Badge variant={group.last_seen_snapshot_id != null ? "success" : "warning"}>
                  {group.last_seen_snapshot_id != null ? "Presente" : "Da verificare"}
                </Badge>
              </div>
              <div className="mt-4 overflow-hidden rounded-lg border border-gray-100">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-xs uppercase tracking-[0.08em] text-gray-400">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium">Lettura</th>
                      <th className="px-3 py-2 text-left font-medium">Scrittura</th>
                      <th className="px-3 py-2 text-left font-medium">Misto</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-t border-gray-100 text-gray-700">
                      <td className="px-3 py-2 font-medium">
                        {permissionStatsByGroup.get(group.name)?.readOnlyUsers ?? 0}
                      </td>
                      <td className="px-3 py-2 font-medium">
                        {permissionStatsByGroup.get(group.name)?.writeUsers ?? 0}
                      </td>
                      <td className="px-3 py-2 font-medium">
                        {permissionStatsByGroup.get(group.name)?.mixedUsers ?? 0}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="mt-4 border-t border-gray-50 pt-3 text-xs text-gray-400">
                Ultimo snapshot: {group.last_seen_snapshot_id ?? "—"}
              </div>
            </article>
          ))}
        </div>
      )}
    </ProtectedPage>
  );
}
