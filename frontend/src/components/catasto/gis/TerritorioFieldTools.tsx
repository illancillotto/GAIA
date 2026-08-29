"use client";

import { MeasurementTools } from "./DrawingTools";
import { buildTerritorioPrintHtml, mapScaleDenominator } from "./territorio-print";
import { useTerritorioMeasurement, type MeasurementMap } from "./use-territorio-measurement";
import type { GisTerritorioLayerGroup } from "@/lib/api/territorio";

export type FieldMap = MeasurementMap & { getCanvas: () => HTMLCanvasElement; getCenter: () => { lat: number }; getZoom: () => number };

export function printTerritorioMap(map: FieldMap | null, groups: GisTerritorioLayerGroup[], enabled: Record<string, boolean>, openWindow = window.open.bind(window)): void {
  if (!map) return;
  const layers = groups.flatMap((group) => group.layers).filter((layer) => enabled[layer.id]);
  const html = buildTerritorioPrintHtml({ image: map.getCanvas().toDataURL("image/png"), scale: mapScaleDenominator(map.getCenter().lat, map.getZoom()), layers });
  const popup = openWindow("", "_blank", "noopener,noreferrer");
  if (!popup) return;
  popup.document.write(html);
  popup.document.close();
  popup.print();
}

export default function TerritorioFieldTools({ map, groups, enabled }: { map: FieldMap | null; groups: GisTerritorioLayerGroup[]; enabled: Record<string, boolean> }) {
  const measurement = useTerritorioMeasurement(map);
  return <div className="absolute bottom-4 left-4 z-20 w-[min(24rem,calc(100%-2rem))] space-y-2"><MeasurementTools {...measurement} onModeChange={measurement.setMode} onClear={measurement.clear} /><button type="button" onClick={() => printTerritorioMap(map, groups, enabled)} disabled={!map} className="w-full rounded-xl bg-amber-700 px-4 py-3 text-sm font-bold text-white disabled:opacity-50">Stampa mappa territoriale</button></div>;
}
