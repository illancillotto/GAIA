"use client";

import { useState } from "react";
import type { Map as MapLibreMap } from "maplibre-gl";

import TerritorioRegisteredMap, { type TerritorioRegisteredMapProps } from "./TerritorioRegisteredMap";
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
  const [map, setMap] = useState<MapLibreMap | null>(null);
  const territorio = useTerritorioLayers(map as TerritorioMapAdapter | null, props.token);
  const interrogazione = useInterrogazione(map, props.token, territorio.groups);
  const { currentUser } = useAppShellContext();

  return (
    <div className="relative h-full w-full">
      <TerritorioRegisteredMap {...props} onMapReady={setMap} />
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
