"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";

import { catastoGetDistrettoGeojson } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatDistretto, CatDistrettoKpi, GeoJSONFeature } from "@/types/catasto";
import type { GisFilters, GisMapOverlayLayer } from "@/types/gis";

const MapContainer = dynamic(
  /* v8 ignore next -- Next dynamic invokes the real loader in browser/runtime, while unit tests mock it. */
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

type DistrettoGisPreviewProps = {
  distretto: CatDistretto;
  kpi: CatDistrettoKpi | null;
};

function formatNumber(value: number): string {
  return new Intl.NumberFormat("it-IT").format(value);
}

function formatHaFromMq(value: string | number | null | undefined): string {
  const mq = typeof value === "number" ? value : Number(value ?? 0);
  return new Intl.NumberFormat("it-IT", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format((Number.isFinite(mq) ? mq : 0) / 10_000);
}

function toFeatureCollection(feature: GeoJSONFeature | null): GeoJSON.FeatureCollection | null {
  if (!feature?.geometry) return null;
  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: feature.geometry as GeoJSON.Geometry,
        properties: feature.properties,
      },
    ],
  };
}

function toGeometryFeatureCollection(
  geometry: GeoJSON.Geometry | null,
  properties: Record<string, unknown> = {},
): GeoJSON.FeatureCollection | null {
  if (!geometry) return null;
  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry,
        properties,
      },
    ],
  };
}

function geometryProperty(feature: GeoJSONFeature | null, property: string): GeoJSON.Geometry | null {
  const value = feature?.properties?.[property];
  if (!value || typeof value !== "object" || !("type" in value)) return null;
  return value as GeoJSON.Geometry;
}

function toFocusFeatureCollection(feature: GeoJSONFeature | null): GeoJSON.FeatureCollection | null {
  const districtCollection = toFeatureCollection(feature);
  const particelleBoundsGeometry = geometryProperty(feature, "particelle_bounds_geometry");
  if (!districtCollection || !particelleBoundsGeometry) return districtCollection;
  return {
    type: "FeatureCollection",
    features: [
      ...districtCollection.features,
      {
        type: "Feature",
        geometry: particelleBoundsGeometry,
        properties: { source: "particelle_bounds" },
      },
    ],
  };
}

export function DistrettoGisPreview({ distretto, kpi }: DistrettoGisPreviewProps) {
  const [districtGeojson, setDistrictGeojson] = useState<GeoJSON.FeatureCollection | null>(null);
  const [particellePreviewGeojson, setParticellePreviewGeojson] = useState<GeoJSON.FeatureCollection | null>(null);
  const [focusGeojson, setFocusGeojson] = useState<GeoJSON.FeatureCollection | null>(null);
  const [focusSignal, setFocusSignal] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;

    let cancelled = false;
    setError(null);

    catastoGetDistrettoGeojson(token, distretto.id)
      .then((feature) => {
        if (cancelled) return;
        const districtCollection = toFeatureCollection(feature);
        const previewCollection = toGeometryFeatureCollection(
          geometryProperty(feature, "particelle_preview_geometry"),
          { source: "particelle_preview" },
        );
        const focusCollection = toFocusFeatureCollection(feature);
        setDistrictGeojson(districtCollection);
        setParticellePreviewGeojson(previewCollection);
        setFocusGeojson(focusCollection);
        if (focusCollection) {
          setFocusSignal((value) => value + 1);
        }
      })
      .catch((loadError) => {
        if (cancelled) return;
        setDistrictGeojson(null);
        setParticellePreviewGeojson(null);
        setFocusGeojson(null);
        setError(loadError instanceof Error ? loadError.message : "Impossibile centrare il distretto sulla mappa");
      });

    return () => {
      cancelled = true;
    };
  }, [distretto.id]);

  const filters = useMemo<GisFilters>(
    () => ({
      num_distretto: distretto.num_distretto,
    }),
    [distretto.num_distretto],
  );
  const districtOverlayLayers = useMemo<GisMapOverlayLayer[]>(
    () => {
      const layers: GisMapOverlayLayer[] = [];
      if (particellePreviewGeojson) {
        layers.push({
          layer_key: `distretto-${distretto.id}-particelle-preview`,
          name: `Particelle distretto ${distretto.num_distretto}`,
          color: "#F97316",
          outlineColor: "#C2410C",
          opacity: 0.85,
          // Thin, muted outline: at the fitted zoom parcels are a few px wide and a
          // stronger border would swallow the fill, reading as unfilled polygons.
          outlineOpacity: 0.45,
          outlineWidth: 0.3,
          visible: true,
          showFill: true,
          showCentroids: false,
          pulse: false,
          geojson: particellePreviewGeojson,
        });
      }
      if (districtGeojson) {
        layers.push({
          layer_key: `distretto-${distretto.id}`,
          name: `Distretto ${distretto.num_distretto}`,
          color: "#FED7AA",
          outlineColor: "#7C2D12",
          opacity: 0.9,
          outlineWidth: 2.2,
          visible: true,
          showFill: false,
          showCentroids: false,
          pulse: false,
          geojson: districtGeojson,
        });
      }
      return layers;
    },
    [districtGeojson, distretto.id, distretto.num_distretto, particellePreviewGeojson],
  );

  return (
    <section className="overflow-hidden rounded-[1.75rem] border border-[#cfe8d8] bg-white shadow-[0_16px_45px_rgba(15,23,42,0.12)]">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 bg-[linear-gradient(135deg,#f4fbf6_0%,#ffffff_70%)] px-5 py-4">
        <div>
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-[#2d6b47]">Vista GIS read-only</p>
          <h3 className="mt-1 text-lg font-semibold text-slate-950">
            Particelle del distretto {distretto.num_distretto}
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            La mappa mostra solo il perimetro e le particelle del distretto. Le particelle non sono cliccabili.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1 font-semibold text-emerald-800">
            {formatNumber(kpi?.totale_particelle ?? 0)} particelle
          </span>
          <span className="rounded-full border border-slate-200 bg-white px-3 py-1 font-semibold text-slate-700">
            {formatHaFromMq(kpi?.superficie_irrigabile_mq)} ha
          </span>
        </div>
      </div>

      <div className="relative h-[430px] bg-slate-100">
        <MapContainer
          token={null}
          onGeometryDrawn={() => undefined}
          onSelectionCleared={() => undefined}
          selectedIds={[]}
          filters={filters}
          mapLayers={{
            showDistretti: true,
            showDistrettiFill: true,
            showParticelleFill: true,
            distretto: distretto.num_distretto,
            distrettiOpacity: 0.08,
            particelleOpacity: 0.96,
            particelleColorMode: "district_preview",
            showParticelleTiles: false,
            highlightSelected: false,
            showDeliveryPoints: false,
          }}
          overlayLayers={districtOverlayLayers}
          focusGeojson={focusGeojson}
          focusSignal={focusSignal}
          focusOptions={{ padding: 56, maxZoom: 11.8, duration: 450 }}
          drawSignal={0}
          clearSignal={0}
          basemap="osm"
          className="h-full min-h-[430px] rounded-none"
        />
        <div className="pointer-events-none absolute bottom-4 left-4 rounded-2xl border border-white/80 bg-white/90 px-4 py-3 text-xs text-slate-600 shadow-lg backdrop-blur">
          <span className="font-semibold text-slate-900">Solo consultazione</span>
          <span className="mx-2 text-slate-300">|</span>
          zoom e pan attivi, selezione disabilitata
        </div>
      </div>

      {error ? (
        <div className="border-t border-amber-100 bg-amber-50 px-5 py-3 text-sm text-amber-800">
          {error}. La mappa resta disponibile, ma potrebbe aprirsi sul perimetro generale.
        </div>
      ) : null}
    </section>
  );
}
