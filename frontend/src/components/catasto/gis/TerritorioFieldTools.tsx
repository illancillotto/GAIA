"use client";

import { useState } from "react";

import { MeasurementTools } from "./DrawingTools";
import { buildTerritorioPrintHtml, mapScaleDenominator } from "./territorio-print";
import { useTerritorioMeasurement, type MeasurementMap } from "./use-territorio-measurement";
import type { GisTerritorioLayerGroup } from "@/lib/api/territorio";

export type FieldMap = MeasurementMap & { getCanvas: () => HTMLCanvasElement; getCenter: () => { lat: number }; getZoom: () => number };

export function printTerritorioMap(map: FieldMap | null, groups: GisTerritorioLayerGroup[], enabled: Record<string, boolean>, openWindow = window.open.bind(window)): void {
  if (!map) return;
  const popup = openWindow("", "_blank");
  if (!popup) return;
  popup.opener = null;
  const layers = groups.flatMap((group) => group.layers).filter((layer) => enabled[layer.id]);
  const html = buildTerritorioPrintHtml({ image: map.getCanvas().toDataURL("image/png"), scale: mapScaleDenominator(map.getCenter().lat, map.getZoom()), layers });
  popup.document.write(html);
  popup.document.close();
  popup.focus();
  popup.print();
}

export default function TerritorioFieldTools({ map, groups, enabled, compact = false }: { map: FieldMap | null; groups: GisTerritorioLayerGroup[]; enabled: Record<string, boolean>; compact?: boolean }) {
  const [measurementOpen, setMeasurementOpen] = useState(false);
  const measurement = useTerritorioMeasurement(map);
  if (compact) {
    return (
      <div data-gis-field-tools="toolbar" className="relative flex items-center gap-1">
        <button
          type="button"
          aria-label="Misure sul terreno"
          aria-expanded={measurementOpen}
          onClick={() => setMeasurementOpen((value) => !value)}
          className={`inline-flex h-9 items-center gap-1.5 rounded-lg border px-2.5 text-xs font-semibold transition ${measurementOpen || measurement.mode ? "border-emerald-300 bg-emerald-100 text-emerald-950" : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"}`}
          title="Misure sul terreno"
        >
          <span aria-hidden="true" className="material-symbols-outlined text-[18px]">straighten</span>
          <span className="hidden xl:inline">Misure</span>
        </button>
        <button
          type="button"
          aria-label="Stampa mappa territoriale"
          onClick={() => printTerritorioMap(map, groups, enabled)}
          disabled={!map}
          className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
          title="Stampa mappa territoriale"
        >
          <span aria-hidden="true" className="material-symbols-outlined text-[18px]">print</span>
          <span className="hidden xl:inline">Stampa</span>
        </button>
        {measurementOpen ? (
          <div className="fixed left-3 right-3 top-[calc(var(--gis-top,52px)+4.5rem)] z-50 sm:absolute sm:left-auto sm:right-0 sm:top-11 sm:w-[min(24rem,calc(100vw-2rem))]">
            <MeasurementTools {...measurement} onModeChange={measurement.setMode} onClear={measurement.clear} />
          </div>
        ) : null}
      </div>
    );
  }
  return <div data-gis-field-tools="overlay" className="absolute bottom-4 left-4 z-20 w-[min(24rem,calc(100%-2rem))] space-y-2"><MeasurementTools {...measurement} onModeChange={measurement.setMode} onClear={measurement.clear} /><button type="button" onClick={() => printTerritorioMap(map, groups, enabled)} disabled={!map} className="w-full rounded-xl bg-amber-700 px-4 py-3 text-sm font-bold text-white disabled:opacity-50">Stampa mappa territoriale</button></div>;
}
