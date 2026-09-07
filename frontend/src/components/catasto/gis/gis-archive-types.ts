import type { Dispatch, SetStateAction } from "react";
import type { GisMapOverlayLayer, GisSavedSelectionItemInput } from "@/types/gis";

export interface ImportStats {
  processed: number;
  found: number;
  notFound: number;
  multiple: number;
  invalid: number;
  withGeometry: number;
}

export interface OverlayLayerState extends GisMapOverlayLayer {
  opacity: number;
  importStats: ImportStats | null;
  importedItems: GisSavedSelectionItemInput[];
  isPersisted: boolean;
}


export type ArchiveOptions = {
  token: string | null;
  autoSelectionId: string | null;
  overlayLayers: OverlayLayerState[];
  setOverlayLayers: Dispatch<SetStateAction<OverlayLayerState[]>>;
  setGisError: Dispatch<SetStateAction<string | null>>;
  setGisInfo: Dispatch<SetStateAction<string | null>>;
  focusLayerGeojson: (geojson: GeoJSON.FeatureCollection | null | undefined) => void;
  updateOverlayLayer: (key: string, update: (layer: OverlayLayerState) => OverlayLayerState) => void;
};
