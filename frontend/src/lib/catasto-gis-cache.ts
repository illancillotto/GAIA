export const DELIVERY_POINTS_TILE_REVISION_STORAGE_KEY = "gaia.catasto.deliveryPointsTileRevision";
export const DEFAULT_DELIVERY_POINTS_TILE_REVISION = "initial";

export function getStoredDeliveryPointsTileRevision(): string {
  if (typeof window === "undefined") {
    return DEFAULT_DELIVERY_POINTS_TILE_REVISION;
  }
  return window.localStorage.getItem(DELIVERY_POINTS_TILE_REVISION_STORAGE_KEY) ?? DEFAULT_DELIVERY_POINTS_TILE_REVISION;
}

export function storeDeliveryPointsTileRevision(revision: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(DELIVERY_POINTS_TILE_REVISION_STORAGE_KEY, revision);
}
