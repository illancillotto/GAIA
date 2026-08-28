"use client";

import { useEffect, useRef, useState } from "react";

import type { GisTerritorioLayer } from "@/lib/api/territorio";
import type { GisBasemap } from "@/types/gis";

type OrtofotoStoricheSelectorProps = {
  layers: GisTerritorioLayer[];
  enabled: Record<string, boolean>;
  opacity: Record<string, number>;
  basemap: GisBasemap;
  onToggle: (layerId: string) => void;
  onOpacityChange: (layerId: string, opacity: number) => void;
};

function yearLabel(layer: GisTerritorioLayer): string {
  return layer.title.match(/\b(?:19|20)\d{2}(?:-\d{2,4})?\b/)?.[0] ?? layer.title;
}

function useOrtofotoSelection({
  layers, enabled, basemap, onToggle,
}: OrtofotoStoricheSelectorProps) {
  const [primaryId, setPrimaryId] = useState("");
  const [comparisonId, setComparisonId] = useState("");
  const previousBasemap = useRef(basemap);
  useEffect(() => {
    if (previousBasemap.current === basemap) return;
    previousBasemap.current = basemap;
    for (const layer of layers) {
      if (enabled[layer.id]) onToggle(layer.id);
    }
    setPrimaryId("");
    setComparisonId("");
  }, [basemap, enabled, layers, onToggle]);
  const selectPrimary = (layerId: string) => {
    if (primaryId && enabled[primaryId]) onToggle(primaryId);
    setPrimaryId(layerId);
    if (layerId && !enabled[layerId]) onToggle(layerId);
  };
  const selectComparison = (layerId: string) => {
    if (comparisonId && enabled[comparisonId]) onToggle(comparisonId);
    setComparisonId(layerId);
    if (layerId && !enabled[layerId]) onToggle(layerId);
  };
  return { primaryId, comparisonId, selectPrimary, selectComparison };
}

export default function OrtofotoStoricheSelector(props: OrtofotoStoricheSelectorProps) {
  const { layers, opacity, onOpacityChange } = props;
  const selection = useOrtofotoSelection(props);

  if (layers.length === 0) return null;

  return (
    <section className="rounded-xl border border-sky-200 bg-sky-50/90 p-3">
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-sky-900">
        Ortofoto storiche
      </p>
      <label className="mt-2 block text-xs font-semibold text-slate-700">
        Annata principale
        <select
          aria-label="Annata principale"
          className="mt-1 w-full rounded-lg border border-sky-200 bg-white px-2 py-1.5 text-sm"
          value={selection.primaryId}
          onChange={(event) => selection.selectPrimary(event.target.value)}
        >
          <option value="">Nessuna ortofoto</option>
          {layers.map((layer) => (
            <option key={layer.id} value={layer.id}>{yearLabel(layer)}</option>
          ))}
        </select>
      </label>
      <label className="mt-2 block text-xs font-semibold text-slate-700">
        Confronta con
        <select
          aria-label="Annata di confronto"
          className="mt-1 w-full rounded-lg border border-sky-200 bg-white px-2 py-1.5 text-sm disabled:opacity-50"
          value={selection.comparisonId}
          disabled={layers.length < 2}
          onChange={(event) => selection.selectComparison(event.target.value)}
        >
          <option value="">Nessun confronto</option>
          {layers.filter((layer) => layer.id !== selection.primaryId).map((layer) => (
            <option key={layer.id} value={layer.id}>{yearLabel(layer)}</option>
          ))}
        </select>
      </label>
      {selection.comparisonId ? (
        <label className="mt-2 block text-xs font-semibold text-slate-700">
          Trasparenza confronto
          <input
            aria-label="Trasparenza confronto"
            className="mt-1 w-full accent-sky-700"
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={opacity[selection.comparisonId] ?? 0.5}
            onChange={(event) => onOpacityChange(selection.comparisonId, Number(event.target.value))}
          />
        </label>
      ) : null}
      {layers.length < 2 ? (
        <p className="mt-2 text-xs leading-5 text-sky-800">
          Una sola annata e oggi autorizzata. Il confronto si attivera quando
          una seconda ortofoto con licenza verificata entrera nel catalogo.
        </p>
      ) : null}
    </section>
  );
}
