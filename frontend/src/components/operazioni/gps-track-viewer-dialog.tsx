"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";

type GpsPoint = {
  latitude: number;
  longitude: number;
  timestamp?: string | null;
};

type GpsBounds = {
  min_latitude: number | null;
  max_latitude: number | null;
  min_longitude: number | null;
  max_longitude: number | null;
};

type GpsSummary = {
  provider_name?: string | null;
  provider_track_id?: string | null;
  source_type?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  total_distance_km?: number | null;
  total_duration_seconds?: number | null;
};

type OperazioniGpsTrackViewerDialogProps = {
  open: boolean;
  title: string;
  points: GpsPoint[];
  bounds: GpsBounds | null;
  summary: GpsSummary | null;
  viewerMode: string | null;
  usesRawPayload: boolean;
  onClose: () => void;
};

const MAP_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    },
  },
  layers: [
    {
      id: "osm",
      type: "raster",
      source: "osm",
    },
  ],
};

function formatCoordinate(value: number | null | undefined) {
  if (value == null) {
    return "—";
  }
  return value.toFixed(6);
}

function createMarkerElement(toneClass: string) {
  const element = document.createElement("div");
  element.className = `gps-map-marker ${toneClass}`;
  return element;
}

export function OperazioniGpsTrackViewerDialog({
  open,
  title,
  points,
  bounds,
  summary,
  viewerMode,
  usesRawPayload,
  onClose,
}: OperazioniGpsTrackViewerDialogProps) {
  const mapRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open || !mapRef.current || points.length === 0) {
      return;
    }

    const map = new maplibregl.Map({
      container: mapRef.current,
      style: MAP_STYLE,
      attributionControl: true,
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: true, showZoom: true }), "top-right");

    const coordinates = points.map((point) => [point.longitude, point.latitude] as [number, number]);

    map.on("load", () => {
      map.addSource("activity-track", {
        type: "geojson",
        data: {
          type: "Feature",
          geometry:
            coordinates.length > 1
              ? {
                  type: "LineString",
                  coordinates,
                }
              : {
                  type: "Point",
                  coordinates: coordinates[0],
                },
          properties: {},
        },
      });

      if (coordinates.length > 1) {
        map.addLayer({
          id: "activity-track-line",
          type: "line",
          source: "activity-track",
          paint: {
            "line-color": "#1D4E35",
            "line-width": 5,
            "line-opacity": 0.88,
          },
          layout: {
            "line-cap": "round",
            "line-join": "round",
          },
        });
      }

      new maplibregl.Marker({ element: createMarkerElement("gps-map-marker-start") })
        .setLngLat(coordinates[0])
        .addTo(map);

      if (coordinates.length > 1) {
        new maplibregl.Marker({ element: createMarkerElement("gps-map-marker-end") })
          .setLngLat(coordinates[coordinates.length - 1])
          .addTo(map);
      }

      if (coordinates.length === 1) {
        map.easeTo({ center: coordinates[0], zoom: 14 });
        return;
      }

      const mapBounds = new maplibregl.LngLatBounds(coordinates[0], coordinates[0]);
      for (const coordinate of coordinates.slice(1)) {
        mapBounds.extend(coordinate);
      }
      map.fitBounds(mapBounds, { padding: 56, maxZoom: 15, duration: 0 });
    });

    return () => {
      map.remove();
    };
  }, [open, points]);

  if (!open) {
    return null;
  }

  const startPoint = points[0] ?? null;
  const endPoint = points.at(-1) ?? null;
  const samplePoints =
    points.length <= 12 ? points : [...points.slice(0, 6), ...points.slice(Math.max(points.length - 6, 6))];

  return (
    <div className="fixed inset-0 z-[125] flex items-center justify-center bg-black/55 p-4" role="dialog" aria-modal="true">
      <div className="flex h-[88vh] w-full max-w-6xl flex-col overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-2xl">
        <div className="flex items-center justify-between gap-4 border-b border-[#edf1eb] px-6 py-4">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#667267]">Viewer GPS</p>
            <p className="mt-1 truncate text-sm font-semibold text-gray-900">{title}</p>
          </div>
          <button type="button" className="btn-secondary" onClick={onClose}>
            Chiudi
          </button>
        </div>

        <div className="grid min-h-0 flex-1 gap-0 lg:grid-cols-[minmax(0,1.8fr)_22rem]">
          <div className="min-h-0 border-b border-[#edf1eb] bg-[radial-gradient(circle_at_top,_rgba(212,229,219,0.6),_transparent_52%),linear-gradient(180deg,_#f7faf7,_#eef4ef)] p-4 lg:border-b-0 lg:border-r">
            <div className="relative flex h-full min-h-[24rem] items-center justify-center overflow-hidden rounded-[24px] border border-[#d9dfd6] bg-white shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]">
              {points.length >= 1 ? (
                <div ref={mapRef} className="h-full min-h-[24rem] w-full" />
              ) : (
                <div className="max-w-md px-6 text-center">
                  <p className="text-sm font-semibold text-gray-900">Traccia non disponibile</p>
                  <p className="mt-2 text-sm text-gray-500">
                    Il provider non ha restituito abbastanza coordinate per aprire la mappa dell&apos;attività.
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="min-h-0 overflow-auto bg-[#fbfcfa] p-5">
            <div className="space-y-4">
              <div className="rounded-[24px] border border-[#e6ebe5] bg-white p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Modalità</p>
                <p className="mt-2 text-sm font-semibold text-gray-900">
                  {viewerMode === "track" ? "Traccia completa" : "Segmento sintetico"}
                </p>
                <p className="mt-2 text-sm text-gray-600">
                  {usesRawPayload
                    ? "La mappa usa i punti estratti dal payload GPS grezzo."
                    : "La mappa usa start/end dal summary perché il payload non espone la polilinea completa."}
                </p>
              </div>

              <div className="rounded-[24px] border border-[#e6ebe5] bg-white p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Metriche</p>
                <div className="mt-3 space-y-3 text-sm text-gray-700">
                  <div className="flex items-center justify-between gap-4">
                    <span>Punti disponibili</span>
                    <span className="font-semibold text-gray-900">{points.length}</span>
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <span>Distanza</span>
                    <span className="font-semibold text-gray-900">
                      {summary?.total_distance_km != null ? `${summary.total_distance_km} km` : "—"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <span>Durata</span>
                    <span className="font-semibold text-gray-900">
                      {summary?.total_duration_seconds != null ? `${summary.total_duration_seconds} sec` : "—"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <span>Provider</span>
                    <span className="truncate font-semibold text-gray-900">{summary?.provider_name ?? "—"}</span>
                  </div>
                </div>
              </div>

              <div className="rounded-[24px] border border-[#e6ebe5] bg-white p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Coordinate</p>
                <div className="mt-3 space-y-3 text-sm text-gray-700">
                  <div>
                    <p className="font-semibold text-gray-900">Start</p>
                    <p className="mt-1">
                      {formatCoordinate(startPoint?.latitude)} / {formatCoordinate(startPoint?.longitude)}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">
                      {startPoint?.timestamp ? new Date(startPoint.timestamp).toLocaleString("it-IT") : "Timestamp non disponibile"}
                    </p>
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900">End</p>
                    <p className="mt-1">
                      {formatCoordinate(endPoint?.latitude)} / {formatCoordinate(endPoint?.longitude)}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">
                      {endPoint?.timestamp ? new Date(endPoint.timestamp).toLocaleString("it-IT") : "Timestamp non disponibile"}
                    </p>
                  </div>
                </div>
              </div>

              <div className="rounded-[24px] border border-[#e6ebe5] bg-white p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Timeline punti</p>
                <div className="mt-3 space-y-3">
                  {samplePoints.length > 0 ? (
                    samplePoints.map((point, index) => (
                      <div key={`${point.latitude}-${point.longitude}-${point.timestamp ?? index}`} className="rounded-xl border border-[#edf1eb] bg-[#fcfdfb] px-3 py-3 text-sm text-gray-700">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-semibold text-gray-900">Punto {index + 1}</p>
                            <p className="mt-1">
                              {formatCoordinate(point.latitude)} / {formatCoordinate(point.longitude)}
                            </p>
                          </div>
                          <span className="rounded-full bg-[#eef4ef] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[#4f6a55]">
                            {index === 0 ? "Start" : index === samplePoints.length - 1 ? "End" : "Track"}
                          </span>
                        </div>
                        <p className="mt-2 text-xs text-gray-500">
                          {point.timestamp ? new Date(point.timestamp).toLocaleString("it-IT") : "Timestamp non disponibile"}
                        </p>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-gray-500">Nessun punto disponibile nel viewer GPS.</p>
                  )}
                  {points.length > samplePoints.length ? (
                    <p className="text-xs text-gray-500">
                      Timeline campionata: {samplePoints.length} punti mostrati su {points.length} disponibili.
                    </p>
                  ) : null}
                </div>
              </div>

              <div className="rounded-[24px] border border-[#e6ebe5] bg-white p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Bounds</p>
                <div className="mt-3 grid gap-3 text-sm text-gray-700 sm:grid-cols-2">
                  <div>
                    <p className="text-xs uppercase tracking-[0.12em] text-gray-500">Lat min</p>
                    <p className="mt-1 font-semibold text-gray-900">{formatCoordinate(bounds?.min_latitude)}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.12em] text-gray-500">Lat max</p>
                    <p className="mt-1 font-semibold text-gray-900">{formatCoordinate(bounds?.max_latitude)}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.12em] text-gray-500">Lon min</p>
                    <p className="mt-1 font-semibold text-gray-900">{formatCoordinate(bounds?.min_longitude)}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.12em] text-gray-500">Lon max</p>
                    <p className="mt-1 font-semibold text-gray-900">{formatCoordinate(bounds?.max_longitude)}</p>
                  </div>
                </div>
              </div>

              <div className="rounded-[24px] border border-[#e6ebe5] bg-white p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Origine dato</p>
                <div className="mt-3 space-y-3 text-sm text-gray-700">
                  <div className="flex items-center justify-between gap-4">
                    <span>Source type</span>
                    <span className="font-semibold text-gray-900">{summary?.source_type ?? "—"}</span>
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <span>Track ID</span>
                    <span className="truncate font-semibold text-gray-900">{summary?.provider_track_id ?? "—"}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
