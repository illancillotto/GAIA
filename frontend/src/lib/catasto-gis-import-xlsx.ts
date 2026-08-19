import type {
  GisParticellaRef,
  GisResolveRefsResponse,
  GisSavedSelectionDetail,
  GisSavedSelectionItemInput,
} from "@/types/gis";

export interface ImportStats {
  processed: number;
  found: number;
  notFound: number;
  multiple: number;
  invalid: number;
  withGeometry: number;
}

export interface ImportedOverlayLayerState {
  importStats: ImportStats | null;
  importedItems: GisSavedSelectionItemInput[];
  isPersisted: boolean;
}

export interface DraftOverlayLayerState extends ImportedOverlayLayerState {
  layer_key: string;
  saved_selection_id: string | null;
  name: string;
  color: string;
  opacity: number;
  visible: boolean;
  source_filename: string | null;
  geojson: GeoJSON.FeatureCollection;
}

const WORKSHEET_COLUMN_ALIASES = {
  comune: ["comune", "Comune", "COMUNE"],
  sezione: ["sezione", "Sezione", "SEZIONE"],
  foglio: ["foglio", "Foglio", "FOGLIO"],
  particella: ["particella", "Particella", "PARTICELLA"],
  sub: ["sub", "Sub", "SUB", "subalterno", "Subalterno"],
} as const;

const PARTICELLA_REF_FIELDS = ["comune", "sezione", "foglio", "particella", "sub"] as const;

function toNullableCellString(value: unknown): string | null {
  if (value == null) return null;
  const normalized = String(value).trim();
  return normalized.length > 0 ? normalized : null;
}

function firstNonNullishCell(row: Record<string, unknown>, aliases: readonly string[]): unknown {
  for (const alias of aliases) {
    const value = row[alias];
    if (value != null) return value;
  }
  return null;
}

export function buildParticellaRefsFromRows(rows: Array<Record<string, unknown>>): GisParticellaRef[] {
  return rows.slice(0, 5000).map((row, index) => {
    const values = Object.fromEntries(
      PARTICELLA_REF_FIELDS.map((field) => [
        field,
        toNullableCellString(firstNonNullishCell(row, WORKSHEET_COLUMN_ALIASES[field])),
      ]),
    ) as Pick<GisParticellaRef, (typeof PARTICELLA_REF_FIELDS)[number]>;
    return { row_index: index + 2, ...values };
  });
}

export function countFeaturesWithGeometry(geojson: GeoJSON.FeatureCollection | null | undefined): number {
  return geojson?.features.filter((feature) => feature.geometry != null).length ?? 0;
}

export function buildFoundSelectionItems(resolved: GisResolveRefsResponse): GisSavedSelectionItemInput[] {
  return resolved.results
    .filter((row) => row.esito === "FOUND" && row.particella_id)
    .map((row) => ({
      particella_id: row.particella_id as string,
      source_row_index: row.row_index ?? null,
      source_ref: {
        comune: row.comune_input,
        sezione: row.sezione_input,
        foglio: row.foglio_input,
        particella: row.particella_input,
        sub: row.sub_input,
      },
    }));
}

export function buildImportStatsFromDetail(detail: GisSavedSelectionDetail): ImportStats {
  const summary = detail.import_summary as Partial<ImportStats> | null | undefined;
  if (!summary) {
    return {
      processed: detail.n_particelle,
      found: detail.n_particelle,
      notFound: 0,
      multiple: 0,
      invalid: 0,
      withGeometry: detail.n_with_geometry,
    };
  }

  return {
    processed: Number(summary.processed ?? detail.n_particelle),
    found: Number(summary.found ?? detail.n_particelle),
    notFound: Number(summary.notFound ?? 0),
    multiple: Number(summary.multiple ?? 0),
    invalid: Number(summary.invalid ?? 0),
    withGeometry: detail.n_with_geometry,
  };
}

export function buildDraftOverlayLayer({
  fileName,
  layerIndex,
  layerColors,
  resolved,
  withGeometry,
}: {
  fileName: string;
  layerIndex: number;
  layerColors: string[];
  resolved: GisResolveRefsResponse;
  withGeometry: number;
}): DraftOverlayLayerState {
  return {
    layer_key: `draft-${layerIndex}`,
    saved_selection_id: null,
    name: fileName.replace(/\.(xlsx|xls)$/i, ""),
    color: layerColors[layerIndex % layerColors.length] ?? "#10B981",
    opacity: 0.55,
    visible: true,
    source_filename: fileName,
    geojson: resolved.geojson ?? { type: "FeatureCollection", features: [] },
    importStats: {
      processed: resolved.processed,
      found: resolved.found,
      notFound: resolved.not_found,
      multiple: resolved.multiple,
      invalid: resolved.invalid,
      withGeometry,
    },
    importedItems: buildFoundSelectionItems(resolved),
    isPersisted: false,
  };
}
