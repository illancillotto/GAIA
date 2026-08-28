"use client";

import { useEffect, useRef, useState, type ComponentProps } from "react";
import type maplibregl from "maplibre-gl";

import MapContainer from "./MapContainer";
import TerritorioLayerPanel from "@/components/catasto/gis/TerritorioLayerPanel";
import InterrogazionePanel from "@/components/catasto/gis/InterrogazionePanel";
import { subscribeTerritorioMaps } from "@/components/catasto/gis/territorio-map-registry";
import {
  useTerritorioLayers,
  type TerritorioMapAdapter,
} from "@/components/catasto/gis/use-territorio-layers";
import { useInterrogazione } from "@/components/catasto/gis/use-interrogazione";

type TerritorioMapExperienceProps = ComponentProps<typeof MapContainer>;

export default function TerritorioMapExperience(props: TerritorioMapExperienceProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<maplibregl.Map | null>(null);
  const territorio = useTerritorioLayers(map as TerritorioMapAdapter | null, props.token);
  const interrogazione = useInterrogazione(map, props.token, territorio.groups);

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
      <MapContainer {...props} />
      <TerritorioLayerPanel {...territorio} basemap={props.basemap ?? "osm"} />
      <InterrogazionePanel {...interrogazione} />
    </div>
  );
}
