"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RiordinoStatusBadge } from "@/components/riordino/shared/status-badge";
import { listRiordinoBlocks } from "@/lib/riordino-api";
import type { RiordinoBlock } from "@/types/riordino";

export function RiordinoBlockList({ token, limit }: { token: string; limit?: number }) {
  const [items, setItems] = useState<RiordinoBlock[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData(): Promise<void> {
      try {
        const response = await listRiordinoBlocks(token, { per_page: String(limit ?? 100) });
        setItems(response.items);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore nel caricamento blocchi");
      }
    }

    void loadData();
  }, [limit, token]);

  return (
    <article className="panel-card">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="section-title">Blocchi di riordino</p>
          <p className="section-copy">Ogni blocco parte da snapshot AdE e guida confronto, visure Sister e lavorazioni operatori.</p>
        </div>
        <Link className="btn-secondary" href="/riordino/blocchi">
          Vedi tutti
        </Link>
      </div>
      {loadError ? <p className="mb-4 text-sm text-red-600">{loadError}</p> : null}
      {items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-5 py-8">
          <p className="text-sm font-medium text-gray-800">Nessun blocco disponibile.</p>
          <p className="mt-1 text-sm text-gray-500">Il super admin potrà creare blocchi da comune, lotto/maglia, lista particelle o selezione GIS.</p>
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {items.map((block) => (
            <Link
              key={block.id}
              href={`/riordino/blocchi/${block.id}`}
              className="group rounded-3xl border border-[#d7e3d5] bg-gradient-to-br from-[#fbf8ef] to-white p-5 transition hover:-translate-y-0.5 hover:border-[#9dbb95] hover:shadow-lg"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#617c55]">{block.code}</p>
                  <h3 className="mt-2 text-lg font-semibold text-gray-950 group-hover:text-[#1d4e35]">{block.title}</h3>
                  <p className="mt-1 text-sm text-gray-500">{block.municipality ?? "Comune non specificato"}</p>
                </div>
                <RiordinoStatusBadge value={block.status} />
              </div>
              <div className="mt-5 grid grid-cols-3 gap-3 text-sm">
                <div className="rounded-2xl bg-white/75 px-3 py-2">
                  <p className="text-xs text-gray-500">Particelle</p>
                  <p className="text-lg font-semibold text-gray-950">{block.parcel_count}</p>
                </div>
                <div className="rounded-2xl bg-white/75 px-3 py-2">
                  <p className="text-xs text-gray-500">Disall.</p>
                  <p className="text-lg font-semibold text-amber-700">{block.mismatch_count}</p>
                </div>
                <div className="rounded-2xl bg-white/75 px-3 py-2">
                  <p className="text-xs text-gray-500">Criterio</p>
                  <p className="truncate text-sm font-semibold text-gray-900">{block.selection_type}</p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </article>
  );
}
