"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import * as XLSX from "xlsx";

import AnalysisPanel from "@/components/catasto/gis/AnalysisPanel";
import DrawingTools from "@/components/catasto/gis/DrawingTools";
import SelectionPanel from "@/components/catasto/gis/SelectionPanel";
import { CatastoPage } from "@/components/catasto/catasto-page";
import { catastoGisExport, catastoGisResolveRefs } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import { useGisSelection } from "@/hooks/useGisSelection";
import type { GisFilters, GisParticellaRef } from "@/types/gis";

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
  const [resizeSignal, setResizeSignal] = useState(0);
  const [isExpanded, setIsExpanded] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [gisError, setGisError] = useState<string | null>(null);
  const [showDistretti, setShowDistretti] = useState(true);
  const [showParticelle, setShowParticelle] = useState(true);
  const [highlightSelected, setHighlightSelected] = useState(true);
  const [distrettoLayer, setDistrettoLayer] = useState<string>("");
  const [xlsxFile, setXlsxFile] = useState<File | null>(null);
  const [xlsxBusy, setXlsxBusy] = useState(false);
  const [uploadedGeojson, setUploadedGeojson] = useState<GeoJSON.FeatureCollection | null>(null);
  const activeFilters = useMemo<GisFilters>(() => ({}), []);
  const { result, isLoading, error, runSelection, clearSelection } = useGisSelection(token);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  useEffect(() => {
    if (!isExpanded) return;
    const previousOverflow = window.document.body.style.overflow;
    window.document.body.style.overflow = "hidden";
    return () => {
      window.document.body.style.overflow = previousOverflow;
    };
  }, [isExpanded]);

  useEffect(() => {
    if (!isExpanded) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setIsExpanded(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isExpanded]);

  useEffect(() => {
    // MapLibre sometimes needs a couple of ticks after layout changes
    // (e.g. exiting fixed/fullscreen) to settle its canvas size.
    const raf1 = window.requestAnimationFrame(() => {
      setResizeSignal((value) => value + 1);
    });
    const raf2 = window.requestAnimationFrame(() => {
      setResizeSignal((value) => value + 1);
    });
    const timeout = window.setTimeout(() => {
      setResizeSignal((value) => value + 1);
    }, 150);

    return () => {
      window.cancelAnimationFrame(raf1);
      window.cancelAnimationFrame(raf2);
      window.clearTimeout(timeout);
    };
  }, [isExpanded]);

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

  const openExpanded = useCallback(() => {
    setIsExpanded(true);
  }, []);

  const closeExpanded = useCallback(() => {
    setIsExpanded(false);
  }, []);

  const handleExport = useCallback(
    async (format: "geojson" | "csv") => {
      if (!token || !result || result.particelle.length === 0) return;

      setExportError(null);
      setGisError(null);
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

  const handleImportXlsx = useCallback(async () => {
    if (!token) {
      setGisError("Sessione non disponibile. Accedi di nuovo.");
      return;
    }
    if (!xlsxFile) {
      setGisError("Seleziona un file Excel (.xlsx/.xls) con colonne: comune, sezione, foglio, particella, sub.");
      return;
    }

    setXlsxBusy(true);
    setGisError(null);
    try {
      const buffer = await xlsxFile.arrayBuffer();
      const workbook = XLSX.read(buffer, { type: "array" });
      const sheetName = workbook.SheetNames[0];
      const ws = workbook.Sheets[sheetName];
      const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(ws, { defval: null });

      const items: GisParticellaRef[] = rows.slice(0, 5000).map((r, i) => ({
        row_index: i + 2, // assume header row
        comune: (r["comune"] ?? r["Comune"] ?? r["COMUNE"] ?? null) as string | null,
        sezione: (r["sezione"] ?? r["Sezione"] ?? r["SEZIONE"] ?? null) as string | null,
        foglio: (r["foglio"] ?? r["Foglio"] ?? r["FOGLIO"] ?? null) as string | null,
        particella: (r["particella"] ?? r["Particella"] ?? r["PARTICELLA"] ?? null) as string | null,
        sub: (r["sub"] ?? r["Sub"] ?? r["SUB"] ?? r["subalterno"] ?? r["Subalterno"] ?? null) as string | null,
      }));

      const resolved = await catastoGisResolveRefs(token, items, { includeGeometry: true });
      setUploadedGeojson(resolved.geojson ?? null);

      if (resolved.not_found + resolved.multiple + resolved.invalid > 0) {
        setGisError(
          `Import completato: trovate ${resolved.found}/${resolved.processed}. ` +
            `Non trovate: ${resolved.not_found}, multiple: ${resolved.multiple}, righe invalide: ${resolved.invalid}.`,
        );
      }
    } catch (e) {
      setGisError(e instanceof Error ? e.message : "Import Excel fallito");
    } finally {
      setXlsxBusy(false);
    }
  }, [token, xlsxFile]);

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
          <div className="flex flex-wrap items-center justify-between gap-2 lg:justify-end">
            <button
              type="button"
              onClick={openExpanded}
              className="inline-flex items-center justify-center rounded-full border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-gray-900 shadow-sm transition hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              Vista estesa
            </button>
            <DrawingTools
              onDrawPolygon={() => setDrawSignal((value) => value + 1)}
              onClearDrawing={handleClearSelection}
              isLoading={isLoading}
              hasSelection={hasDrawing}
              nParticelle={result?.n_particelle}
            />
          </div>
        </div>

        {error || exportError || gisError ? (
          <div className="mx-4 mt-3 rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error || exportError || gisError}
          </div>
        ) : null}

        <div className={`grid flex-1 overflow-hidden ${isExpanded ? "lg:grid-cols-1" : "lg:grid-cols-2"}`}>
          <div
            className={
              isExpanded
                ? "fixed inset-0 z-50 flex flex-col"
                : "min-h-[680px] bg-gray-100 p-3 lg:min-h-[calc(100vh-260px)]"
            }
          >
            {isExpanded ? (
              <div className="absolute inset-0 bg-black/50" onClick={closeExpanded} />
            ) : null}

            {isExpanded ? (
              <div className="relative flex items-center justify-between gap-3 border-b border-white/10 bg-gray-950/90 px-4 py-3 text-white backdrop-blur">
                <div>
                  <div className="text-sm font-semibold">Vista estesa GIS</div>
                  <div className="text-xs text-white/70">Premi Esc per uscire</div>
                </div>
                <div className="flex items-center gap-2">
                  <DrawingTools
                    onDrawPolygon={() => setDrawSignal((value) => value + 1)}
                    onClearDrawing={handleClearSelection}
                    isLoading={isLoading}
                    hasSelection={hasDrawing}
                    nParticelle={result?.n_particelle}
                  />
                  <button
                    type="button"
                    onClick={closeExpanded}
                    className="inline-flex items-center justify-center rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/15 focus:outline-none focus:ring-2 focus:ring-white/60"
                  >
                    Chiudi
                  </button>
                </div>
              </div>
            ) : null}

            <div className={isExpanded ? "relative pointer-events-none flex min-h-0 flex-1 p-3" : ""}>
              <div
                className={
                  isExpanded
                    ? "pointer-events-auto min-h-0 w-full overflow-hidden rounded-2xl bg-gray-100 shadow-2xl ring-1 ring-white/10"
                    : ""
                }
              >
                <div className={isExpanded ? "pointer-events-auto px-1 pb-2" : "px-1 pb-2"}>
                  <div className="flex flex-wrap items-end gap-3 rounded-2xl border border-gray-200 bg-white px-4 py-3 shadow-sm">
                    <div className="flex items-center gap-2">
                      <label className="flex items-center gap-2 text-sm text-gray-700">
                        <input type="checkbox" checked={showDistretti} onChange={(e) => setShowDistretti(e.target.checked)} />
                        Distretti
                      </label>
                      <label className="flex items-center gap-2 text-sm text-gray-700">
                        <input type="checkbox" checked={showParticelle} onChange={(e) => setShowParticelle(e.target.checked)} />
                        Particelle
                      </label>
                      <label className="flex items-center gap-2 text-sm text-gray-700">
                        <input type="checkbox" checked={highlightSelected} onChange={(e) => setHighlightSelected(e.target.checked)} />
                        Evidenzia selezione
                      </label>
                    </div>

                    <div className="flex items-end gap-2">
                      <div>
                        <div className="text-[11px] font-semibold uppercase tracking-wide text-gray-500">Distretto</div>
                        <input
                          value={distrettoLayer}
                          onChange={(e) => setDistrettoLayer(e.target.value)}
                          placeholder="es. 03"
                          className="mt-1 w-28 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900"
                        />
                      </div>
                      <button
                        type="button"
                        className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-semibold text-gray-900 hover:bg-gray-50"
                        onClick={() => setDistrettoLayer("")}
                      >
                        Reset
                      </button>
                    </div>

                    <div className="flex flex-1 flex-wrap items-end justify-end gap-2">
                      <div>
                        <div className="text-[11px] font-semibold uppercase tracking-wide text-gray-500">Import Excel</div>
                        <input
                          type="file"
                          accept=".xlsx,.xls"
                          onChange={(e) => setXlsxFile(e.target.files?.[0] ?? null)}
                          className="mt-1 block w-full text-sm text-gray-700"
                          disabled={xlsxBusy}
                        />
                      </div>
                      <button
                        type="button"
                        onClick={() => void handleImportXlsx()}
                        disabled={!xlsxFile || xlsxBusy}
                        className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-emerald-300"
                      >
                        {xlsxBusy ? "Caricamento…" : "Visualizza particelle"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setUploadedGeojson(null)}
                        className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-semibold text-gray-900 hover:bg-gray-50"
                      >
                        Pulisci import
                      </button>
                    </div>
                  </div>
                </div>
                <MapContainer
                  token={token}
                  onGeometryDrawn={handleGeometryDrawn}
                  onSelectionCleared={handleClearSelection}
                  selectedIds={result?.particelle.map((particella) => particella.id) ?? []}
                  filters={activeFilters}
                  mapLayers={{
                    showDistretti,
                    showParticelle,
                    distretto: distrettoLayer.trim() ? distrettoLayer.trim() : null,
                    highlightSelected,
                  }}
                  uploadedGeojson={uploadedGeojson}
                  drawSignal={drawSignal}
                  clearSignal={clearSignal}
                  resizeSignal={resizeSignal}
                  className={isExpanded ? "min-h-0 h-full rounded-2xl" : ""}
                />
              </div>
            </div>
          </div>

          {!isExpanded ? (
            <aside className="flex min-h-[360px] flex-col overflow-hidden border-t border-gray-100 bg-white lg:min-h-[calc(100vh-260px)] lg:border-l lg:border-t-0">
              <AnalysisPanel result={result} isLoading={isLoading} onExport={handleExport} />
              {result ? (
                <SelectionPanel particelle={result.particelle} truncated={result.truncated} nTotale={result.n_particelle} />
              ) : null}
            </aside>
          ) : null}
        </div>
      </div>
    </CatastoPage>
  );
}
