"use client";

import { useEffect, useState } from "react";

import { formatMeasurement, geodesicArea, geodesicDistance, type GeoPoint } from "./geodesic-measurements";
import type { MeasurementMode } from "./DrawingTools";

const SOURCE_ID = "territorio-measure-source";
const LINE_ID = "territorio-measure-line";
const FILL_ID = "territorio-measure-fill";

type MapClick = { lngLat: { lng: number; lat: number }; preventDefault?: () => void };
type GeoJsonSource = { setData: (data: object) => void };
export type MeasurementMap = {
  on: (event: "click" | "dblclick", listener: (event: MapClick) => void) => void;
  off: (event: "click" | "dblclick", listener: (event: MapClick) => void) => void;
  addSource: (id: string, source: object) => void;
  getSource: (id: string) => unknown;
  removeSource: (id: string) => void;
  addLayer: (layer: object) => void;
  getLayer: (id: string) => unknown;
  removeLayer: (id: string) => void;
};

function feature(points: GeoPoint[], mode: Exclude<MeasurementMode, null>) {
  const coordinates = points.map((point) => [point.lon, point.lat]);
  const geometry = mode === "area" && points.length >= 3
    ? { type: "Polygon", coordinates: [[...coordinates, coordinates[0]]] }
    : { type: "LineString", coordinates };
  return { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry }] };
}

function removeOverlay(map: MeasurementMap) {
  if (map.getLayer(FILL_ID)) map.removeLayer(FILL_ID);
  if (map.getLayer(LINE_ID)) map.removeLayer(LINE_ID);
  if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
}

export function useTerritorioMeasurement(map: MeasurementMap | null) {
  const [mode, setMode] = useState<MeasurementMode>(null);
  const [points, setPoints] = useState<GeoPoint[]>([]);
  const [finished, setFinished] = useState(false);

  useEffect(() => {
    if (!map || !mode || finished) return;
    map.addSource(SOURCE_ID, { type: "geojson", data: feature([], mode) });
    map.addLayer({ id: LINE_ID, type: "line", source: SOURCE_ID, paint: { "line-color": "#b45309", "line-width": 3 } });
    map.addLayer({ id: FILL_ID, type: "fill", source: SOURCE_ID, paint: { "fill-color": "#f59e0b", "fill-opacity": 0.2 }, filter: ["==", "$type", "Polygon"] });
    const click = (event: MapClick) => setPoints((current) => [...current, { lon: event.lngLat.lng, lat: event.lngLat.lat }]);
    const finish = (event: MapClick) => { event.preventDefault?.(); setFinished(true); };
    map.on("click", click);
    map.on("dblclick", finish);
    return () => { map.off("click", click); map.off("dblclick", finish); };
  }, [finished, map, mode]);

  useEffect(() => {
    if (!map || !mode) return;
    (map.getSource(SOURCE_ID) as GeoJsonSource | undefined)?.setData(feature(points, mode));
  }, [map, mode, points]);

  useEffect(() => () => { if (map) removeOverlay(map); }, [map]);

  const value = mode === "area" ? geodesicArea(points) : geodesicDistance(points);
  return {
    mode,
    result: points.length > (mode === "area" ? 2 : 1) && mode ? formatMeasurement(value, mode) : null,
    setMode: (next: Exclude<MeasurementMode, null>) => { if (map) removeOverlay(map); setPoints([]); setFinished(false); setMode(next); },
    clear: () => { if (map) removeOverlay(map); setPoints([]); setFinished(false); setMode(null); },
  };
}
