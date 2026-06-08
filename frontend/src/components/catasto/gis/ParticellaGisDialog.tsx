"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";

import { getStoredAccessToken } from "@/lib/auth";
import type { CatAnagraficaMatch, GeoJSONFeature } from "@/types/catasto";
import type { GisMapOverlayLayer } from "@/types/gis";

const MapContainer = dynamic(() => import("@/components/catasto/gis/MapContainer"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[560px] items-center justify-center rounded-2xl bg-gray-100 text-sm text-gray-500">
      Caricamento GIS...
    </div>
  ),
});

function formatCoordinate(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return value.toLocaleString("it-IT", { minimumFractionDigits: 6, maximumFractionDigits: 6 });
}

export function ParticellaGisDialog({
  open,
  match,
  geojson,
  centroid,
  onClose,
}: {
  open: boolean;
  match: CatAnagraficaMatch | null;
  geojson: GeoJSONFeature | null;
  centroid: { lon: number; lat: number } | null;
  onClose: () => void;
}) {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setToken(getStoredAccessToken());
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, open]);

  const featureCollection = useMemo<GeoJSON.FeatureCollection | null>(() => {
    if (!open || !geojson?.geometry || !match) return null;
    return {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: geojson.geometry as GeoJSON.Geometry,
          properties: {
            ...(geojson.properties ?? {}),
            id: match.particella_id,
          },
        },
      ],
    };
  }, [geojson, match, open]);

  const overlayLayers = useMemo<GisMapOverlayLayer[]>(
    () =>
      featureCollection
        ? [
            {
              layer_key: `particella-${match?.particella_id ?? "current"}`,
              name: "Particella selezionata",
              color: "#1D4E35",
              outlineColor: "#0F3B28",
              opacity: 0.8,
              showFill: true,
              visible: true,
              geojson: featureCollection,
            },
          ]
        : [],
    [featureCollection, match?.particella_id],
  );

  if (!open || !match) return null;

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-black/55 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={`GIS ${match.foglio}/${match.particella}`}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="flex h-[88vh] w-full max-w-6xl flex-col overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-2xl">
        <div className="border-b border-gray-200 px-6 py-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#52715d]">GIS particella</p>
              <h2 className="mt-1 text-xl font-semibold text-gray-900">
                Fg.{match.foglio} Part.{match.particella}
                {match.subalterno ? ` Sub.${match.subalterno}` : ""}
              </h2>
              <p className="mt-1 text-sm text-gray-500">
                {match.comune ?? "Comune n/d"} · Distretto {match.num_distretto ?? "—"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <a
                className="btn-secondary"
                href={centroid ? `https://www.openstreetmap.org/?mlat=${centroid.lat}&mlon=${centroid.lon}#map=18/${centroid.lat}/${centroid.lon}` : "#"}
                target="_blank"
                rel="noreferrer"
                aria-disabled={!centroid}
                onClick={(event) => {
                  if (!centroid) event.preventDefault();
                }}
              >
                Apri su OSM
              </a>
              <button type="button" className="btn-secondary" onClick={onClose}>
                Chiudi
              </button>
            </div>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-2xl border border-[#d9e7dc] bg-[#f5faf5] px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#52715d]">Latitudine</p>
              <p className="mt-1 text-sm font-medium text-gray-900">{formatCoordinate(centroid?.lat)}</p>
            </div>
            <div className="rounded-2xl border border-[#d9e7dc] bg-[#f5faf5] px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#52715d]">Longitudine</p>
              <p className="mt-1 text-sm font-medium text-gray-900">{formatCoordinate(centroid?.lon)}</p>
            </div>
            <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-500">Tipo geometria</p>
              <p className="mt-1 text-sm font-medium text-gray-900">
                {typeof geojson?.properties?.["geometry_type"] === "string" ? String(geojson.properties["geometry_type"]) : "—"}
              </p>
            </div>
            <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-500">GeoJSON</p>
              <p className="mt-1 text-sm font-medium text-gray-900">{featureCollection ? "Disponibile" : "Assente"}</p>
            </div>
          </div>
        </div>

        <div className="min-h-0 flex-1 p-4">
          <MapContainer
            token={token}
            onGeometryDrawn={() => undefined}
            onSelectionCleared={() => undefined}
            selectedIds={match.particella_id ? [match.particella_id] : []}
            filters={{}}
            drawSignal={0}
            clearSignal={0}
            basemap="satellite"
            mapLayers={{
              showDistretti: true,
              showDistrettiFill: false,
              showParticelleFill: false,
              particelleOpacity: 0.25,
              highlightSelected: true,
            }}
            overlayLayers={overlayLayers}
            focusGeojson={featureCollection}
            focusSignal={featureCollection ? 1 : 0}
            focusOptions={{ maxZoom: 18, padding: 48, duration: 0 }}
            className="border border-gray-200"
          />
        </div>
      </div>
    </div>
  );
}
