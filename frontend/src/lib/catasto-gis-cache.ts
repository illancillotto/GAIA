export const GIS_TILE_REVISION_STORAGE_KEY = "gaia.catasto.gisTileRevision";
export const GIS_TILE_REVISION_UPDATED_EVENT = "gaia:catasto-gis-tile-revision-updated";
export const DEFAULT_GIS_TILE_REVISION = "initial";

export function getStoredGisTileRevision(): string {
  if (typeof window === "undefined") {
    return DEFAULT_GIS_TILE_REVISION;
  }
  return window.localStorage.getItem(GIS_TILE_REVISION_STORAGE_KEY) ?? DEFAULT_GIS_TILE_REVISION;
}

export function storeGisTileRevision(revision: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(GIS_TILE_REVISION_STORAGE_KEY, revision);
  window.dispatchEvent(new CustomEvent(GIS_TILE_REVISION_UPDATED_EVENT, { detail: { revision } }));
}
