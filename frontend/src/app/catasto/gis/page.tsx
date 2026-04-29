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
  const [gisInfo, setGisInfo] = useState<string | null>(null);
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
      setGisInfo(null);
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

  const handleImportXlsx = useCallback(async (file: File) => {
    if (!token) {
      setGisError("Sessione non disponibile. Accedi di nuovo.");
      return;
    }

    setXlsxBusy(true);
    setGisError(null);
    setGisInfo(null);
    try {
      const buffer = await file.arrayBuffer();
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

      const withGeometry = resolved.geojson?.features.filter((f) => f.geometry != null).length ?? 0;

      if (resolved.found === 0) {
        setGisError(`Nessuna particella trovata su ${resolved.processed} righe.`);
      } else {
        if (withGeometry === 0) {
          setGisError(
            `Trovate ${resolved.found} particelle ma nessuna ha geometria: controlla che lo shapefile sia stato importato.`,
          );
        } else if (resolved.not_found + resolved.multiple + resolved.invalid > 0) {
          const parts: string[] = [`Import completato: trovate ${resolved.found}/${resolved.processed}.`];
          if (resolved.not_found > 0) parts.push(`Non trovate: ${resolved.not_found}.`);
          if (resolved.multiple > 0) parts.push(`Multiple: ${resolved.multiple}.`);
          if (resolved.invalid > 0) parts.push(`Righe invalide: ${resolved.invalid}.`);
          setGisInfo(parts.join(" "));
        }
      }
    } catch (e) {
      setGisError(e instanceof Error ? e.message : "Import Excel fallito");
    } finally {
      setXlsxBusy(false);
    }
  }, [token]);

  return (
    <CatastoPage
      title="GIS"
      description="Analisi spaziale delle particelle catastali con layer MVT e selezione GIS."
      breadcrumb="Catasto / GIS"
      requiredModule="catasto"
    >
      <div className="flex h-[calc(100vh-190px)] min-h-[560px] flex-col overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
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
        ) : gisInfo ? (
          <div className="mx-4 mt-3 rounded-lg border border-amber-100 bg-amber-50 px-3 py-2 text-sm text-amber-700">
            {gisInfo}
          </div>
        ) : null}

        <div className={`grid min-h-0 flex-1 overflow-hidden ${isExpanded ? "lg:grid-cols-1" : "lg:grid-cols-2"}`}>
          <div
            className={
              isExpanded
                ? "fixed inset-0 z-50 flex flex-col"
                : "h-full bg-gray-100 p-3"
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

            <div className={isExpanded ? "relative pointer-events-none flex min-h-0 flex-1 p-3" : "h-full"}>
              <div
                className={
                  isExpanded
                    ? "pointer-events-auto min-h-0 w-full overflow-hidden rounded-2xl bg-gray-100 shadow-2xl ring-1 ring-white/10"
                    : "h-full"
                }
              >
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
            <aside className="flex h-full flex-col overflow-hidden border-t border-gray-100 bg-white lg:border-l lg:border-t-0">

              {/* ── Controls ── */}
              <div className="flex flex-col gap-4 border-b border-gray-100 px-4 py-4">

                {/* Layer toggles */}
                <div>
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-gray-400">Layer visibili</p>
                  <div className="flex flex-wrap gap-1.5">
                    {(
                      [
                        { label: "Distretti", active: showDistretti, onToggle: () => setShowDistretti((v) => !v), activeClass: "border-blue-200 bg-blue-50 text-blue-700", dotClass: "bg-blue-400" },
                        { label: "Particelle", active: showParticelle, onToggle: () => setShowParticelle((v) => !v), activeClass: "border-indigo-200 bg-indigo-50 text-indigo-700", dotClass: "bg-indigo-400" },
                        { label: "Evidenzia sel.", active: highlightSelected, onToggle: () => setHighlightSelected((v) => !v), activeClass: "border-amber-200 bg-amber-50 text-amber-700", dotClass: "bg-amber-400" },
                      ] as const
                    ).map(({ label, active, onToggle, activeClass, dotClass }) => (
                      <button
                        key={label}
                        type="button"
                        onClick={onToggle}
                        className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-all ${active ? activeClass : "border-gray-200 bg-white text-gray-400 hover:border-gray-300 hover:text-gray-600"}`}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full transition-colors ${active ? dotClass : "bg-gray-300"}`} />
                        {label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Distretto filter */}
                <div>
                  <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-gray-400">Filtro distretto</p>
                  <div className="flex items-center gap-2">
                    <input
                      value={distrettoLayer}
                      onChange={(e) => setDistrettoLayer(e.target.value)}
                      placeholder="es. 03"
                      className="w-24 rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-sm text-gray-900 placeholder-gray-400 transition focus:border-indigo-300 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100"
                    />
                    {distrettoLayer ? (
                      <button
                        type="button"
                        onClick={() => setDistrettoLayer("")}
                        className="flex h-7 w-7 items-center justify-center rounded-full text-gray-400 transition hover:bg-gray-100 hover:text-gray-600"
                        title="Rimuovi filtro"
                      >
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    ) : null}
                  </div>
                </div>

                {/* Excel import */}
                <div>
                  <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-gray-400">Import da Excel</p>
                  <label
                    className={`group flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed px-4 py-5 text-center transition-all ${
                      xlsxBusy
                        ? "cursor-wait border-gray-200 bg-gray-50 opacity-60"
                        : xlsxFile
                          ? "border-emerald-300 bg-emerald-50/60 hover:bg-emerald-50"
                          : "border-gray-200 bg-gray-50/60 hover:border-indigo-300 hover:bg-indigo-50/30"
                    }`}
                  >
                    <input
                      type="file"
                      accept=".xlsx,.xls"
                      className="sr-only"
                      onChange={(e) => {
                        const file = e.target.files?.[0] ?? null;
                        setXlsxFile(file);
                        if (file) void handleImportXlsx(file);
                      }}
                      disabled={xlsxBusy}
                    />
                    {xlsxBusy ? (
                      <>
                        <svg className="h-7 w-7 animate-spin text-emerald-500" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        <span className="text-sm font-medium text-emerald-600">Caricamento…</span>
                      </>
                    ) : xlsxFile ? (
                      <>
                        <svg className="h-7 w-7 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                        </svg>
                        <span className="max-w-full truncate text-sm font-semibold text-emerald-700">{xlsxFile.name}</span>
                        <span className="text-[11px] text-emerald-500">Clicca per cambiare file</span>
                      </>
                    ) : (
                      <>
                        <svg className="h-7 w-7 text-gray-400 transition group-hover:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                        </svg>
                        <span className="text-sm font-medium text-gray-600 transition group-hover:text-indigo-600">Clicca per selezionare</span>
                        <span className="text-[11px] text-gray-400">.xlsx · .xls · max 5 000 righe</span>
                      </>
                    )}
                  </label>
                  {uploadedGeojson ? (
                    <div className="mt-2">
                      <button
                        type="button"
                        onClick={() => { setUploadedGeojson(null); setXlsxFile(null); setGisInfo(null); setGisError(null); }}
                        className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-gray-200 bg-white py-2 text-sm text-gray-500 transition hover:bg-gray-50 hover:text-gray-700"
                      >
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                        Rimuovi dalla mappa
                      </button>
                    </div>
                  ) : null}
                </div>

              </div>

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
