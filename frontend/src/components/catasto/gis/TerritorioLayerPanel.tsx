"use client";

import { useState } from "react";
import Image from "next/image";

import IncendiAnnualiSelector from "@/components/catasto/gis/IncendiAnnualiSelector";
import OrtofotoStoricheSelector from "@/components/catasto/gis/OrtofotoStoricheSelector";
import type { TerritorioLayerState } from "@/components/catasto/gis/use-territorio-layers";
import type { GisTerritorioLayer, GisTerritorioLayerGroup } from "@/lib/api/territorio";
import type { GisBasemap } from "@/types/gis";

type TerritorioLayerPanelProps = TerritorioLayerState & {
  basemap: GisBasemap;
};

type LayerItemProps = Pick<TerritorioLayerState, "enabled" | "opacity" | "layerErrors" | "legendUrls" | "toggleLayer" | "setLayerOpacity"> & {
  layer: GisTerritorioLayer;
};

function TerritorioLayerItem({
  layer, enabled, opacity, layerErrors, legendUrls, toggleLayer, setLayerOpacity,
}: LayerItemProps) {
  const isEnabled = Boolean(enabled[layer.id]);
  const layerOpacity = opacity[layer.id] ?? layer.default_opacity;
  return (
    <article className="border-t border-stone-100 pt-2 first:border-0 first:pt-0">
      <label className="flex cursor-pointer items-start gap-2">
        <input type="checkbox" className="mt-1 accent-emerald-700" checked={isEnabled} onChange={() => toggleLayer(layer.id)} />
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold text-slate-800">{layer.title}</span>
          <span className="mt-1 inline-flex rounded-full bg-stone-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-stone-600">solo consultazione</span>
          <span className="ml-2 text-xs text-slate-500">Fonte: {layer.source === "ras_sitr" ? "Regione Sardegna" : "Agenzia delle Entrate"}</span>
        </span>
      </label>
      {isEnabled ? (
        <>
          <label className="mt-2 block text-xs font-medium text-slate-600">
            Opacita {Math.round(layerOpacity * 100)}%
            <input aria-label={`Opacita ${layer.title}`} className="mt-1 w-full accent-emerald-700" type="range" min="0" max="1" step="0.05" value={layerOpacity} onChange={(event) => setLayerOpacity(layer.id, Number(event.target.value))} />
          </label>
          {legendUrls[layer.id] ? <Image className="mt-2 h-auto max-h-16 max-w-full" src={legendUrls[layer.id]} alt={`Legenda ${layer.title}`} width={240} height={64} unoptimized /> : null}
        </>
      ) : null}
      {layerErrors[layer.id] ? <p role="alert" className="mt-2 rounded-md bg-amber-50 p-2 text-xs text-amber-900">Sorgente momentaneamente non disponibile: {layerErrors[layer.id]}</p> : null}
    </article>
  );
}

type ThemeSectionProps = Pick<
  TerritorioLayerState,
  "enabled" | "opacity" | "layerErrors" | "legendUrls" | "toggleLayer" | "setLayerOpacity"
> & {
  group: GisTerritorioLayerGroup;
};

function isFireLayer(layer: GisTerritorioLayer): boolean {
  return layer.name.startsWith("ras_aree_incendiate_");
}

function TerritorioThemeSection({ group, ...layerState }: ThemeSectionProps) {
  const fireLayers = group.theme === "eventi" ? group.layers.filter(isFireLayer) : [];
  const listedLayers = group.layers.filter(
    (layer) => !isFireLayer(layer) || Boolean(layerState.enabled[layer.id]),
  );

  return (
    <section aria-label={group.label} className="rounded-xl border border-stone-200 bg-white p-3">
      <h3 className="text-sm font-bold text-slate-900">{group.label}</h3>
      {fireLayers.length ? (
        <IncendiAnnualiSelector
          layers={fireLayers}
          enabled={layerState.enabled}
          onToggle={layerState.toggleLayer}
        />
      ) : null}
      {listedLayers.length ? (
        <div className="mt-2 space-y-3">
          {listedLayers.map((layer) => (
            <TerritorioLayerItem key={layer.id} layer={layer} {...layerState} />
          ))}
        </div>
      ) : null}
    </section>
  );
}

export default function TerritorioLayerPanel({
  groups,
  loading,
  catalogError,
  catalogDisabled,
  enabled,
  opacity,
  layerErrors,
  legendUrls,
  toggleLayer,
  setLayerOpacity,
  basemap,
}: TerritorioLayerPanelProps) {
  const [open, setOpen] = useState(false);
  const ortofoto = groups.find((group) => group.theme === "ortofoto")?.layers ?? [];
  const activeAttributions = groups
    .flatMap((group) => group.layers)
    .filter((layer) => enabled[layer.id])
    .map((layer) => layer.attribution)
    .filter((value, index, values) => values.indexOf(value) === index);

  return (
    <aside className="absolute left-3 top-3 z-20 w-[min(23rem,calc(100%-1.5rem))] font-sans">
      <button
        type="button"
        aria-expanded={open}
        className="flex w-full items-center justify-between rounded-xl border border-emerald-900/15 bg-[#f7f3e8]/95 px-4 py-3 text-left shadow-lg backdrop-blur"
        onClick={() => setOpen((value) => !value)}
      >
        <span>
          <span className="block text-xs font-bold uppercase tracking-[0.18em] text-emerald-800">Territorio</span>
          <span className="text-sm font-semibold text-slate-900">Strati pubblici di consultazione</span>
        </span>
        <span aria-hidden="true" className="text-lg text-emerald-900">{open ? "−" : "+"}</span>
      </button>

      {open ? (
        <div className="mt-2 max-h-[70vh] space-y-3 overflow-y-auto rounded-2xl border border-emerald-900/10 bg-[#fffdf6]/95 p-3 shadow-xl backdrop-blur">
          {loading ? <p className="p-2 text-sm text-slate-600">Caricamento strati...</p> : null}
          {catalogError ? (
            <p
              role={catalogDisabled ? "status" : "alert"}
              className={`rounded-lg p-3 text-sm ${catalogDisabled ? "bg-stone-100 text-stone-700" : "bg-red-50 text-red-800"}`}
            >
              {catalogError}
            </p>
          ) : null}
          <OrtofotoStoricheSelector
            layers={ortofoto}
            enabled={enabled}
            opacity={opacity}
            basemap={basemap}
            onToggle={toggleLayer}
            onOpacityChange={setLayerOpacity}
          />
          {groups.filter((group) => group.theme !== "ortofoto").map((group) => (
            <TerritorioThemeSection
              key={group.theme}
              group={group}
              enabled={enabled}
              opacity={opacity}
              layerErrors={layerErrors}
              legendUrls={legendUrls}
              toggleLayer={toggleLayer}
              setLayerOpacity={setLayerOpacity}
            />
          ))}
          {activeAttributions.length ? (
            <footer aria-label="Attribuzioni strati attivi" className="rounded-xl bg-slate-900 p-3 text-[11px] leading-5 text-slate-100">
              {activeAttributions.map((attribution) => <p key={attribution}>{attribution}</p>)}
            </footer>
          ) : null}
        </div>
      ) : null}
    </aside>
  );
}
