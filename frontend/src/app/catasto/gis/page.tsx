"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";

import AnalysisPanel from "@/components/catasto/gis/AnalysisPanel";
import DrawingTools from "@/components/catasto/gis/DrawingTools";
import SelectionPanel from "@/components/catasto/gis/SelectionPanel";
import { CatastoPage } from "@/components/catasto/catasto-page";
import { catastoGisExport } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import { useGisSelection } from "@/hooks/useGisSelection";
import type { GisFilters } from "@/types/gis";

const MapContainer = dynamic(() => import("@/components/catasto/gis/MapContainer"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[560px] items-center justify-center rounded-2xl bg-gray-100 text-sm text-gray-400">
      Caricamento GIS...
    </div>
  ),
});

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = window.document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function CatastoGisPage() {
  const [token, setToken] = useState<string | null>(null);
  const [hasDrawing, setHasDrawing] = useState(false);
  const [drawSignal, setDrawSignal] = useState(0);
  const [clearSignal, setClearSignal] = useState(0);
  const [exportError, setExportError] = useState<string | null>(null);
  const activeFilters = useMemo<GisFilters>(() => ({}), []);
  const { result, isLoading, error, runSelection, clearSelection } = useGisSelection(token);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  const handleGeometryDrawn = useCallback(
    async (geometry: GeoJSON.Geometry) => {
      setHasDrawing(true);
      await runSelection(geometry, activeFilters);
    },
    [activeFilters, runSelection],
  );

  const handleClearSelection = useCallback(() => {
    setHasDrawing(false);
    setClearSignal((value) => value + 1);
    clearSelection();
  }, [clearSelection]);

  const handleExport = useCallback(
    async (format: "geojson" | "csv") => {
      if (!token || !result || result.particelle.length === 0) return;

      setExportError(null);
      try {
        const blob = await catastoGisExport(
          token,
          result.particelle.map((particella) => particella.id),
          format,
        );
        triggerDownload(blob, `selezione_catasto.${format === "geojson" ? "geojson" : "csv"}`);
      } catch (downloadError) {
        setExportError(downloadError instanceof Error ? downloadError.message : "Export fallito");
      }
    },
    [result, token],
  );

  return (
    <CatastoPage
      title="GIS"
      description="Analisi spaziale delle particelle catastali con layer MVT e selezione GIS."
      breadcrumb="Catasto / GIS"
      requiredModule="catasto"
    >
      <div className="flex min-h-[calc(100vh-190px)] flex-col overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <div className="flex flex-col gap-3 border-b border-gray-100 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Catasto GIS</h2>
            <p className="text-sm text-gray-500">Vista centrata sul comprensorio consortile. Disegna un poligono per calcolare aggregazioni e preview particelle.</p>
          </div>
          <DrawingTools
            onDrawPolygon={() => setDrawSignal((value) => value + 1)}
            onClearDrawing={handleClearSelection}
            isLoading={isLoading}
            hasSelection={hasDrawing}
            nParticelle={result?.n_particelle}
          />
        </div>

        {error || exportError ? (
          <div className="mx-4 mt-3 rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error || exportError}
          </div>
        ) : null}

        <div className="grid flex-1 overflow-hidden lg:grid-cols-2">
          <div className="min-h-[680px] bg-gray-100 p-3 lg:min-h-[calc(100vh-260px)]">
            <MapContainer
              token={token}
              onGeometryDrawn={handleGeometryDrawn}
              onSelectionCleared={handleClearSelection}
              selectedIds={result?.particelle.map((particella) => particella.id) ?? []}
              filters={activeFilters}
              drawSignal={drawSignal}
              clearSignal={clearSignal}
            />
          </div>

          <aside className="flex min-h-[360px] flex-col overflow-hidden border-t border-gray-100 bg-white lg:min-h-[calc(100vh-260px)] lg:border-l lg:border-t-0">
            <AnalysisPanel result={result} isLoading={isLoading} onExport={handleExport} />
            {result ? (
              <SelectionPanel particelle={result.particelle} truncated={result.truncated} nTotale={result.n_particelle} />
            ) : null}
          </aside>
        </div>
      </div>
    </CatastoPage>
  );
}
