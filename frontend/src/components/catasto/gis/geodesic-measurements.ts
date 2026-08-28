export type GeoPoint = { lon: number; lat: number };

const EARTH_RADIUS_M = 6_371_008.8;
const toRadians = (degrees: number) => degrees * Math.PI / 180;

export function geodesicDistance(points: GeoPoint[]): number {
  let distance = 0;
  for (let index = 1; index < points.length; index += 1) {
    const previous = points[index - 1];
    const current = points[index];
    const deltaLat = toRadians(current.lat - previous.lat);
    const deltaLon = toRadians(current.lon - previous.lon);
    const a = Math.sin(deltaLat / 2) ** 2
      + Math.cos(toRadians(previous.lat)) * Math.cos(toRadians(current.lat))
      * Math.sin(deltaLon / 2) ** 2;
    distance += 2 * EARTH_RADIUS_M * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }
  return distance;
}

export function geodesicArea(points: GeoPoint[]): number {
  if (points.length < 3) return 0;
  let sum = 0;
  for (let index = 0; index < points.length; index += 1) {
    const current = points[index];
    const next = points[(index + 1) % points.length];
    sum += toRadians(next.lon - current.lon)
      * (2 + Math.sin(toRadians(current.lat)) + Math.sin(toRadians(next.lat)));
  }
  return Math.abs(sum * EARTH_RADIUS_M ** 2 / 2);
}

export function formatMeasurement(value: number, kind: "distance" | "area"): string {
  if (kind === "distance") {
    return value >= 1000 ? `${(value / 1000).toFixed(2)} km` : `${value.toFixed(1)} m`;
  }
  return value >= 10_000 ? `${(value / 10_000).toFixed(2)} ha` : `${value.toFixed(1)} m2`;
}
