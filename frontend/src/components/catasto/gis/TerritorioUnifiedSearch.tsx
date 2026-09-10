"use client";

import { useState } from "react";
import type { Map as MapLibreMap } from "maplibre-gl";

import type { GisTerritorioLayerGroup } from "@/lib/api/territorio";
import { useTerritorioUnifiedSearch } from "./use-territorio-unified-search";
import type { TerritorioSearchResult } from "./territorio-unified-search";

type SearchMap = Pick<MapLibreMap, "fitBounds" | "flyTo" | "querySourceFeatures">;
type SearchController = ReturnType<typeof useTerritorioUnifiedSearch>;

function UnifiedSearchPanel({ search, municipalEnabled, embedded }: {
  search: SearchController;
  municipalEnabled: boolean;
  embedded: boolean;
}) {
  return (
    <section className={embedded
      ? "w-full rounded-2xl border border-white/30 bg-white/95 p-3 shadow-2xl backdrop-blur"
      : "absolute left-3 top-24 z-10 w-[min(390px,calc(100%-1.5rem))] rounded-2xl border border-white/30 bg-white/95 p-3 shadow-2xl backdrop-blur"}
      aria-label="Ricerca unica GIS"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-emerald-700">Ricerca nel comprensorio</p>
          <p className="mt-1 text-xs text-slate-500">Particelle, distretti, PdC caricati in mappa, comuni RAS e coordinate. Non cerca indirizzi o numeri civici.</p>
        </div>
        {search.results.length ? <button type="button" onClick={search.clear} className="text-xs font-semibold text-slate-500 hover:text-slate-900">Pulisci</button> : null}
      </div>
      <form className="mt-3 flex gap-2" onSubmit={(event) => { event.preventDefault(); void search.runSearch(); }}>
        <input type="search" aria-label="Cerca nel GIS" value={search.query} onChange={(event) => search.setQuery(event.target.value)} placeholder="Particella, distretto, PdC, comune, coordinate" className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100" />
        <button type="submit" disabled={search.busy} className="rounded-xl bg-[#1D4E35] px-3 py-2 text-xs font-semibold text-white disabled:opacity-60">{search.busy ? "Ricerca..." : "Cerca"}</button>
      </form>
      {!municipalEnabled ? <p className="mt-2 text-[11px] text-amber-700">Per cercare un comune, attiva “Limiti amministrativi comunali CTR”.</p> : null}
      {search.message ? <p role="status" className="mt-2 rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800">{search.message}</p> : null}
      {search.results.length ? (
        <ul className="mt-2 max-h-64 space-y-1.5 overflow-y-auto pr-1">
          {search.results.map((result) => (
            <li key={result.id}>
              <button type="button" onClick={() => void search.selectResult(result)} className="w-full rounded-xl border border-slate-100 bg-white px-3 py-2 text-left transition hover:border-emerald-200 hover:bg-emerald-50/50">
                <span className="flex items-center justify-between gap-2"><span className="truncate text-xs font-semibold text-slate-900">{result.label}</span><span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">{result.source}</span></span>
                <span className="mt-0.5 block truncate text-[11px] text-slate-500">{result.detail}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

export default function TerritorioUnifiedSearch({
  token,
  map,
  groups,
  enabled,
  compact = false,
  onSearchResults,
  onResultFocus,
}: {
  token: string | null;
  map: SearchMap | null;
  groups: GisTerritorioLayerGroup[];
  enabled: Record<string, boolean>;
  compact?: boolean;
  onSearchResults?: (results: TerritorioSearchResult[]) => void;
  onResultFocus?: (result: TerritorioSearchResult) => void;
}) {
  const [open, setOpen] = useState(false);
  const municipal = groups.flatMap((group) => group.layers).find(
    (layer) => layer.name === "ras_limiti_comunali" && layer.queryable === "wfs_queryable" && enabled[layer.id],
  ) ?? null;
  const search = useTerritorioUnifiedSearch({
    token,
    map,
    municipalityLayer: municipal,
    onSearchResults,
    onResultFocus,
  });

  const panel = <UnifiedSearchPanel search={search} municipalEnabled={municipal !== null} embedded={compact} />;

  if (!compact) return panel;
  return (
    <div data-gis-search="toolbar" className="relative flex items-center">
      <button
        type="button"
        aria-label="Ricerca nel comprensorio"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className={`inline-flex h-9 items-center gap-1.5 rounded-lg border px-2.5 text-xs font-semibold transition ${open || search.results.length ? "border-emerald-300 bg-emerald-100 text-emerald-950" : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"}`}
        title="Ricerca nel comprensorio"
      >
        <span aria-hidden="true" className="material-symbols-outlined text-[18px]">search</span>
        <span className="hidden xl:inline">Cerca</span>
      </button>
      {open ? (
        <div className="fixed left-3 right-3 top-[calc(var(--gis-top,52px)+4.5rem)] z-50 sm:left-[calc(var(--gis-left,0px)+0.75rem)] sm:right-auto sm:top-[calc(var(--gis-top,52px)+3.75rem)] sm:w-[390px]">
          {panel}
        </div>
      ) : null}
    </div>
  );
}
