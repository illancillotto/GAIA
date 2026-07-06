import type maplibregl from "maplibre-gl";

export type ParticelleQuickFilter = "all" | "ruolo" | "ruolo_inferito";
export type DeliveryPointQuickFilter = "all" | "with_meter" | "without_meter";

const BOOLEAN_TRUE_EXPRESSION: (property: string) => maplibregl.ExpressionSpecification = (property) => [
  "any",
  ["==", ["get", property], true],
  ["==", ["get", property], 1],
  ["==", ["get", property], "true"],
];

const BOOLEAN_FALSE_EXPRESSION: (property: string) => maplibregl.ExpressionSpecification = (property) => [
  "any",
  ["==", ["get", property], false],
  ["==", ["get", property], 0],
  ["==", ["get", property], "false"],
];

const STRING_PROPERTY_MISSING_EXPRESSION: (property: string) => maplibregl.ExpressionSpecification = (property) => [
  "==",
  ["coalesce", ["to-string", ["get", property]], ""],
  "",
];

export const PARTICELLA_INCOMPLETE_KEY_EXPRESSION: maplibregl.ExpressionSpecification = [
  "any",
  STRING_PROPERTY_MISSING_EXPRESSION("codice_catastale"),
  STRING_PROPERTY_MISSING_EXPRESSION("foglio"),
  STRING_PROPERTY_MISSING_EXPRESSION("particella"),
];

export function buildParticelleFilter(
  distretto: string | null,
  quickFilter: ParticelleQuickFilter,
): maplibregl.FilterSpecification | null {
  const clauses: maplibregl.ExpressionSpecification[] = [];
  if (distretto) {
    clauses.push(["==", ["get", "num_distretto"], distretto]);
  }
  if (quickFilter === "ruolo") {
    clauses.push(BOOLEAN_TRUE_EXPRESSION("ha_ruolo"));
  } else if (quickFilter === "ruolo_inferito") {
    clauses.push(BOOLEAN_TRUE_EXPRESSION("ha_ruolo_inferito"));
  }

  if (clauses.length === 0) return null;
  if (clauses.length === 1) return clauses[0] as maplibregl.FilterSpecification;
  return ["all", ...clauses] as maplibregl.FilterSpecification;
}

export function buildDeliveryPointFilter(
  distretto: string | null,
): maplibregl.FilterSpecification | null {
  if (!distretto) return null;
  return ["==", ["get", "distretto_code"], distretto];
}

export function buildMeterVisibilityFilter(
  distretto: string | null,
  hasMeter: boolean,
): maplibregl.FilterSpecification {
  const meterClause = hasMeter ? BOOLEAN_TRUE_EXPRESSION("has_meter") : BOOLEAN_FALSE_EXPRESSION("has_meter");
  const distrettoClause = buildDeliveryPointFilter(distretto);
  if (!distrettoClause) return meterClause as maplibregl.FilterSpecification;
  return ["all", distrettoClause as maplibregl.ExpressionSpecification, meterClause] as maplibregl.FilterSpecification;
}

export function shouldShowDeliveryPointLayer(
  quickFilter: DeliveryPointQuickFilter,
  hasMeter: boolean,
): boolean {
  if (quickFilter === "all") return true;
  return quickFilter === "with_meter" ? hasMeter : !hasMeter;
}

export function buildParticelleFillOpacity(
  baseOpacity: number,
  quickFilter: ParticelleQuickFilter,
): number | maplibregl.ExpressionSpecification {
  const incompleteOpacityExpr: maplibregl.ExpressionSpecification = [
    "*",
    Math.min(baseOpacity, 0.22),
    0.45,
  ];
  if (quickFilter === "all") {
    return [
      "case",
      PARTICELLA_INCOMPLETE_KEY_EXPRESSION,
      incompleteOpacityExpr,
      baseOpacity,
    ] as maplibregl.ExpressionSpecification;
  }
  return [
    "case",
    PARTICELLA_INCOMPLETE_KEY_EXPRESSION,
    incompleteOpacityExpr,
    quickFilter === "ruolo" ? BOOLEAN_TRUE_EXPRESSION("ha_ruolo") : BOOLEAN_TRUE_EXPRESSION("ha_ruolo_inferito"),
    baseOpacity,
    0.05,
  ] as maplibregl.ExpressionSpecification;
}

export function buildParticelleOutlineColor(
  basemap: "osm" | "satellite" | "google_satellite" | null | undefined,
): string | maplibregl.ExpressionSpecification {
  const regularColor = basemap === "satellite" || basemap === "google_satellite" ? "#FACC15" : "#4F46E5";
  const incompleteColor = basemap === "satellite" || basemap === "google_satellite" ? "#EAB308" : "#C4008E";
  return [
    "case",
    PARTICELLA_INCOMPLETE_KEY_EXPRESSION,
    incompleteColor,
    regularColor,
  ] as maplibregl.ExpressionSpecification;
}
