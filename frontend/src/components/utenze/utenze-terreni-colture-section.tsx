"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceMiniStat,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { DocumentIcon, GridIcon } from "@/components/ui/icons";
import { getSubjectLandCrops } from "@/lib/ruolo-api";
import type { RuoloSubjectLandCropsResponse } from "@/types/ruolo";
import type { GisFilters, GisMapOverlayLayer } from "@/types/gis";

const MapContainer = dynamic(
  /* v8 ignore next -- Next dynamic invokes the real loader in browser/runtime; unit tests mock this boundary. */
  () => import("@/components/catasto/gis/MapContainer"),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full min-h-[420px] items-center justify-center rounded-[1.5rem] bg-slate-100 text-sm text-slate-500">
        Caricamento vista GIS...
      </div>
    ),
  },
);

type Props = {
  subjectId: string;
  token: string;
};

const CROP_LAYER_COLORS = ["#15803D", "#D97706", "#2563EB", "#BE123C", "#7C3AED", "#0F766E", "#A16207", "#4338CA"];

export function formatLandCropArea(value: number | null | undefined): string {
  if (value == null) return "-";
  return `${new Intl.NumberFormat("it-IT", { maximumFractionDigits: 2 }).format(value)} ha`;
}

export function formatLandCropEuro(value: number | null | undefined): string {
  if (value == null) return "-";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 2 }).format(value);
}

export function cropFeatureLabel(feature: GeoJSON.Feature): string {
  const value = feature.properties?.coltura;
  return typeof value === "string" && value.trim() ? value.trim() : "Coltura non indicata";
}

export function buildCropOverlayLayers(collection: GeoJSON.FeatureCollection | null | undefined): GisMapOverlayLayer[] {
  if (!collection?.features?.length) return [];
  const byCrop = new Map<string, GeoJSON.Feature[]>();
  for (const feature of collection.features) {
    if (!feature.geometry) continue;
    const crop = cropFeatureLabel(feature);
    byCrop.set(crop, [...(byCrop.get(crop) ?? []), feature]);
  }
  return Array.from(byCrop.entries()).map(([crop, features], index) => {
    const color = CROP_LAYER_COLORS[index % CROP_LAYER_COLORS.length];
    return {
      layer_key: `utenze-terreni-${index}-${crop.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`,
      name: crop,
      color,
      outlineColor: color,
      opacity: 0.7,
      outlineOpacity: 0.95,
      outlineWidth: 1.1,
      visible: true,
      showFill: true,
      showCentroids: true,
      featureClickMode: "overlay",
      geojson: { type: "FeatureCollection", features },
    };
  });
}

function isModuleAccessError(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error);
  return message.includes("403") || message.includes("Module access");
}

function safeErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Errore caricamento terreni e colture a ruolo";
}

export function UtenzeTerreniColtureSection({ subjectId, token }: Props) {
  const [summary, setSummary] = useState<RuoloSubjectLandCropsResponse | null>(null);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [roleAccessMissing, setRoleAccessMissing] = useState(false);
  const [mapSummary, setMapSummary] = useState<RuoloSubjectLandCropsResponse | null>(null);
  const [mapLoading, setMapLoading] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const [focusSignal, setFocusSignal] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setRoleAccessMissing(false);
    setMapSummary(null);
    setMapError(null);

    getSubjectLandCrops(token, subjectId, {
      anno: selectedYear ?? undefined,
      include_geojson: false,
      particelle_limit: 160,
    })
      .then((response) => {
        if (cancelled) return;
        setSummary(response);
      })
      .catch((loadError: unknown) => {
        if (cancelled) return;
        if (isModuleAccessError(loadError)) {
          setRoleAccessMissing(true);
          setSummary(null);
          return;
        }
        setError(safeErrorMessage(loadError));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedYear, subjectId, token]);

  async function handleOpenMap() {
    if (!summary?.anno_riferimento) return;
    setMapLoading(true);
    setMapError(null);
    try {
      const response = await getSubjectLandCrops(token, subjectId, {
        anno: summary.anno_riferimento,
        include_geojson: true,
        particelle_limit: 160,
        geojson_limit: 500,
      });
      setMapSummary(response);
      setFocusSignal((current) => current + 1);
    } catch (loadError) {
      setMapError(safeErrorMessage(loadError));
    } finally {
      setMapLoading(false);
    }
  }

  const overlayLayers = useMemo(() => buildCropOverlayLayers(mapSummary?.geojson), [mapSummary?.geojson]);
  const filters = useMemo<GisFilters>(() => ({}), []);
  const featureCount = mapSummary?.geojson?.features.length ?? 0;

  if (loading) {
    return (
      <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-panel">
        <p className="text-sm text-gray-500">Caricamento terreni e colture a ruolo...</p>
      </section>
    );
  }

  if (roleAccessMissing) {
    return (
      <section className="rounded-[28px] border border-amber-200 bg-amber-50 p-5 text-sm text-amber-800 shadow-panel">
        Il modulo Ruolo non e accessibile con l&apos;utente corrente: terreni e colture a ruolo non sono disponibili.
      </section>
    );
  }

  if (error) {
    return (
      <section className="rounded-[28px] border border-red-200 bg-red-50 p-5 text-sm text-red-700 shadow-panel">
        {error}
      </section>
    );
  }

  if (!summary || summary.totals.particelle_count === 0) {
    return (
      <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-panel">
        <p className="text-sm text-gray-500">Nessun terreno o coltura a ruolo collegato a questo soggetto.</p>
      </section>
    );
  }

  const totals = summary.totals;
  const latestCrop = summary.colture[0];

  return (
    <section className="space-y-4">
      <ModuleWorkspaceHero
        compact
        badge={
          <>
            <GridIcon className="h-3.5 w-3.5" />
            Terreni
          </>
        }
        title={summary.anno_riferimento ? `Terreni e colture a ruolo ${summary.anno_riferimento}` : "Terreni e colture a ruolo"}
        description="Quadro sintetico derivato dal ruolo: particelle, superfici irrigate, colture e localizzazione catastale collegata al soggetto. Non sostituisce una visura di proprieta aggiornata."
        actions={
          <>
            <ModuleWorkspaceNoticeCard compact title="Superficie irrigata" description={formatLandCropArea(totals.sup_irrigata_ha)} tone="success" />
            <ModuleWorkspaceNoticeCard compact title="Importo a ruolo" description={formatLandCropEuro(totals.importo_totale_euro)} tone="warning" />
          </>
        }
      >
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <ModuleWorkspaceMiniStat compact eyebrow="Particelle" value={totals.particelle_count} description={`${totals.comuni_count} comuni e ${totals.distretti_count} distretti coinvolti.`} />
          <ModuleWorkspaceMiniStat compact eyebrow="Colture" value={totals.colture_count} description={latestCrop ? `Prevalente: ${latestCrop.coltura}` : "Coltura non indicata"} tone="success" />
          <ModuleWorkspaceMiniStat compact eyebrow="Ettari irrigati" value={formatLandCropArea(totals.sup_irrigata_ha)} description={`Catastale: ${formatLandCropArea(totals.sup_catastale_ha)}`} tone="success" />
          <ModuleWorkspaceMiniStat compact eyebrow="Mapping GIS" value={`${totals.mapped_count}/${totals.particelle_count}`} description={totals.warning_count > 0 ? `${totals.warning_count} particelle da verificare` : "Collegamenti senza warning"} tone={totals.warning_count > 0 ? "warning" : "default"} />
        </div>
      </ModuleWorkspaceHero>

      {summary.available_years.length > 1 ? (
        <div className="flex flex-wrap gap-2 rounded-2xl border border-[#e6ebe5] bg-white p-3 shadow-sm">
          {summary.available_years.map((year) => (
            <button
              key={year}
              className={year === summary.anno_riferimento ? "rounded-xl bg-[#1D4E35] px-3 py-2 text-xs font-semibold text-white" : "rounded-xl bg-gray-100 px-3 py-2 text-xs font-semibold text-gray-700 transition hover:bg-gray-200"}
              type="button"
              onClick={() => setSelectedYear(year)}
            >
              {year}
            </button>
          ))}
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[1.1fr,0.9fr]">
        <article className="rounded-[24px] border border-[#e6ebe5] bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-gray-900">Colture principali</p>
              <p className="mt-1 text-xs text-gray-500">Superfici e importi aggregati dalle particelle a ruolo.</p>
            </div>
            <span className="rounded-full bg-[#eef3ec] px-3 py-1 text-xs font-semibold text-[#1D4E35]">{summary.colture.length} colture</span>
          </div>
          <div className="mt-4 space-y-3">
            {summary.colture.slice(0, 6).map((crop) => (
              <div key={crop.coltura} className="rounded-2xl border border-gray-100 bg-[linear-gradient(180deg,#ffffff,#fbfcfa)] px-4 py-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-gray-900">{crop.coltura}</p>
                    <p className="mt-1 text-xs text-gray-500">{crop.particelle_count} particelle · {crop.comune.join(", ")}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-gray-900">{formatLandCropArea(crop.sup_irrigata_ha)}</p>
                    <p className="mt-1 text-xs text-gray-500">{formatLandCropEuro(crop.importo_totale_euro)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="rounded-[24px] border border-[#e6ebe5] bg-white p-4 shadow-sm">
          <div>
            <p className="text-sm font-semibold text-gray-900">Dove sono i terreni</p>
            <p className="mt-1 text-xs text-gray-500">Breakdown sintetico per comune e distretto irriguo.</p>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-1">
            {summary.comuni.slice(0, 4).map((comune) => (
              <div key={comune.comune_nome} className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                <p className="text-sm font-semibold text-gray-900">{comune.comune_nome}</p>
                <p className="mt-1 text-xs text-gray-500">{formatLandCropArea(comune.sup_irrigata_ha)} · {comune.coltura.join(", ")}</p>
              </div>
            ))}
            {summary.distretti.slice(0, 4).map((distretto) => (
              <div key={distretto.distretto} className="rounded-2xl border border-emerald-100 bg-emerald-50/70 px-4 py-3">
                <p className="text-sm font-semibold text-emerald-900">Distretto {distretto.distretto}</p>
                <p className="mt-1 text-xs text-emerald-800">{distretto.particelle_count} particelle · {formatLandCropArea(distretto.sup_irrigata_ha)}</p>
              </div>
            ))}
          </div>
        </article>
      </div>

      <article className="rounded-[24px] border border-[#e6ebe5] bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-gray-900">Vista GIS terreni e colture</p>
            <p className="mt-1 text-xs text-gray-500">La mappa viene caricata solo su richiesta e colora le particelle per coltura.</p>
          </div>
          <button className="btn-primary" type="button" onClick={() => void handleOpenMap()} disabled={mapLoading}>
            {mapLoading ? "Caricamento mappa..." : mapSummary ? "Ricarica mappa" : "Apri mappa terreni"}
          </button>
        </div>

        {mapError ? <p className="mt-3 text-sm text-red-600">{mapError}</p> : null}
        {mapSummary ? (
          <div className="mt-4 overflow-hidden rounded-[1.5rem] border border-slate-200 bg-slate-100">
            <div className="flex flex-wrap gap-2 border-b border-slate-200 bg-white px-4 py-3 text-xs text-slate-600">
              <span className="font-semibold text-slate-900">{featureCount} geometrie caricate</span>
              {mapSummary.geojson_limited ? <span className="text-amber-700">Layer limitato per performance.</span> : null}
              {overlayLayers.map((layer) => (
                <span key={layer.layer_key} className="rounded-full border border-slate-200 bg-white px-2.5 py-1 font-semibold" style={{ color: layer.color }}>
                  {layer.name}
                </span>
              ))}
            </div>
            {featureCount > 0 ? (
              <div className="h-[430px]">
                <MapContainer
                  token={null}
                  onGeometryDrawn={() => undefined}
                  onSelectionCleared={() => undefined}
                  selectedIds={[]}
                  filters={filters}
                  mapLayers={{
                    showDistretti: true,
                    showDistrettiFill: false,
                    showParticelleFill: false,
                    showParticelleTiles: false,
                    highlightSelected: false,
                    showDeliveryPoints: false,
                  }}
                  overlayLayers={overlayLayers}
                  focusGeojson={mapSummary.geojson}
                  focusSignal={focusSignal}
                  focusOptions={{ padding: 56, maxZoom: 13, duration: 450 }}
                  drawSignal={0}
                  clearSignal={0}
                  basemap="osm"
                  className="h-full min-h-[430px] rounded-none"
                />
              </div>
            ) : (
              <div className="flex min-h-[180px] items-center justify-center px-4 py-8 text-center text-sm text-slate-500">
                Nessuna geometria GIS disponibile per le particelle collegate. Verificare i match catastali.
              </div>
            )}
          </div>
        ) : (
          <div className="mt-4 rounded-2xl border border-dashed border-[#d9dfd6] bg-[#fbfcfa] px-4 py-5 text-sm text-gray-600">
            Mappa non caricata. Usa il pulsante per recuperare solo ora le geometrie collegate al ruolo.
          </div>
        )}
      </article>

      <article className="rounded-[24px] border border-[#e6ebe5] bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <DocumentIcon className="h-4 w-4 text-[#1D4E35]" />
          <p className="text-sm font-semibold text-gray-900">Particelle a ruolo</p>
          <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs text-gray-600">
            prime {summary.particelle.length} di {totals.particelle_count}
          </span>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-[0.14em] text-gray-400">
              <tr>
                <th className="px-3 py-2">Comune</th>
                <th className="px-3 py-2">Fg/Part</th>
                <th className="px-3 py-2">Coltura</th>
                <th className="px-3 py-2">Ha irrigati</th>
                <th className="px-3 py-2">GIS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {summary.particelle.slice(0, 12).map((particella) => (
                <tr key={particella.id}>
                  <td className="px-3 py-2 text-gray-700">{particella.comune_nome}</td>
                  <td className="px-3 py-2 font-medium text-gray-900">
                    {particella.foglio}/{particella.particella}{particella.subalterno ? `/${particella.subalterno}` : ""}
                  </td>
                  <td className="px-3 py-2 text-gray-700">{particella.coltura ?? "Non indicata"}</td>
                  <td className="px-3 py-2 text-gray-700">{formatLandCropArea(particella.sup_irrigata_ha)}</td>
                  <td className="px-3 py-2">
                    <span className={particella.has_warning ? "rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-800" : "rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800"}>
                      {particella.is_mapped ? "Mappata" : "Da collegare"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  );
}
