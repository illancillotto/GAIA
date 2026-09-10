"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { Map as MapLibreMap, MapMouseEvent } from "maplibre-gl";

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
import type { TerritorioSearchResult } from "@/components/catasto/gis/territorio-unified-search";
import { useAppShellContext } from "@/components/layout/app-shell-context";
import type { GisMapOverlayLayer } from "@/types/gis";

type TerritorioMapExperienceProps = TerritorioRegisteredMapProps;

export function usePortalTarget(
  ownerDocument: Pick<Document, "getElementById"> | undefined,
  targetId: string,
  trigger: unknown,
): HTMLElement | null {
  const [target, setTarget] = useState<HTMLElement | null>(null);
  useEffect(() => {
    setTarget(ownerDocument?.getElementById(targetId) ?? null);
  }, [ownerDocument, targetId, trigger]);
  return target;
}

export function findPortalTarget(
  ownerDocument: Pick<Document, "getElementById"> | undefined,
  expandedId: string,
  standardId: string,
): HTMLElement | null {
  return ownerDocument?.getElementById(expandedId) ?? ownerDocument?.getElementById(standardId) ?? null;
}

function parcelIdFromGaia(
  gaia: Array<{ source_id: string; data: Array<Record<string, unknown>> }>,
): string | null {
  const id = gaia.find((source) => source.source_id === "particella")?.data[0]?.id;
  return typeof id === "string" ? id : null;
}

function buildSearchOverlay(
  results: TerritorioSearchResult[],
  focused: boolean,
): GisMapOverlayLayer | null {
  const features = results.flatMap((result) =>
    result.kind === "particella" && result.feature ? [result.feature] : [],
  );
  if (features.length === 0) return null;
  return {
    layer_key: focused ? "gis-search-focus" : "gis-search-results",
    name: focused ? "Focus ricerca GIS" : "Risultati ricerca GIS",
    color: focused ? "#F000B8" : "#FACC15",
    outlineColor: focused ? "#C4008E" : "#F97316",
    pulse: true,
    pulseUntil: Date.now() + (focused ? 6_000 : 4_000),
    opacity: focused ? 0.9 : 0.82,
    showFill: true,
    showCentroids: false,
    featureClickMode: "particella",
    visible: true,
    geojson: { type: "FeatureCollection", features },
  };
}

export default function TerritorioMapExperience(props: TerritorioMapExperienceProps) {
  const [map, setMap] = useState<MapLibreMap | null>(null);
  const [searchOverlay, setSearchOverlay] = useState<GisMapOverlayLayer | null>(null);
  const lastClickedPointRef = useRef<{ lon: number; lat: number } | null>(null);
  const territorio = useTerritorioLayers(map as TerritorioMapAdapter | null, props.token);
  const interrogazione = useInterrogazione(props.token, territorio.groups);
  const { clear: clearInterrogation, interrogate } = interrogazione;
  const onParticellaClick = props.onParticellaClick;
  const { currentUser } = useAppShellContext();
  const territorioPanelTarget = findPortalTarget(globalThis.document, "gis-expanded-territorio-layers", "gis-territorio-layers");
  const fieldToolsTarget = findPortalTarget(globalThis.document, "gis-expanded-toolbar-tools", "gis-toolbar-tools");
  const interrogationTarget = usePortalTarget(globalThis.document, "gis-particella-interrogation", interrogazione.point);
  useEffect(() => {
    if (!map) return;
    const rememberClickedPoint = (event: MapMouseEvent) => {
      lastClickedPointRef.current = { lon: event.lngLat.lng, lat: event.lngLat.lat };
    };
    map.on("click", rememberClickedPoint);
    return () => { map.off("click", rememberClickedPoint); };
  }, [map]);
  const handleParticellaClick = useCallback<NonNullable<TerritorioRegisteredMapProps["onParticellaClick"]>>((particella) => {
    onParticellaClick?.(particella);
    const point = lastClickedPointRef.current;
    lastClickedPointRef.current = null;
    if (particella && point) interrogate(point);
    else clearInterrogation();
  }, [clearInterrogation, interrogate, onParticellaClick]);
  const handleSearchResults = useCallback((results: TerritorioSearchResult[]) => {
    setSearchOverlay(buildSearchOverlay(results, false));
  }, []);
  const handleResultFocus = useCallback((result: TerritorioSearchResult) => {
    setSearchOverlay(buildSearchOverlay([result], true));
  }, []);
  const mapOverlays = searchOverlay
    ? [searchOverlay, ...(props.overlayLayers ?? [])]
    : props.overlayLayers;
  const territorioPanel = <TerritorioLayerPanel {...territorio} basemap={props.basemap ?? "osm"} embedded={Boolean(territorioPanelTarget)} />;
  const fieldTools = (
    <TerritorioFieldTools
      map={map as unknown as FieldMap | null}
      groups={territorio.groups}
      enabled={territorio.enabled}
      compact={Boolean(fieldToolsTarget)}
    />
  );
  const unifiedSearch = (
    <TerritorioUnifiedSearch
      token={props.token}
      map={map}
      groups={territorio.groups}
      enabled={territorio.enabled}
      compact={Boolean(fieldToolsTarget)}
      onSearchResults={handleSearchResults}
      onResultFocus={handleResultFocus}
    />
  );

  return (
    <div className="relative h-full w-full">
      <TerritorioRegisteredMap {...props} overlayLayers={mapOverlays} onMapReady={setMap} onParticellaClick={handleParticellaClick} />
      {fieldToolsTarget ? createPortal(unifiedSearch, fieldToolsTarget) : unifiedSearch}
      {territorioPanelTarget ? createPortal(territorioPanel, territorioPanelTarget) : territorioPanel}
      {interrogationTarget ? createPortal(
        <InterrogazionePanel
          {...interrogazione}
          scheda={{
            token: props.token,
            particellaId: parcelIdFromGaia(interrogazione.gaia),
            currentUser,
          }}
        />,
        interrogationTarget,
      ) : null}
      {fieldToolsTarget ? createPortal(fieldTools, fieldToolsTarget) : fieldTools}
    </div>
  );
}
