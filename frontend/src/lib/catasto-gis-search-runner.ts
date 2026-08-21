import { catastoGisSearch } from "@/lib/api/catasto";
import { buildCatastoGisCoordinateSearchResponse } from "@/lib/catasto-gis-coordinate-search";
import type { GisSearchMode, GisSearchResponse } from "@/types/gis";

export const CATASTO_GIS_COORDINATE_FOCUS_OPTIONS = { maxZoom: 15, padding: 48, duration: 700 } as const;

export type CatastoGisSearchRunResult = {
  focusGeojson: GeoJSON.FeatureCollection | null;
  focusOptions?: {
    maxZoom?: number;
    padding?: number;
    duration?: number;
  };
  info: string;
  response: GisSearchResponse;
};

export async function runCatastoGisSmartSearch(
  token: string,
  query: string,
  mode: GisSearchMode,
  modeLabels: Record<GisSearchMode, string>,
): Promise<CatastoGisSearchRunResult> {
  const coordinateSearch = buildCatastoGisCoordinateSearchResponse(query);
  if (coordinateSearch) {
    return {
      focusGeojson: coordinateSearch.geojson,
      focusOptions: CATASTO_GIS_COORDINATE_FOCUS_OPTIONS,
      info: `Coordinate: ${coordinateSearch.label}.`,
      response: coordinateSearch.response,
    };
  }

  const response = await catastoGisSearch(token, { query, mode, limit: 25 });
  return {
    focusGeojson: response.geojson && response.geojson.features.length > 0 ? response.geojson : null,
    info:
      response.total > 0
        ? `Ricerca ${modeLabels[response.mode_resolved]}: ${response.total.toLocaleString("it-IT")} risultati.`
        : `Nessun risultato per “${query}”.`,
    response,
  };
}
