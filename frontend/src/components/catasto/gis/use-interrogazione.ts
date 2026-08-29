"use client";

import { useEffect, useState } from "react";

import {
  interrogaGisTerritorio,
  type GisInterrogazioneSource,
  type GisTerritorioLayer,
  type GisTerritorioLayerGroup,
} from "@/lib/api/territorio";

export type InterrogazioneViewSource = Omit<GisInterrogazioneSource, "status"> & {
  status: GisInterrogazioneSource["status"] | "loading";
  theme?: string;
  themeLabel?: string;
  attribution?: string;
};

export type InterrogazioneState = {
  open: boolean;
  armed: boolean;
  point: { lon: number; lat: number } | null;
  gaia: InterrogazioneViewSource[];
  catastoUfficiale: InterrogazioneViewSource[];
  territorio: InterrogazioneViewSource[];
  arm: () => void;
  close: () => void;
};

type MapClick = { lngLat: { lng: number; lat: number } };

export type InterrogazioneMap = {
  on: (event: "click", listener: (event: MapClick) => void) => void;
  off: (event: "click", listener: (event: MapClick) => void) => void;
};

const GAIA_LOADING: InterrogazioneViewSource[] = [
  "particella", "distretto", "punto_consegna", "rete_condotte", "dui", "ruolo_utenze",
].map((sourceId) => ({
  source_id: sourceId,
  title: sourceId.replaceAll("_", " "),
  status: "loading",
  duration_ms: 0,
  data: [],
  message: null,
}));

function externalPlaceholder(
  layer: GisTerritorioLayer,
  group: GisTerritorioLayerGroup,
): InterrogazioneViewSource {
  const visualOnly = layer.queryable === "wms_visual_only";
  return {
    source_id: layer.id,
    title: layer.title,
    status: visualOnly ? "skipped" : "loading",
    duration_ms: 0,
    data: [],
    message: visualOnly ? "Layer disponibile solo per la visualizzazione." : null,
    theme: group.theme,
    themeLabel: group.label,
    attribution: layer.attribution,
  };
}

function externalSources(groups: GisTerritorioLayerGroup[]): InterrogazioneViewSource[] {
  return groups.flatMap((group) => group.layers.map((layer) => externalPlaceholder(layer, group)));
}

function enrich(
  result: GisInterrogazioneSource,
  current: InterrogazioneViewSource,
): InterrogazioneViewSource {
  return { ...current, ...result };
}

function failed(current: InterrogazioneViewSource, error: unknown): InterrogazioneViewSource {
  return {
    ...current,
    status: "failed",
    message: error instanceof Error ? error.message : String(error),
  };
}

async function runWithLimit<T>(items: T[], limit: number, task: (item: T) => Promise<void>) {
  let index = 0;
  async function worker() {
    while (index < items.length) {
      const item = items[index++];
      await task(item);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
}

export function useInterrogazione(
  map: InterrogazioneMap | null,
  token: string | null,
  groups: GisTerritorioLayerGroup[],
): InterrogazioneState {
  const [open, setOpen] = useState(false);
  const [armed, setArmed] = useState(false);
  const [point, setPoint] = useState<{ lon: number; lat: number } | null>(null);
  const [gaia, setGaia] = useState<InterrogazioneViewSource[]>([]);
  const [catastoUfficiale, setCatastoUfficiale] = useState<InterrogazioneViewSource[]>([]);
  const [territorio, setTerritorio] = useState<InterrogazioneViewSource[]>([]);

  useEffect(() => {
    if (!map || !armed || !token) return;
    const onClick = ({ lngLat }: MapClick) => {
      const selectedPoint = { lon: lngLat.lng, lat: lngLat.lat };
      const placeholders = externalSources(groups);
      setArmed(false);
      setPoint(selectedPoint);
      setGaia(GAIA_LOADING);
      setCatastoUfficiale(placeholders.filter((source) => source.theme === "catasto_ufficiale"));
      setTerritorio(placeholders.filter((source) => source.theme !== "catasto_ufficiale"));

      void interrogaGisTerritorio(token, { ...selectedPoint, layer_ids: [] })
        .then((response) => setGaia(response.gaia.sources))
        .catch((error: unknown) => setGaia(GAIA_LOADING.map((source) => failed(source, error))));

      const queryable = groups.flatMap((group) => group.layers).filter((layer) => layer.queryable !== "wms_visual_only");
      void runWithLimit(queryable, 4, async (layer) => {
        const update = (source: InterrogazioneViewSource) => {
          const setter = source.theme === "catasto_ufficiale" ? setCatastoUfficiale : setTerritorio;
          setter((current) => current.map((item) => item.source_id === source.source_id ? source : item));
        };
        const current = placeholders.find((source) => source.source_id === layer.id)!;
        try {
          const response = await interrogaGisTerritorio(token, { ...selectedPoint, layer_ids: [layer.id] });
          const result = [...response.catasto_ufficiale.sources, ...response.territorio.sources][0];
          update(result ? enrich(result, current) : failed(current, "Risposta sorgente assente."));
        } catch (error) {
          update(failed(current, error));
        }
      });
    };
    map.on("click", onClick);
    return () => map.off("click", onClick);
  }, [armed, groups, map, token]);

  return {
    open,
    armed,
    point,
    gaia,
    catastoUfficiale,
    territorio,
    arm: () => { setOpen(true); setArmed(true); },
    close: () => { setOpen(false); setArmed(false); },
  };
}
