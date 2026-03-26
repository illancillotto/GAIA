"use client";

import Link from "next/link";
import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { ShareDetailPanel } from "@/components/app/share-detail-panel";
import { TableFilters } from "@/components/table/table-filters";
import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { FolderIcon, SearchIcon } from "@/components/ui/icons";
import { Badge } from "@/components/ui/badge";
import { getEffectivePermissions, getShares } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { EffectivePermission, Share } from "@/types/api";

type SectorFilter = "all" | "with-sector" | "without-sector";

type ShareRow = Share & {
  userCount: number;
  denyCount: number;
};

export default function SharesPage() {
  const [shares, setShares] = useState<Share[]>([]);
  const [permissions, setPermissions] = useState<EffectivePermission[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedShareId, setSelectedShareId] = useState<number | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [sectorFilter, setSectorFilter] = useState<SectorFilter>("all");

  const deferredSearchTerm = useDeferredValue(searchTerm);

  useEffect(() => {
    async function loadShares() {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        const [shareItems, permissionItems] = await Promise.all([getShares(token), getEffectivePermissions(token)]);
        setShares(shareItems);
        setPermissions(permissionItems);
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento share");
      }
    }

    void loadShares();
  }, []);

  useEffect(() => {
    if (selectedShareId == null) return;

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setSelectedShareId(null);
      }
    }

    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleEscape);

    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleEscape);
    };
  }, [selectedShareId]);

  const shareRows = useMemo<ShareRow[]>(() => {
    return shares.map((share) => {
      const related = permissions.filter((permission) => permission.share_id === share.id);
      return {
        ...share,
        userCount: new Set(related.filter((item) => item.can_read || item.can_write).map((item) => item.nas_user_id)).size,
        denyCount: related.filter((item) => item.is_denied).length,
      };
    });
  }, [shares, permissions]);

  const filteredShares = useMemo(() => {
    const normalizedSearch = deferredSearchTerm.trim().toLowerCase();

    return shareRows
      .filter((share) => {
        if (sectorFilter === "with-sector" && !share.sector) return false;
        if (sectorFilter === "without-sector" && share.sector) return false;

        if (!normalizedSearch) return true;

        return [share.name, share.path, share.sector ?? "", share.description ?? ""].some((value) =>
          value.toLowerCase().includes(normalizedSearch),
        );
      })
      .sort((left, right) => left.name.localeCompare(right.name, "it"));
  }, [shareRows, deferredSearchTerm, sectorFilter]);

  return (
    <ProtectedPage
      title="Cartelle condivise"
      description="Catalogo delle share del NAS con indicatori di accesso, deny e classificazione settoriale."
      breadcrumb="NAS Control"
    >
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <div className="surface-grid">
        <MetricCard label="Share NAS" value={shares.length} sub="Cartelle condivise sincronizzate" />
        <MetricCard label="Con settore" value={shares.filter((share) => Boolean(share.sector)).length} sub="Share con classificazione funzionale" />
        <MetricCard label="Con deny" value={shareRows.filter((share) => share.denyCount > 0).length} sub="Share con almeno un deny attivo" variant="danger" />
        <MetricCard label="Con utenti" value={shareRows.filter((share) => share.userCount > 0).length} sub="Share con accessi calcolati" />
      </div>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Filtri</p>
          <p className="section-copy">Ricerca su nome, path, settore e descrizione.</p>
        </div>
        <TableFilters>
          <label className="text-sm font-medium text-gray-700">
            Cerca
            <input
              className="form-control mt-1"
              type="text"
              placeholder="Es. EmailSaver, /volume1, legali"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
          </label>
          <label className="text-sm font-medium text-gray-700">
            Settore
            <select
              className="form-control mt-1"
              value={sectorFilter}
              onChange={(event) => setSectorFilter(event.target.value as SectorFilter)}
            >
              <option value="all">Tutte</option>
              <option value="with-sector">Con settore</option>
              <option value="without-sector">Senza settore</option>
            </select>
          </label>
        </TableFilters>
      </article>

      {filteredShares.length === 0 ? (
        <EmptyState
          icon={SearchIcon}
          title="Nessuna cartella trovata"
          description="Nessuna share corrisponde ai filtri selezionati."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filteredShares.map((share) => (
            <button
              key={share.id}
              className="block rounded-xl border border-gray-100 bg-white p-4 text-left shadow-panel transition hover:border-gray-200 hover:shadow-sm"
              onClick={() => setSelectedShareId(share.id)}
              type="button"
            >
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#D3EAD4]">
                  <FolderIcon className="h-5 w-5 text-[#1D4E35]" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-gray-900">{share.name}</p>
                  <p className="truncate text-xs text-gray-400">{share.path}</p>
                </div>
                {share.denyCount > 0 ? <Badge variant="danger">{share.denyCount} deny</Badge> : null}
              </div>
              <div className="mt-3 border-t border-gray-50 pt-3 text-xs text-gray-400">
                <div className="flex items-center gap-2">
                  <span>{share.userCount} utenti</span>
                  <span>·</span>
                  <span>{share.last_seen_snapshot_id ?? "—"} snapshot</span>
                </div>
                <div className="mt-2 flex items-center justify-between gap-3">
                  <Link
                    className="text-xs font-medium text-[#1D4E35] underline-offset-2 hover:underline"
                    href={`/nas-control/shares/${share.id}`}
                    onClick={(event) => event.stopPropagation()}
                  >
                    Apri pagina completa
                  </Link>
                  {share.sector ? <p className="text-right">{share.sector}</p> : null}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {selectedShareId != null ? (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-[#0E1712]/50 p-4 backdrop-blur-sm md:p-8">
          <button
            aria-label="Chiudi dettaglio cartella"
            className="absolute inset-0 cursor-default"
            onClick={() => setSelectedShareId(null)}
            type="button"
          />
          <div className="relative z-10 max-h-[calc(100vh-2rem)] w-full max-w-5xl overflow-y-auto rounded-[28px] border border-gray-200 bg-[#F6F7F2] p-4 shadow-[0_30px_80px_rgba(15,25,19,0.18)] md:max-h-[calc(100vh-4rem)] md:p-6">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-gray-400">Dettaglio cartella</p>
                <h3 className="mt-1 text-xl font-medium text-gray-900">Vista rapida operativa</h3>
              </div>
              <div className="flex items-center gap-3">
                <Link className="text-sm font-medium text-[#1D4E35]" href={`/nas-control/shares/${selectedShareId}`}>
                  Apri pagina completa
                </Link>
                <button className="btn-secondary" onClick={() => setSelectedShareId(null)} type="button">
                  Chiudi
                </button>
              </div>
            </div>

            <ShareDetailPanel shareId={selectedShareId} compact onClose={() => setSelectedShareId(null)} />
          </div>
        </div>
      ) : null}
    </ProtectedPage>
  );
}
