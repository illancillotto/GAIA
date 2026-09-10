import type { Map as MapLibreMap } from "maplibre-gl";
import { TerraDraw, TerraDrawPolygonMode, TerraDrawSelectMode } from "terra-draw";
import { TerraDrawMapLibreGLAdapter } from "terra-draw-maplibre-gl-adapter";

type DrawCallbacks = {
  onGeometryDrawn: (geometry: GeoJSON.Geometry) => void;
  onSelectionCleared: () => void;
};

type CurrentDrawHandlers = {
  current: DrawCallbacks & { drawSignal: number };
};

export type TerritorioDrawController = {
  startPolygon: () => void;
  clear: () => void;
  destroy: () => void;
};

export function createTerritorioDraw(
  map: MapLibreMap,
  callbacks: DrawCallbacks,
): TerritorioDrawController {
  const draw = new TerraDraw({
    adapter: new TerraDrawMapLibreGLAdapter({ map }),
    modes: [
      new TerraDrawPolygonMode(),
      new TerraDrawSelectMode({
        flags: {
          polygon: {
            feature: {
              draggable: true,
              coordinates: { draggable: true, midpoints: true, deletable: true },
            },
          },
        },
      }),
    ],
  });

  const publishGeometry = (featureId: string | number) => {
    const geometry = draw.getSnapshotFeature(featureId)?.geometry;
    if (geometry) callbacks.onGeometryDrawn(geometry);
  };
  const handleFinish = (featureId: string | number) => {
    publishGeometry(featureId);
    draw.setMode("select");
    draw.selectFeature(featureId);
  };
  let isProgrammaticClear = false;
  const handleChange = (featureIds: Array<string | number>, type: string) => {
    if (type === "delete") {
      if (!isProgrammaticClear) callbacks.onSelectionCleared();
      return;
    }
    if (type === "update") featureIds.forEach(publishGeometry);
  };

  draw.on("finish", handleFinish);
  draw.on("change", handleChange);
  draw.start();

  return {
    startPolygon: () => draw.setMode("polygon"),
    clear: () => {
      isProgrammaticClear = true;
      try {
        draw.clear();
      } finally {
        isProgrammaticClear = false;
      }
    },
    destroy: () => {
      draw.off("finish", handleFinish);
      draw.off("change", handleChange);
      draw.stop();
    },
  };
}

export function initializeTerritorioDraw(
  map: MapLibreMap,
  handlers: CurrentDrawHandlers,
): TerritorioDrawController {
  const draw = createTerritorioDraw(map, {
    onGeometryDrawn: (geometry) => handlers.current.onGeometryDrawn(geometry),
    onSelectionCleared: () => handlers.current.onSelectionCleared(),
  });
  if (handlers.current.drawSignal > 0) draw.startPolygon();
  return draw;
}
