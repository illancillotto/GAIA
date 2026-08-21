import type { GisMapOverlayLayer, GisSearchResponse } from "@/types/gis";

export type ParsedGisCoordinate = {
  lat: number;
  lon: number;
  source: "decimal" | "dms";
};

const DECIMAL_NUMBER_PATTERN = /[+-]?\d+(?:[.,]\d+)?/g;
const LEADING_DIRECTION_DMS_PATTERN =
  /([NSEW])\s*([+-]?\d+(?:[.,]\d+)?)\s*(?:°|d|deg)?\s*(?:(\d+(?:[.,]\d+)?)\s*(?:'|′|m|min)?)?\s*(?:(\d+(?:[.,]\d+)?)\s*(?:"|″|s|sec)?)?/gi;
const TRAILING_DIRECTION_DMS_PATTERN =
  /([+-]?\d+(?:[.,]\d+)?)\s*(?:°|d|deg)?\s*(?:(\d+(?:[.,]\d+)?)\s*(?:'|′|m|min)?)?\s*(?:(\d+(?:[.,]\d+)?)\s*(?:"|″|s|sec)?)?\s*([NSEW])/gi;
const SIGNED_DMS_PATTERN =
  /([+-]?\d+(?:[.,]\d+)?)\s*°\s*(?:(\d+(?:[.,]\d+)?)\s*(?:'|′)?)?\s*(?:(\d+(?:[.,]\d+)?)\s*(?:"|″)?)?/g;
const METERS_PER_DEGREE_LATITUDE = 111_320;
const COORDINATE_WAYPOINT_RADIUS_METERS = 90;

export function buildCatastoGisCoordinateOverlay(
  label: string,
  geojson: GeoJSON.FeatureCollection,
): { label: string; geojson: GeoJSON.FeatureCollection; layer: GisMapOverlayLayer } {
  return {
    label,
    geojson,
    layer: {
      layer_key: "coordinate-search",
      saved_selection_id: null,
      name: `Waypoint ${label}`,
      color: "#0F766E",
      outlineColor: "#F97316",
      opacity: 0.86,
      outlineOpacity: 1,
      outlineWidth: 3,
      showFill: true,
      showCentroids: true,
      visible: true,
      source_filename: null,
      geojson,
    },
  };
}

function parseRequiredNumber(value: string): number {
  return Number(value.replace(",", "."));
}

function parseOptionalNumber(value: string | undefined): number | null {
  if (value === undefined) return null;
  return parseRequiredNumber(value);
}

function isValidLatitude(value: number): boolean {
  return value >= -90 && value <= 90;
}

function isValidLongitude(value: number): boolean {
  return value >= -180 && value <= 180;
}

function toCoordinate(lat: number, lon: number, source: ParsedGisCoordinate["source"]): ParsedGisCoordinate | null {
  if (!isValidLatitude(lat) || !isValidLongitude(lon)) return null;
  return { lat, lon, source };
}

function parseDecimalCoordinate(input: string): ParsedGisCoordinate | null {
  if (/[°'′"″]|\b[NSEW]\b/i.test(input)) return null;
  const leftover = input.replace(DECIMAL_NUMBER_PATTERN, "").replace(/[,\s;|/()]+/g, "");
  if (leftover) return null;
  const values = (input.match(DECIMAL_NUMBER_PATTERN) ?? []).map(parseRequiredNumber);
  if (values.length !== 2) return null;
  return toCoordinate(values[0], values[1], "decimal");
}

function dmsToDecimal(degrees: number, minutes: number | null, seconds: number | null, direction: string | null): number {
  const absolute = Math.abs(degrees) + (minutes ?? 0) / 60 + (seconds ?? 0) / 3600;
  const directionSign = direction && /[SW]/i.test(direction) ? -1 : 1;
  const sign = degrees < 0 ? -1 : directionSign;
  return absolute * sign;
}

function parseDmsValues(
  directionValue: string,
  degreesValue: string,
  minutesValue: string | undefined,
  secondsValue: string | undefined,
): { value: number; direction?: string } | null {
  const direction = directionValue.toUpperCase();
  const degrees = parseRequiredNumber(degreesValue);
  const minutes = parseOptionalNumber(minutesValue);
  const seconds = parseOptionalNumber(secondsValue);
  if ((minutes != null && (minutes < 0 || minutes >= 60)) || (seconds != null && (seconds < 0 || seconds >= 60))) return null;
  return { value: dmsToDecimal(degrees, minutes, seconds, direction), direction };
}

function parseDirectionalDms(input: string): ParsedGisCoordinate | null {
  const parts: Array<{ value: number; direction?: string }> = [];
  const hasLeadingDirections = /\b[NS]\s*[+-]?\d/i.test(input) && /\b[EW]\s*[+-]?\d/i.test(input);
  const pattern = hasLeadingDirections ? LEADING_DIRECTION_DMS_PATTERN : TRAILING_DIRECTION_DMS_PATTERN;
  for (const match of input.matchAll(pattern)) {
    const part = hasLeadingDirections
      ? parseDmsValues(match[1], match[2], match[3], match[4])
      : parseDmsValues(match[4], match[1], match[2], match[3]);
    if (part) parts.push(part);
  }
  if (parts.length !== 2) return null;

  const latPart = parts.find((part) => part.direction && /[NS]/.test(part.direction));
  const lonPart = parts.find((part) => part.direction && /[EW]/.test(part.direction));
  if (!latPart || !lonPart) return null;
  return toCoordinate(latPart.value, lonPart.value, "dms");
}

function parseSignedDms(input: string): ParsedGisCoordinate | null {
  const values: number[] = [];
  for (const match of input.matchAll(SIGNED_DMS_PATTERN)) {
    const degrees = parseRequiredNumber(match[1]);
    const minutes = parseOptionalNumber(match[2]);
    const seconds = parseOptionalNumber(match[3]);
    if ((minutes != null && (minutes < 0 || minutes >= 60)) || (seconds != null && (seconds < 0 || seconds >= 60))) return null;
    values.push(dmsToDecimal(degrees, minutes, seconds, null));
  }
  if (values.length !== 2) return null;
  return toCoordinate(values[0], values[1], "dms");
}

export function parseCatastoGisCoordinateSearch(input: string): ParsedGisCoordinate | null {
  const normalized = input.trim();
  if (!normalized) return null;
  const decimal = parseDecimalCoordinate(normalized);
  if (decimal) return decimal;
  if (/\b[NSEW]\b/i.test(normalized)) return parseDirectionalDms(normalized);
  return parseSignedDms(normalized);
}

export function formatCatastoGisCoordinateLabel(coordinate: ParsedGisCoordinate): string {
  return `${coordinate.lat.toFixed(6)}, ${coordinate.lon.toFixed(6)}`;
}

export function buildCatastoGisCoordinateHref(input: string): string | null {
  const coordinate = parseCatastoGisCoordinateSearch(input);
  if (!coordinate) return null;
  const params = new URLSearchParams({
    coordinate: formatCatastoGisCoordinateLabel(coordinate),
  });
  return `/catasto/gis/coordinate?${params.toString()}`;
}

export function buildCatastoGisCoordinateFeatureCollection(
  coordinate: ParsedGisCoordinate,
): GeoJSON.FeatureCollection<GeoJSON.Geometry> {
  const label = formatCatastoGisCoordinateLabel(coordinate);
  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: buildCoordinateWaypointGeometry(coordinate),
        properties: {
          id: "coordinate-search-waypoint",
          label,
          source: coordinate.source,
          role: "waypoint-halo",
        },
      },
      {
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [coordinate.lon, coordinate.lat],
        },
        properties: {
          id: "coordinate-search",
          label,
          source: coordinate.source,
          role: "waypoint-point",
        },
      },
    ],
  };
}

function buildCoordinateWaypointGeometry(coordinate: ParsedGisCoordinate): GeoJSON.Polygon {
  const latDelta = COORDINATE_WAYPOINT_RADIUS_METERS / METERS_PER_DEGREE_LATITUDE;
  const lonScale = Math.max(0.2, Math.cos((coordinate.lat * Math.PI) / 180));
  const lonDelta = COORDINATE_WAYPOINT_RADIUS_METERS / (METERS_PER_DEGREE_LATITUDE * lonScale);
  const ring: GeoJSON.Position[] = [
    [coordinate.lon, coordinate.lat + latDelta],
    [coordinate.lon + lonDelta, coordinate.lat],
    [coordinate.lon, coordinate.lat - latDelta],
    [coordinate.lon - lonDelta, coordinate.lat],
    [coordinate.lon, coordinate.lat + latDelta],
  ];
  return { type: "Polygon", coordinates: [ring] };
}

export function buildCatastoGisCoordinateSearchResponse(input: string): {
  geojson: GeoJSON.FeatureCollection<GeoJSON.Geometry>;
  label: string;
  response: GisSearchResponse;
} | null {
  const coordinate = parseCatastoGisCoordinateSearch(input);
  if (!coordinate) return null;
  const label = formatCatastoGisCoordinateLabel(coordinate);
  const geojson = buildCatastoGisCoordinateFeatureCollection(coordinate);
  return {
    geojson,
    label,
    response: {
      query: label,
      mode_requested: "auto",
      mode_resolved: "auto",
      total: 1,
      results: [],
      geojson,
    },
  };
}
