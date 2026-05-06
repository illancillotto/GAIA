"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as XLSX from "xlsx";

import AnalysisPanel from "@/components/catasto/gis/AnalysisPanel";
import DrawingTools from "@/components/catasto/gis/DrawingTools";
import SelectionPanel from "@/components/catasto/gis/SelectionPanel";
import { CatastoPage } from "@/components/catasto/catasto-page";
import {
  catastoGisCreateSavedSelection,
  catastoGisDeleteSavedSelection,
  catastoGisExport,
  catastoGisGetSavedSelection,
  catastoGisListSavedSelections,
  catastoGisResolveRefs,
  catastoGisUpdateSavedSelection,
} from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import { useGisSelection } from "@/hooks/useGisSelection";
import type {
  GisFilters,
  GisMapOverlayLayer,
  GisParticellaRef,
  GisSavedSelectionDetail,
  GisSavedSelectionItemInput,
  GisSavedSelectionSummary,
} from "@/types/gis";

const MapContainer = dynamic(() => import("@/components/catasto/gis/MapContainer"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[680px] items-center justify-center rounded-2xl bg-gray-100 text-sm text-gray-400">
      Caricamento GIS...
    </div>
  ),
});

interface ImportStats {
  processed: number;
  found: number;
  notFound: number;
  multiple: number;
  invalid: number;
  withGeometry: number;
}

interface OverlayLayerState extends GisMapOverlayLayer {
  importStats: ImportStats | null;
  importedItems: GisSavedSelectionItemInput[];
  isPersisted: boolean;
}

const LAYER_COLORS = ["#10B981", "#F59E0B", "#3B82F6", "#EF4444", "#8B5CF6", "#14B8A6", "#F97316"];

function toNullableCellString(value: unknown): string | null {
  if (value == null) return null;
  const normalized = String(value).trim();
  return normalized.length > 0 ? normalized : null;
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = window.document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function buildImportStatsFromDetail(detail: GisSavedSelectionDetail): ImportStats {
  const summary = detail.import_summary as Partial<ImportStats> | null | undefined;
  if (!summary) {
    return {
      processed: detail.n_particelle,
      found: detail.n_particelle,
      notFound: 0,
      multiple: 0,
      invalid: 0,
      withGeometry: detail.n_with_geometry,
    };
  }

  return {
    processed: Number(summary.processed ?? detail.n_particelle),
    found: Number(summary.found ?? detail.n_particelle),
    notFound: Number(summary.notFound ?? 0),
    multiple: Number(summary.multiple ?? 0),
    invalid: Number(summary.invalid ?? 0),
    withGeometry: detail.n_with_geometry,
  };
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
  const [showDistrettiFill, setShowDistrettiFill] = useState(false);
  const [showParticelle, setShowParticelle] = useState(true);
  const [highlightSelected, setHighlightSelected] = useState(true);
  const [distrettiOpacity, setDistrettiOpacity] = useState(0.3);
  const [particelleOpacity, setParticelleOpacity] = useState(0.42);
  const [distrettoLayer, setDistrettoLayer] = useState<string>("");
  const [xlsxFile, setXlsxFile] = useState<File | null>(null);
  const [xlsxBusy, setXlsxBusy] = useState(false);
  const [overlayLayers, setOverlayLayers] = useState<OverlayLayerState[]>([]);
  const [savedSelections, setSavedSelections] = useState<GisSavedSelectionSummary[]>([]);
  const [savedSelectionOpacities, setSavedSelectionOpacities] = useState<Record<string, number>>({});
  const [savedBusy, setSavedBusy] = useState(false);
  const [focusGeojson, setFocusGeojson] = useState<GeoJSON.FeatureCollection | null>(null);
  const [focusSignal, setFocusSignal] = useState(0);
  const layerCounterRef = useRef(0);
  const activeFilters = useMemo<GisFilters>(() => ({}), []);
  const { result, isLoading, error, runSelection, clearSelection } = useGisSelection(token);
  const loadedSavedSelectionIds = useMemo(
    () => new Set(overlayLayers.filter((layer) => layer.saved_selection_id).map((layer) => layer.saved_selection_id as string)),
    [overlayLayers],
  );
  const visibleOverlayLayers = useMemo(() => overlayLayers.filter((layer) => layer.visible), [overlayLayers]);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  const refreshSavedSelections = useCallback(async () => {
    if (!token) return;
    const selections = await catastoGisListSavedSelections(token);
    setSavedSelections(selections);
  }, [token]);

  useEffect(() => {
    if (!token) return;
    void refreshSavedSelections().catch((e) => {
      setGisError(e instanceof Error ? e.message : "Caricamento selezioni salvate fallito");
    });
  }, [refreshSavedSelections, token]);

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

  const focusLayerGeojson = useCallback((geojson: GeoJSON.FeatureCollection | null | undefined) => {
    if (!geojson || geojson.features.length === 0) return;
    setFocusGeojson(geojson);
    setFocusSignal((value) => value + 1);
    setResizeSignal((value) => value + 1);
  }, []);

  const updateOverlayLayer = useCallback((layerKey: string, updater: (layer: OverlayLayerState) => OverlayLayerState) => {
    setOverlayLayers((layers) => layers.map((layer) => (layer.layer_key === layerKey ? updater(layer) : layer)));
  }, []);

  const removeOverlayLayer = useCallback((layerKey: string) => {
    setOverlayLayers((layers) => layers.filter((layer) => layer.layer_key !== layerKey));
    setGisError(null);
    setGisInfo(null);
  }, []);

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
        comune: toNullableCellString(r["comune"] ?? r["Comune"] ?? r["COMUNE"] ?? null),
        sezione: toNullableCellString(r["sezione"] ?? r["Sezione"] ?? r["SEZIONE"] ?? null),
        foglio: toNullableCellString(r["foglio"] ?? r["Foglio"] ?? r["FOGLIO"] ?? null),
        particella: toNullableCellString(r["particella"] ?? r["Particella"] ?? r["PARTICELLA"] ?? null),
        sub: toNullableCellString(r["sub"] ?? r["Sub"] ?? r["SUB"] ?? r["subalterno"] ?? r["Subalterno"] ?? null),
      }));

      const resolved = await catastoGisResolveRefs(token, items, { includeGeometry: true });
      const withGeometry = resolved.geojson?.features.filter((f) => f.geometry != null).length ?? 0;
      const foundItems: GisSavedSelectionItemInput[] = resolved.results
        .filter((row) => row.esito === "FOUND" && row.particella_id)
        .map((row) => ({
          particella_id: row.particella_id as string,
          source_row_index: row.row_index ?? null,
          source_ref: {
            comune: row.comune_input,
            sezione: row.sezione_input,
            foglio: row.foglio_input,
            particella: row.particella_input,
            sub: row.sub_input,
          },
        }));
      const nextLayerIndex = layerCounterRef.current++;
      const nextLayer: OverlayLayerState = {
        layer_key: `draft-${nextLayerIndex}`,
        saved_selection_id: null,
        name: file.name.replace(/\.(xlsx|xls)$/i, ""),
        color: LAYER_COLORS[nextLayerIndex % LAYER_COLORS.length] ?? "#10B981",
        opacity: 0.55,
        visible: true,
        source_filename: file.name,
        geojson: resolved.geojson ?? { type: "FeatureCollection", features: [] },
        importStats: {
          processed: resolved.processed,
          found: resolved.found,
          notFound: resolved.not_found,
          multiple: resolved.multiple,
          invalid: resolved.invalid,
          withGeometry,
        },
        importedItems: foundItems,
        isPersisted: false,
      };
      setOverlayLayers((layers) => [...layers, nextLayer]);
      focusLayerGeojson(nextLayer.geojson);

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
  }, [focusLayerGeojson, token]);

  const handleSaveImportedLayer = useCallback(async (layerKey: string) => {
    if (!token) return;
    const layer = overlayLayers.find((item) => item.layer_key === layerKey);
    if (!layer || layer.isPersisted || layer.importedItems.length === 0 || !layer.importStats) return;
    const trimmedName = layer.name.trim();
    if (!trimmedName) {
      setGisError("Inserisci un nome per salvare il layer.");
      return;
    }

    setSavedBusy(true);
    setGisError(null);
    setGisInfo(null);
    try {
      const saved = await catastoGisCreateSavedSelection(token, {
        name: trimmedName,
        color: layer.color,
        source_filename: layer.source_filename ?? null,
        import_summary: layer.importStats as unknown as Record<string, unknown>,
        items: layer.importedItems,
      });
      setOverlayLayers((layers) =>
        layers.map((item) =>
          item.layer_key === layerKey
            ? {
                ...item,
                layer_key: saved.id,
                saved_selection_id: saved.id,
                name: saved.name,
                color: saved.color,
                geojson: saved.geojson ?? item.geojson,
                isPersisted: true,
              }
            : item,
        ),
      );
      await refreshSavedSelections();
      setGisInfo(`Layer salvato: ${saved.name} (${saved.n_particelle.toLocaleString("it-IT")} particelle).`);
    } catch (e) {
      setGisError(e instanceof Error ? e.message : "Salvataggio layer fallito");
    } finally {
      setSavedBusy(false);
    }
  }, [overlayLayers, refreshSavedSelections, token]);

  const handleLoadSavedSelection = useCallback(async (selectionId: string) => {
    if (!token) return;

    const existing = overlayLayers.find((layer) => layer.saved_selection_id === selectionId);
    if (existing) {
      updateOverlayLayer(existing.layer_key, (layer) => ({ ...layer, visible: true }));
      focusLayerGeojson(existing.geojson);
      setGisInfo(`Layer già disponibile in mappa: ${existing.name}.`);
      setGisError(null);
      return;
    }

    setSavedBusy(true);
    setGisError(null);
    setGisInfo(null);
    try {
      const detail = await catastoGisGetSavedSelection(token, selectionId);
      const loadedLayer: OverlayLayerState = {
        layer_key: detail.id,
        saved_selection_id: detail.id,
        name: detail.name,
        color: detail.color,
        opacity: savedSelectionOpacities[selectionId] ?? 0.55,
        visible: true,
        source_filename: detail.source_filename ?? null,
        geojson: detail.geojson ?? { type: "FeatureCollection", features: [] },
        importStats: buildImportStatsFromDetail(detail),
        importedItems: [],
        isPersisted: true,
      };
      setOverlayLayers((layers) => [...layers, loadedLayer]);
      focusLayerGeojson(loadedLayer.geojson);
      setGisInfo(`Layer caricato: ${detail.name}.`);
    } catch (e) {
      setGisError(e instanceof Error ? e.message : "Caricamento layer fallito");
    } finally {
      setSavedBusy(false);
    }
  }, [focusLayerGeojson, overlayLayers, savedSelectionOpacities, token, updateOverlayLayer]);

  const handleUpdatePersistedLayer = useCallback(async (layerKey: string) => {
    if (!token) return;
    const layer = overlayLayers.find((item) => item.layer_key === layerKey);
    if (!layer?.saved_selection_id) return;

    setSavedBusy(true);
    setGisError(null);
    setGisInfo(null);
    try {
      const updated = await catastoGisUpdateSavedSelection(token, layer.saved_selection_id, {
        name: layer.name.trim() || undefined,
        color: layer.color,
      });
      setOverlayLayers((layers) =>
        layers.map((item) =>
          item.layer_key === layerKey
            ? {
                ...item,
                name: updated.name,
                color: updated.color,
              }
            : item,
        ),
      );
      await refreshSavedSelections();
      setGisInfo(`Layer aggiornato: ${updated.name}.`);
    } catch (e) {
      setGisError(e instanceof Error ? e.message : "Aggiornamento layer fallito");
    } finally {
      setSavedBusy(false);
    }
  }, [overlayLayers, refreshSavedSelections, token]);

  const handleDeleteSavedSelection = useCallback(async (selectionId: string) => {
    if (!token) return;
    setSavedBusy(true);
    setGisError(null);
    setGisInfo(null);
    try {
      await catastoGisDeleteSavedSelection(token, selectionId);
      setOverlayLayers((layers) => layers.filter((layer) => layer.saved_selection_id !== selectionId));
      await refreshSavedSelections();
      setGisInfo("Layer salvato eliminato.");
    } catch (e) {
      setGisError(e instanceof Error ? e.message : "Eliminazione layer fallita");
    } finally {
      setSavedBusy(false);
    }
  }, [refreshSavedSelections, token]);

  const handleUpdateArchivedSelectionColor = useCallback(async (selectionId: string, color: string) => {
    if (!token) return;
    try {
      await catastoGisUpdateSavedSelection(token, selectionId, { color });
      setOverlayLayers((layers) => layers.map((l) => l.saved_selection_id === selectionId ? { ...l, color } : l));
    } catch (e) {
      setGisError(e instanceof Error ? e.message : "Aggiornamento colore fallito");
    }
  }, [token]);

  const handleArchiveOpacityChange = useCallback((selectionId: string, opacity: number) => {
    setSavedSelectionOpacities((prev) => ({ ...prev, [selectionId]: opacity }));
    setOverlayLayers((layers) =>
      layers.map((l) => l.saved_selection_id === selectionId ? { ...l, opacity } : l),
    );
  }, []);

  return (
    <CatastoPage
      title="GIS"
      description="Analisi spaziale delle particelle catastali con layer MVT e selezione GIS."
      breadcrumb="Catasto / GIS"
      requiredModule="catasto"
    >
      <div className="flex h-[calc(100vh-135px)] min-h-[720px] flex-col overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
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

        <div className={`grid min-h-0 flex-1 overflow-hidden ${isExpanded ? "lg:grid-cols-1" : "lg:grid-cols-[minmax(0,1.55fr)_420px]"}`}>
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
                    showDistrettiFill,
                    showParticelle,
                    distrettiOpacity,
                    particelleOpacity,
                    distretto: distrettoLayer.trim() ? distrettoLayer.trim() : null,
                    highlightSelected,
                  }}
                  overlayLayers={visibleOverlayLayers}
                  focusGeojson={focusGeojson}
                  focusSignal={focusSignal}
                  drawSignal={drawSignal}
                  clearSignal={clearSignal}
                  resizeSignal={resizeSignal}
                  className={isExpanded ? "min-h-0 h-full rounded-2xl" : ""}
                />
              </div>
            </div>
          </div>

          {!isExpanded ? (
            <aside className="flex h-full min-h-0 flex-col overflow-hidden border-t border-gray-100 bg-white lg:border-l lg:border-t-0">

              {/* ── Controls ── */}
              <div className="shrink-0 border-b border-gray-100 px-4 py-4">

                {/* Layer toggles */}
                <div className="flex flex-col gap-4">
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-gray-400">Layer visibili</p>
                  <div className="flex flex-wrap gap-1.5">
                    <div className="group relative">
                      <button
                        type="button"
                        onClick={() => setShowDistretti((v) => !v)}
                        className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-all ${
                          showDistretti
                            ? "border-blue-200 bg-blue-50 text-blue-700"
                            : "border-gray-200 bg-white text-gray-400 hover:border-gray-300 hover:text-gray-600"
                        }`}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full transition-colors ${showDistretti ? "bg-blue-400" : "bg-gray-300"}`} />
                        Distretti
                      </button>
                      <div className="pointer-events-none absolute left-0 top-full z-10 mt-2 w-52 translate-y-1 rounded-2xl border border-blue-100 bg-white/95 p-3 opacity-0 shadow-xl ring-1 ring-black/5 backdrop-blur transition-all duration-150 group-hover:pointer-events-auto group-hover:translate-y-0 group-hover:opacity-100 group-focus-within:pointer-events-auto group-focus-within:translate-y-0 group-focus-within:opacity-100">
                        <button
                          type="button"
                          onClick={() => setShowDistrettiFill((v) => !v)}
                          className={`mb-3 inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-medium transition-all ${
                            showDistrettiFill
                              ? "border-sky-200 bg-sky-50 text-sky-700"
                              : "border-gray-200 bg-white text-gray-500 hover:border-sky-100 hover:text-sky-700"
                          }`}
                        >
                          <span className={`h-1.5 w-1.5 rounded-full transition-colors ${showDistrettiFill ? "bg-sky-400" : "bg-gray-300"}`} />
                          Riempimento
                        </button>
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-medium text-blue-900/75">Opacità bordo + fill</span>
                          <span className="rounded-full bg-blue-50 px-2 py-0.5 font-semibold text-blue-700">
                            {Math.round(distrettiOpacity * 100)}%
                          </span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.05"
                          value={distrettiOpacity}
                          onChange={(e) => setDistrettiOpacity(Number(e.target.value))}
                          className="mt-2 w-full accent-blue-600"
                        />
                      </div>
                    </div>
                    <div className="group relative">
                      <button
                        type="button"
                        onClick={() => setShowParticelle((v) => !v)}
                        className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-all ${
                          showParticelle
                            ? "border-indigo-200 bg-indigo-50 text-indigo-700"
                            : "border-gray-200 bg-white text-gray-400 hover:border-gray-300 hover:text-gray-600"
                        }`}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full transition-colors ${showParticelle ? "bg-indigo-400" : "bg-gray-300"}`} />
                        Particelle
                      </button>
                      <div className="pointer-events-none absolute left-0 top-full z-10 mt-2 w-52 translate-y-1 rounded-2xl border border-indigo-100 bg-white/95 p-3 opacity-0 shadow-xl ring-1 ring-black/5 backdrop-blur transition-all duration-150 group-hover:pointer-events-auto group-hover:translate-y-0 group-hover:opacity-100 group-focus-within:pointer-events-auto group-focus-within:translate-y-0 group-focus-within:opacity-100">
                        <div className="mb-2 flex items-center justify-between text-[11px]">
                          <span className="font-medium text-indigo-900/75">Opacità bordo + fill</span>
                          <span className="rounded-full bg-indigo-50 px-2 py-0.5 font-semibold text-indigo-700">
                            {Math.round(particelleOpacity * 100)}%
                          </span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.05"
                          value={particelleOpacity}
                          onChange={(e) => setParticelleOpacity(Number(e.target.value))}
                          className="w-full accent-indigo-600"
                        />
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setHighlightSelected((v) => !v)}
                      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-all ${
                        highlightSelected
                          ? "border-amber-200 bg-amber-50 text-amber-700"
                          : "border-gray-200 bg-white text-gray-400 hover:border-gray-300 hover:text-gray-600"
                      }`}
                    >
                      <span className={`h-1.5 w-1.5 rounded-full transition-colors ${highlightSelected ? "bg-amber-400" : "bg-gray-300"}`} />
                      Evidenzia sel.
                    </button>
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
                <div className="rounded-2xl border border-emerald-100 bg-emerald-50/30 p-3">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-emerald-700">Import da Excel</p>
                    <span className="text-[11px] text-gray-500">{overlayLayers.length.toLocaleString("it-IT")} layer in workspace</span>
                  </div>
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
                  <p className="mt-2 text-[11px] text-gray-500">
                    Colonne attese: <span className="font-medium">comune</span>, <span className="font-medium">sezione</span>, <span className="font-medium">foglio</span>, <span className="font-medium">particella</span>, <span className="font-medium">sub</span>. Nel campo{" "}
                    <span className="font-medium">comune</span> puoi usare nome comune, codice Capacitas numerico oppure codice catastale/Belfiore.
                  </p>
                </div>
              </div>

              <div className="min-h-0 flex-1 overflow-hidden px-4 py-4">
                <div className="flex h-full min-h-0 flex-col gap-4">
                  <div className="min-h-0 flex-1 overflow-hidden">
                    <div className="mb-2 flex items-center justify-between">
                      <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-400">Layer in mappa</p>
                      <span className="text-[11px] text-gray-400">{visibleOverlayLayers.length.toLocaleString("it-IT")} visibili</span>
                    </div>
                    <div className="h-full max-h-full space-y-2 overflow-y-auto pr-1">
                      {overlayLayers.length === 0 ? (
                        <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 px-3 py-4 text-center text-xs text-gray-400">
                          Nessun layer caricato. Importa uno o piu file Excel oppure aggiungi un layer salvato.
                        </div>
                      ) : (
                        overlayLayers.map((layer) => (
                        <div
                          key={layer.layer_key}
                          className="rounded-2xl border border-gray-200 bg-[linear-gradient(180deg,#ffffff_0%,#fbfcfa_100%)] p-3 shadow-[0_10px_24px_rgba(15,23,42,0.05)]"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="h-3 w-3 rounded-full ring-2 ring-white shadow-sm" style={{ backgroundColor: layer.color }} />
                                <p className="truncate text-sm font-semibold text-gray-800">{layer.name || "Layer senza nome"}</p>
                                <span
                                  className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                                    layer.isPersisted ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
                                  }`}
                                >
                                  {layer.isPersisted ? "Salvato" : "Bozza"}
                                </span>
                              </div>
                              <p className="mt-0.5 truncate text-[11px] text-gray-400">{layer.source_filename ?? "Import manuale"}</p>
                            </div>
                            <label className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-2.5 py-1 text-[11px] font-medium text-gray-600 shadow-sm">
                              <input
                                type="checkbox"
                                checked={layer.visible}
                                onChange={() => updateOverlayLayer(layer.layer_key, (item) => ({ ...item, visible: !item.visible }))}
                                className="h-3.5 w-3.5 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                              />
                              Visibile
                            </label>
                          </div>
                          {layer.importStats ? (
                            <div className="mt-3 grid grid-cols-3 gap-2 text-center text-[11px]">
                              <div className="rounded-xl bg-emerald-50/70 px-2 py-2">
                                <div className="font-semibold text-emerald-700">{layer.importStats.found.toLocaleString("it-IT")}</div>
                                <div className="text-emerald-900/45">trovate</div>
                              </div>
                              <div className="rounded-xl bg-indigo-50/70 px-2 py-2">
                                <div className="font-semibold text-indigo-700">{layer.importStats.withGeometry.toLocaleString("it-IT")}</div>
                                <div className="text-indigo-900/45">in mappa</div>
                              </div>
                              <div className="rounded-xl bg-amber-50/80 px-2 py-2">
                                <div className="font-semibold text-amber-700">
                                  {(layer.importStats.notFound + layer.importStats.multiple + layer.importStats.invalid).toLocaleString("it-IT")}
                                </div>
                                <div className="text-amber-900/45">scarti</div>
                              </div>
                            </div>
                          ) : null}
                          <div className="mt-3 grid grid-cols-[1fr_auto] gap-2">
                            <input
                              value={layer.name}
                              onChange={(e) => updateOverlayLayer(layer.layer_key, (item) => ({ ...item, name: e.target.value }))}
                              placeholder="Nome layer"
                              className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-emerald-300 focus:outline-none focus:ring-2 focus:ring-emerald-100"
                            />
                            <input
                              type="color"
                              value={layer.color}
                              onChange={(e) => updateOverlayLayer(layer.layer_key, (item) => ({ ...item, color: e.target.value.toUpperCase() }))}
                              className="h-10 w-12 cursor-pointer rounded-xl border border-gray-200 bg-white p-1"
                              title="Colore layer"
                            />
                          </div>
                          <div className="mt-3 rounded-xl border border-gray-100 bg-gray-50/70 px-3 py-2">
                            <div className="mb-1.5 flex items-center justify-between text-[11px] text-gray-500">
                              <span className="font-medium text-gray-600">Opacità</span>
                              <span className="rounded-full bg-white px-2 py-0.5 font-semibold text-gray-700 shadow-sm">
                                {Math.round((layer.opacity ?? 0.55) * 100)}%
                              </span>
                            </div>
                            <input
                              type="range"
                              min="5"
                              max="100"
                              step="5"
                              value={Math.round((layer.opacity ?? 0.55) * 100)}
                              onChange={(e) =>
                                updateOverlayLayer(layer.layer_key, (item) => ({
                                  ...item,
                                  opacity: Number(e.target.value) / 100,
                                }))
                              }
                              className="w-full accent-emerald-600"
                            />
                          </div>
                          <div className="mt-3 grid grid-cols-2 gap-2">
                            <button
                              type="button"
                              onClick={() => focusLayerGeojson(layer.geojson)}
                              className="rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-xs font-medium text-gray-700 transition hover:bg-indigo-50 hover:text-indigo-700"
                            >
                              Centra
                            </button>
                            <button
                              type="button"
                              onClick={() => removeOverlayLayer(layer.layer_key)}
                              className="rounded-xl border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-500 transition hover:bg-gray-50 hover:text-gray-700"
                            >
                              Rimuovi dalla mappa
                            </button>
                          </div>
                          <button
                            type="button"
                            onClick={() => void (layer.isPersisted ? handleUpdatePersistedLayer(layer.layer_key) : handleSaveImportedLayer(layer.layer_key))}
                            disabled={savedBusy || (!layer.isPersisted && layer.importedItems.length === 0)}
                            className="mt-3 w-full rounded-xl bg-emerald-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-gray-300"
                          >
                            {layer.isPersisted ? "Aggiorna metadati salvati" : "Salva permanentemente"}
                          </button>
                        </div>
                        ))
                      )}
                    </div>
                  </div>

                  <div className="shrink-0">
                    <div className="mb-2 flex items-center justify-between">
                      <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-400">Archivio layer salvati</p>
                      <button
                        type="button"
                        onClick={() => void refreshSavedSelections()}
                        disabled={savedBusy}
                        className="text-[11px] font-medium text-indigo-600 hover:text-indigo-800 disabled:text-gray-300"
                      >
                        Aggiorna
                      </button>
                    </div>
                    <div className="max-h-44 space-y-2 overflow-y-auto pr-1">
                      {savedSelections.length === 0 ? (
                        <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 px-3 py-4 text-center text-xs text-gray-400">
                          Nessuna selezione salvata.
                        </div>
                      ) : (
                        savedSelections.map((selection) => (
                          <div
                            key={selection.id}
                            className={`rounded-xl border bg-white p-2 shadow-sm ${
                              loadedSavedSelectionIds.has(selection.id) ? "border-emerald-200 ring-1 ring-emerald-100" : "border-gray-100"
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <div className="flex items-center gap-2">
                                  <input
                                    type="color"
                                    value={selection.color}
                                    onChange={(e) => setSavedSelections((ss) => ss.map((s) => s.id === selection.id ? { ...s, color: e.target.value } : s))}
                                    onBlur={(e) => void handleUpdateArchivedSelectionColor(selection.id, e.target.value.toUpperCase())}
                                    className="h-5 w-5 cursor-pointer rounded-full border-0 bg-transparent p-0"
                                    title="Modifica colore"
                                  />
                                  <p className="truncate text-sm font-semibold text-gray-800">{selection.name}</p>
                                </div>
                                <p className="mt-0.5 text-[11px] text-gray-400">
                                  {selection.n_particelle.toLocaleString("it-IT")} particelle · {selection.n_with_geometry.toLocaleString("it-IT")} in mappa
                                </p>
                              </div>
                              <button
                                type="button"
                                onClick={() => void handleDeleteSavedSelection(selection.id)}
                                disabled={savedBusy}
                                className="text-[11px] font-medium text-gray-400 hover:text-red-600 disabled:text-gray-300"
                              >
                                Elimina
                              </button>
                            </div>
                            <div className="mt-2 rounded-lg border border-gray-100 bg-gray-50/70 px-2.5 py-2">
                              <div className="mb-1 flex items-center justify-between text-[11px]">
                                <span className="font-medium text-gray-600">Opacità</span>
                                <span className="font-semibold text-gray-700">
                                  {Math.round((savedSelectionOpacities[selection.id] ?? 0.55) * 100)}%
                                </span>
                              </div>
                              <input
                                type="range"
                                min="5"
                                max="100"
                                step="5"
                                value={Math.round((savedSelectionOpacities[selection.id] ?? 0.55) * 100)}
                                onChange={(e) => handleArchiveOpacityChange(selection.id, Number(e.target.value) / 100)}
                                className="w-full accent-emerald-600"
                              />
                            </div>
                            <div className="mt-2 grid grid-cols-2 gap-2">
                              <button
                                type="button"
                                onClick={() => void handleLoadSavedSelection(selection.id)}
                                disabled={savedBusy}
                                className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs font-medium text-gray-700 transition hover:bg-indigo-50 hover:text-indigo-700 disabled:text-gray-300"
                              >
                                {loadedSavedSelectionIds.has(selection.id) ? "Porta in primo piano" : "Aggiungi in mappa"}
                              </button>
                              <button
                                type="button"
                                onClick={() => {
                                  const loadedLayer = overlayLayers.find((layer) => layer.saved_selection_id === selection.id);
                                  if (loadedLayer) removeOverlayLayer(loadedLayer.layer_key);
                                }}
                                disabled={!loadedSavedSelectionIds.has(selection.id)}
                                className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 disabled:text-gray-300"
                              >
                                Rimuovi
                              </button>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
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
