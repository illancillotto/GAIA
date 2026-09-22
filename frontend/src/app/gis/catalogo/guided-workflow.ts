import type {
  GisCatalogChangeRequest,
  GisCatalogChangeRequestSaveInput,
  GisCatalogChangeRequestType,
  GisCatalogLayer,
  GisCatalogLayerFeature,
} from "@/types/gis";

export type GuidedChangeDraft = {
  changeType: GisCatalogChangeRequestType;
  featureId: string;
  fieldName: string;
  newValue: string;
  coordinates: string;
  propertyName: string;
  propertyValue: string;
  justification: string;
};

export const emptyGuidedChangeDraft: GuidedChangeDraft = {
  changeType: "attribute_update",
  featureId: "",
  fieldName: "",
  newValue: "",
  coordinates: "",
  propertyName: "",
  propertyValue: "",
  justification: "",
};

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function firstEntry(value: unknown): [string, unknown] | undefined {
  return Object.entries(objectValue(value))[0];
}

function coordinatesFromGeometry(
  geometry: Record<string, unknown>,
): number[][] {
  const type = String(geometry.type ?? "").toLowerCase();
  const coordinates = geometry.coordinates;
  if (!Array.isArray(coordinates)) return [];
  if (type === "point") return [coordinates as number[]];
  if (type === "linestring") return coordinates as number[][];
  if (["polygon", "multilinestring"].includes(type))
    return (coordinates[0] as number[][] | undefined) ?? [];
  if (type === "multipolygon")
    return (
      ((coordinates[0] as number[][][] | undefined)?.[0] as
        number[][] | undefined) ?? []
    );
  return [];
}

export function coordinatesTextFromGeometry(value: unknown): string {
  return coordinatesFromGeometry(objectValue(value))
    .map((coordinate) => `${coordinate[0] ?? ""}, ${coordinate[1] ?? ""}`)
    .join("\n");
}

function baseGeometryType(
  layer: GisCatalogLayer,
  selectedFeature?: GisCatalogLayerFeature | null,
): string {
  return String(
    selectedFeature?.geometry?.type ?? layer.geometry_type ?? "Point",
  ).toUpperCase();
}

function coordinatePairs(value: string): number[][] | null {
  const lines = value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  const pairs = lines.map((line) =>
    line
      .split(/[;,\s]+/)
      .filter(Boolean)
      .map(Number),
  );
  if (
    pairs.some(
      (pair) =>
        pair.length !== 2 ||
        pair.some((coordinate) => !Number.isFinite(coordinate)),
    )
  )
    return null;
  return pairs;
}

export function geometryFromCoordinates(
  value: string,
  layer: GisCatalogLayer,
  selectedFeature?: GisCatalogLayerFeature | null,
): Record<string, unknown> | null {
  const pairs = coordinatePairs(value);
  if (!pairs?.length) return null;
  const type = baseGeometryType(layer, selectedFeature);
  let geometry: { type: string; coordinates: number[] | number[][] | number[][][] };
  if (type.includes("POINT")) {
    if (pairs.length !== 1) return null;
    geometry = { type: "Point", coordinates: pairs[0] };
  } else if (type.includes("POLYGON")) {
    if (pairs.length < 3) return null;
    const ring = [...pairs];
    const last = ring[ring.length - 1];
    if (ring[0][0] !== last[0] || ring[0][1] !== last[1])
      ring.push([...ring[0]]);
    geometry = { type: "Polygon", coordinates: [ring] };
  } else {
    if (pairs.length < 2) return null;
    geometry = { type: "LineString", coordinates: pairs };
  }
  if (type.startsWith("MULTI")) {
    return { type: `Multi${geometry.type}`, coordinates: [geometry.coordinates] };
  }
  return geometry;
}

export function parseGuidedValue(
  value: string,
  currentValue?: unknown,
): unknown {
  const cleaned = value.trim();
  if (typeof currentValue === "number") {
    const numberValue = Number(cleaned);
    return Number.isFinite(numberValue) ? numberValue : cleaned;
  }
  if (typeof currentValue === "boolean") {
    if (["si", "true", "1"].includes(cleaned.toLowerCase())) return true;
    if (["no", "false", "0"].includes(cleaned.toLowerCase())) return false;
  }
  return cleaned;
}

export function guidedDraftFromChangeRequest(
  changeRequest?: GisCatalogChangeRequest | null,
): GuidedChangeDraft {
  if (!changeRequest) return emptyGuidedChangeDraft;
  const afterEntry = firstEntry(changeRequest.payload.after);
  const propertyEntry = firstEntry(changeRequest.payload.properties);
  return {
    changeType: changeRequest.change_type,
    featureId: changeRequest.feature_id ?? "",
    fieldName: afterEntry?.[0] ?? "",
    newValue: afterEntry?.[1] == null ? "" : String(afterEntry[1]),
    coordinates: coordinatesTextFromGeometry(changeRequest.payload.geometry),
    propertyName: propertyEntry?.[0] ?? "",
    propertyValue: propertyEntry?.[1] == null ? "" : String(propertyEntry[1]),
    justification: changeRequest.justification ?? "",
  };
}

function fallbackBefore(
  changeRequest?: GisCatalogChangeRequest | null,
): Record<string, unknown> {
  return objectValue(changeRequest?.payload.before);
}

export function guidedChangeValidation(
  draft: GuidedChangeDraft,
  layer: GisCatalogLayer,
  selectedFeature?: GisCatalogLayerFeature | null,
): string | null {
  if (draft.changeType !== "feature_create" && !draft.featureId)
    return "Seleziona l'elemento della mappa da correggere.";
  if (!draft.justification.trim())
    return "Spiega il motivo della richiesta prima di continuare.";
  if (
    draft.changeType === "attribute_update" &&
    (!draft.fieldName || !draft.newValue.trim())
  ) {
    return "Scegli il campo e inserisci il nuovo valore.";
  }
  if (
    draft.changeType === "feature_create" &&
    (!draft.propertyName.trim() || !draft.propertyValue.trim())
  ) {
    return "Inserisci almeno un dato descrittivo per il nuovo elemento.";
  }
  if (
    ["geometry_update", "feature_create"].includes(draft.changeType) &&
    !geometryFromCoordinates(draft.coordinates, layer, selectedFeature)
  ) {
    return "Inserisci coordinate valide, una coppia X e Y per riga.";
  }
  return null;
}

export function buildGuidedChangeInput(
  draft: GuidedChangeDraft,
  layer: GisCatalogLayer,
  selectedFeature?: GisCatalogLayerFeature | null,
  changeRequest?: GisCatalogChangeRequest | null,
): GisCatalogChangeRequestSaveInput {
  const before = selectedFeature?.attributes ?? fallbackBefore(changeRequest);
  let payload: Record<string, unknown>;
  if (draft.changeType === "attribute_update") {
    const currentValue = before[draft.fieldName];
    payload = {
      before: { [draft.fieldName]: currentValue },
      after: {
        [draft.fieldName]: parseGuidedValue(draft.newValue, currentValue),
      },
    };
  } else if (draft.changeType === "geometry_update") {
    payload = {
      geometry: geometryFromCoordinates(
        draft.coordinates,
        layer,
        selectedFeature,
      ),
    };
  } else if (draft.changeType === "feature_create") {
    payload = {
      properties: {
        [draft.propertyName.trim()]: parseGuidedValue(draft.propertyValue),
      },
      geometry: geometryFromCoordinates(
        draft.coordinates,
        layer,
        selectedFeature,
      ),
    };
  } else {
    payload = { before };
  }
  return {
    featureId:
      draft.changeType === "feature_create" ? undefined : draft.featureId,
    changeType: draft.changeType,
    payload,
    justification: draft.justification.trim(),
  };
}

export function readableValue(value: unknown): string {
  if (value == null || value === "") return "non valorizzato";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
