"use client";

import type { GisTerritorioLayer } from "@/lib/api/territorio";

type IncendiAnnualiSelectorProps = {
  layers: GisTerritorioLayer[];
  enabled: Record<string, boolean>;
  onToggle: (layerId: string) => void;
};

function layerYear(layer: GisTerritorioLayer): string {
  return layer.name.slice(-4);
}

export default function IncendiAnnualiSelector({
  layers,
  enabled,
  onToggle,
}: IncendiAnnualiSelectorProps) {
  const orderedLayers = [...layers].sort((left, right) =>
    layerYear(right).localeCompare(layerYear(left)),
  );
  const activeLayer = orderedLayers.find((layer) => enabled[layer.id]);

  const selectYear = (layerId: string) => {
    for (const layer of orderedLayers) {
      if (enabled[layer.id] && layer.id !== layerId) onToggle(layer.id);
    }
    if (layerId && !enabled[layerId]) onToggle(layerId);
  };

  return (
    <div className="mt-2 rounded-lg bg-amber-50 p-2">
      <label className="block text-xs font-semibold text-amber-950">
        Anno aree percorse dal fuoco
        <select
          aria-label="Anno aree percorse dal fuoco"
          className="mt-1 w-full rounded-lg border border-amber-200 bg-white px-2 py-1.5 text-sm"
          value={activeLayer?.id ?? ""}
          onChange={(event) => selectYear(event.target.value)}
        >
          <option value="">Nessuna annata</option>
          {orderedLayers.map((layer) => (
            <option key={layer.id} value={layer.id}>
              {layerYear(layer)}
            </option>
          ))}
        </select>
      </label>
      <p className="mt-1 text-[11px] leading-4 text-amber-900">
        Una annata alla volta per mantenere leggibile la mappa.
      </p>
    </div>
  );
}
