"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { TableFilters } from "@/components/table/table-filters";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { SearchIcon, UsersIcon } from "@/components/ui/icons";
import { getNasGroups } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { NasGroup } from "@/types/api";

type SnapshotFilter = "all" | "with-snapshot" | "without-snapshot";

export default function GroupsPage() {
  const [groups, setGroups] = useState<NasGroup[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [snapshotFilter, setSnapshotFilter] = useState<SnapshotFilter>("all");

  const deferredSearchTerm = useDeferredValue(searchTerm);

  useEffect(() => {
    async function loadGroups() {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        setGroups(await getNasGroups(token));
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

        if (!normalizedSearch) return true;

        return [group.name, group.description ?? ""].some((value) =>
          value.toLowerCase().includes(normalizedSearch),
        );
      })
      .sort((left, right) => left.name.localeCompare(right.name, "it"));
  }, [groups, deferredSearchTerm, snapshotFilter]);

  return (
    <ProtectedPage
      title="Gruppi NAS"
      description="Vista dei gruppi presenti nel dominio sincronizzato con focus su presenza nel ciclo di snapshot."
      breadcrumb="Accessi"
    >
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <div className="surface-grid">
        <MetricCard label="Gruppi NAS" value={groups.length} sub="Gruppi sincronizzati dal NAS" />
        <MetricCard label="Con snapshot" value={groups.filter((item) => item.last_seen_snapshot_id != null).length} sub="Visti almeno una volta" />
        <MetricCard label="Con descrizione" value={groups.filter((item) => Boolean(item.description)).length} sub="Gruppi con metadata descrittivi" />
        <MetricCard label="Senza snapshot" value={groups.filter((item) => item.last_seen_snapshot_id == null).length} sub="Da verificare nei cicli sync" variant="warning" />
      </div>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Filtri</p>
          <p className="section-copy">Ricerca su nome e descrizione del gruppo con filtro snapshot.</p>
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
                </div>
                <Badge variant={group.last_seen_snapshot_id != null ? "success" : "warning"}>
                  {group.last_seen_snapshot_id != null ? "Presente" : "Da verificare"}
                </Badge>
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
