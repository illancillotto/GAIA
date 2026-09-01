"use client";

import { useEffect, useRef, useState } from "react";
import type maplibregl from "maplibre-gl";

import TerritorioRegisteredMap, { type TerritorioRegisteredMapProps } from "./TerritorioRegisteredMap";
import { subscribeTerritorioMaps } from "./territorio-map-registry";
import TerritorioLayerPanel from "@/components/catasto/gis/TerritorioLayerPanel";
import InterrogazionePanel from "@/components/catasto/gis/InterrogazionePanel";
import {
  useTerritorioLayers,
  type TerritorioMapAdapter,
} from "@/components/catasto/gis/use-territorio-layers";
import { useInterrogazione } from "@/components/catasto/gis/use-interrogazione";
import TerritorioFieldTools, { type FieldMap } from "@/components/catasto/gis/TerritorioFieldTools";
import TerritorioUnifiedSearch from "@/components/catasto/gis/TerritorioUnifiedSearch";
import { useAppShellContext } from "@/components/layout/app-shell-context";

type TerritorioMapExperienceProps = TerritorioRegisteredMapProps;

function parcelIdFromGaia(
  gaia: Array<{ source_id: string; data: Array<Record<string, unknown>> }>,
): string | null {
  const id = gaia.find((source) => source.source_id === "particella")?.data[0]?.id;
  return typeof id === "string" ? id : null;
}

export default function TerritorioMapExperience(props: TerritorioMapExperienceProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<maplibregl.Map | null>(null);
  const territorio = useTerritorioLayers(map as TerritorioMapAdapter | null, props.token);
  const interrogazione = useInterrogazione(map, props.token, territorio.groups);
  const { currentUser } = useAppShellContext();

  useEffect(
    () => subscribeTerritorioMaps((availableMaps) => {
      const container = containerRef.current;
      const ownedMap = [...availableMaps].reverse().find(
        (candidate) => container?.contains(candidate.getContainer()),
      );
      setMap(ownedMap ?? null);
    }),
    [],
  );

  return (
    <div ref={containerRef} className="relative h-full w-full">
      <TerritorioRegisteredMap {...props} />
      <TerritorioUnifiedSearch
        token={props.token}
        map={map}
        groups={territorio.groups}
        enabled={territorio.enabled}
      />
      <TerritorioLayerPanel {...territorio} basemap={props.basemap ?? "osm"} />
      <InterrogazionePanel
        {...interrogazione}
        scheda={{
          token: props.token,
          particellaId: parcelIdFromGaia(interrogazione.gaia),
          currentUser,
        }}
      />
      <TerritorioFieldTools map={map as unknown as FieldMap | null} groups={territorio.groups} enabled={territorio.enabled} />
    </div>
  );
}
