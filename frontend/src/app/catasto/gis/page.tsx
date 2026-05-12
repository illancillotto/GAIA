"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as XLSX from "xlsx";

import AnalysisPanel from "@/components/catasto/gis/AnalysisPanel";
import { ParticellaDetailDialog } from "@/components/catasto/anagrafica/ParticellaDetailDialog";
import DrawingTools from "@/components/catasto/gis/DrawingTools";
import SelectionPanel from "@/components/catasto/gis/SelectionPanel";
import { CatastoPage } from "@/components/catasto/catasto-page";
import {
  catastoGetDistrettoGeojson,
  catastoGisCreateSavedSelection,
  catastoGisDeleteSavedSelection,
  catastoGisExport,
  catastoGisGetSavedSelection,
  catastoGisListSavedSelections,
  catastoGisResolveRefs,
  catastoGisUpdateSavedSelection,
  catastoListDistretti,
} from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import { useGisSelection } from "@/hooks/useGisSelection";
import type { CatAnagraficaMatch, CatDistretto } from "@/types/catasto";
import type {
  GisBasemap,
  GisFilters,
  GisMapOverlayLayer,
  GisParticellaRef,
  ParticellaPopupData,
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
const DISTRETTO_COLORS = [
  "#2E7D32",
  "#1565C0",
  "#EF6C00",
  "#6A1B9A",
  "#00838F",
  "#C2185B",
  "#9E9D24",
  "#5D4037",
  "#1976D2",
  "#F9A825",
  "#455A64",
  "#AD1457",
];
const GOOGLE_MAP_TILES_CONFIGURED = Boolean(process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY?.trim());
const BASEMAP_OPTIONS: Array<{ id: GisBasemap; label: string; swatch: string; requiresGoogleKey?: boolean }> = [
  { id: "osm", label: "Mappa", swatch: "bg-slate-500" },
  { id: "satellite", label: "Satellite", swatch: "bg-cyan-600" },
  { id: "google_satellite", label: "Google Earth", swatch: "bg-lime-600", requiresGoogleKey: true },
];

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

function compareDistrettoNumber(a: CatDistretto, b: CatDistretto): number {
  const aNumber = Number.parseInt(a.num_distretto, 10);
  const bNumber = Number.parseInt(b.num_distretto, 10);
  if (Number.isFinite(aNumber) && Number.isFinite(bNumber) && aNumber !== bNumber) return aNumber - bNumber;
  return a.num_distretto.localeCompare(b.num_distretto, "it", { numeric: true, sensitivity: "base" });
}

function popupToMatch(popup: ParticellaPopupData | null): CatAnagraficaMatch | null {
  if (!popup) return null;
  return {
    particella_id: popup.id,
    unit_id: null,
    comune_id: null,
    comune: popup.nome_comune ?? null,
    cod_comune_capacitas: popup.cod_comune_capacitas ?? null,
    codice_catastale: popup.codice_catastale ?? null,
    foglio: popup.foglio ?? "",
    particella: popup.particella ?? "",
    subalterno: popup.subalterno ?? null,
    num_distretto: popup.num_distretto ?? null,
    nome_distretto: popup.nome_distretto ?? null,
    superficie_mq: popup.superficie_mq != null ? String(popup.superficie_mq) : null,
    superficie_grafica_mq: popup.superficie_grafica_mq != null ? String(popup.superficie_grafica_mq) : null,
    presente_in_catasto_consorzio: false,
    utenza_latest: null,
    cert_com: null,
    cert_pvc: null,
    cert_fra: null,
    cert_ccs: null,
    stato_ruolo: popup.ha_ruolo ? "a_ruolo" : null,
    stato_cnc: null,
    intestatari: [],
    anomalie_count: popup.n_anomalie_aperte ?? 0,
    anomalie_top: [],
    note: null,
  };
}

function formatHectares(value: number | null | undefined): string {
  if (value == null) return "-";
  return `${value.toLocaleString("it-IT", { minimumFractionDigits: 0, maximumFractionDigits: 4 })} ha`;
}

function formatEuro(value: number | null | undefined): string {
  if (value == null) return "-";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}


export default function CatastoGisPage() {
  const [token, setToken] = useState<string | null>(null);
  const [autoSelectionId, setAutoSelectionId] = useState<string | null>(null);
  const [hasDrawing, setHasDrawing] = useState(false);
  const [drawSignal, setDrawSignal] = useState(0);
  const [clearSignal, setClearSignal] = useState(0);
  const [resizeSignal, setResizeSignal] = useState(0);
  const [isExpanded, setIsExpanded] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [gisError, setGisError] = useState<string | null>(null);
  const [gisInfo, setGisInfo] = useState<string | null>(null);
  const [showDistretti, setShowDistretti] = useState(true);
  const [showDistrettiFill, setShowDistrettiFill] = useState(true);
  const [showParticelle, setShowParticelle] = useState(false);
  const [showParticelleFill, setShowParticelleFill] = useState(true);
  const [basemap, setBasemap] = useState<GisBasemap>("osm");
  const [highlightSelected, setHighlightSelected] = useState(true);
  const [distrettiOpacity, setDistrettiOpacity] = useState(0.34);
  const [particelleOpacity, setParticelleOpacity] = useState(0.42);
  const [distrettoLayer, setDistrettoLayer] = useState<string>("");
  const [distretti, setDistretti] = useState<CatDistretto[]>([]);
  const [distrettiOpen, setDistrettiOpen] = useState(true);
  const [distrettiLoading, setDistrettiLoading] = useState(false);
  const [xlsxFile, setXlsxFile] = useState<File | null>(null);
  const [xlsxBusy, setXlsxBusy] = useState(false);
  const [overlayLayers, setOverlayLayers] = useState<OverlayLayerState[]>([]);
  const [savedSelections, setSavedSelections] = useState<GisSavedSelectionSummary[]>([]);
  const [savedSelectionOpacities, setSavedSelectionOpacities] = useState<Record<string, number>>({});
  const [savedSelectionFills, setSavedSelectionFills] = useState<Record<string, boolean>>({});
  const [savedBusy, setSavedBusy] = useState(false);
  const [focusGeojson, setFocusGeojson] = useState<GeoJSON.FeatureCollection | null>(null);
  const [focusSignal, setFocusSignal] = useState(0);
  const [popupParticella, setPopupParticella] = useState<ParticellaPopupData | null>(null);
  const [popupDetailOpen, setPopupDetailOpen] = useState(false);
  const layerCounterRef = useRef(0);
  const activeFilters = useMemo<GisFilters>(() => ({}), []);
  const { result, isLoading, error, runSelection, clearSelection } = useGisSelection(token);
  const loadedSavedSelectionIds = useMemo(
    () => new Set(overlayLayers.filter((layer) => layer.saved_selection_id).map((layer) => layer.saved_selection_id as string)),
    [overlayLayers],
  );
  const loadedSavedSelectionLayerMap = useMemo(
    () =>
      new Map(
        overlayLayers
          .filter((layer) => layer.saved_selection_id)
          .map((layer) => [layer.saved_selection_id as string, layer] as const),
      ),
    [overlayLayers],
  );
  const visibleOverlayLayers = useMemo(() => overlayLayers.filter((layer) => layer.visible), [overlayLayers]);
  const distrettoColorMap = useMemo(
    () =>
      Object.fromEntries(
        [...distretti]
          .sort(compareDistrettoNumber)
          .map((distretto, index) => [
            distretto.num_distretto,
            DISTRETTO_COLORS[index % DISTRETTO_COLORS.length] ?? "#1D4E35",
          ]),
      ),
    [distretti],
  );
  const selectedDistretto = useMemo(
    () => distretti.find((distretto) => distretto.num_distretto === distrettoLayer.trim()) ?? null,
    [distretti, distrettoLayer],
  );
  const autoLoadedSelectionRef = useRef<string | null>(null);
  const popupMatch = useMemo(() => popupToMatch(popupParticella), [popupParticella]);

  useEffect(() => {
    setToken(getStoredAccessToken());
    const params = new URLSearchParams(window.location.search);
    setAutoSelectionId(params.get("selection"));
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
    if (!token) return;
    setDistrettiLoading(true);
    void catastoListDistretti(token)
      .then((items) => setDistretti([...items].sort(compareDistrettoNumber)))
      .catch((e) => {
        setGisError(e instanceof Error ? e.message : "Caricamento distretti fallito");
      })
      .finally(() => setDistrettiLoading(false));
  }, [token]);

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

  const handlePopupParticella = useCallback((particella: ParticellaPopupData | null) => {
    setPopupParticella(particella);
    if (!particella) {
      setPopupDetailOpen(false);
    }
  }, []);

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

  const handleSelectDistretto = useCallback(async (distretto: CatDistretto) => {
    setShowDistretti(true);
    setShowParticelle(false);
    setDistrettoLayer(distretto.num_distretto);
    if (!token) return;
    try {
      const feature = await catastoGetDistrettoGeojson(token, distretto.id);
      setFocusGeojson({
        type: "FeatureCollection",
        features: [feature as GeoJSON.Feature],
      });
      setFocusSignal((value) => value + 1);
      setGisError(null);
    } catch (e) {
      setGisError(e instanceof Error ? e.message : "Impossibile centrare il distretto selezionato");
    }
  }, [token]);

  const handleClearDistretto = useCallback(() => {
    setDistrettoLayer("");
    setShowDistretti(true);
    setResizeSignal((value) => value + 1);
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

      const items: GisParticellaRef[] = rows.slice(0, 5000).map((r: Record<string, unknown>, i: number) => ({
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

  const handleLoadSavedSelection = useCallback(async (
    selectionId: string,
    overrides?: { opacity?: number; showFill?: boolean },
  ) => {
    if (!token) return;

    const existing = overlayLayers.find((layer) => layer.saved_selection_id === selectionId);
    if (existing) {
      updateOverlayLayer(existing.layer_key, (layer) => ({
        ...layer,
        visible: true,
        opacity: overrides?.opacity ?? layer.opacity,
        showFill: overrides?.showFill ?? layer.showFill,
      }));
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
        opacity: overrides?.opacity ?? savedSelectionOpacities[selectionId] ?? 0.55,
        showFill: overrides?.showFill ?? savedSelectionFills[selectionId] ?? true,
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
  }, [focusLayerGeojson, overlayLayers, savedSelectionFills, savedSelectionOpacities, token, updateOverlayLayer]);

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

  const handleArchiveOpacityChange = useCallback(async (selectionId: string, opacity: number) => {
    setSavedSelectionOpacities((prev) => ({ ...prev, [selectionId]: opacity }));
    setOverlayLayers((layers) =>
      layers.map((l) => l.saved_selection_id === selectionId ? { ...l, opacity } : l),
    );
    if (!overlayLayers.some((layer) => layer.saved_selection_id === selectionId)) {
      await handleLoadSavedSelection(selectionId, { opacity });
    }
  }, [handleLoadSavedSelection, overlayLayers]);

  const handleArchiveFillChange = useCallback(async (selectionId: string, showFill: boolean) => {
    setSavedSelectionFills((prev) => ({ ...prev, [selectionId]: showFill }));
    setOverlayLayers((layers) =>
      layers.map((l) => l.saved_selection_id === selectionId ? { ...l, showFill } : l),
    );
    if (!overlayLayers.some((layer) => layer.saved_selection_id === selectionId)) {
      await handleLoadSavedSelection(selectionId, { showFill });
    }
  }, [handleLoadSavedSelection, overlayLayers]);

  useEffect(() => {
    if (!token || !autoSelectionId) return;
    if (autoLoadedSelectionRef.current === autoSelectionId) return;
    autoLoadedSelectionRef.current = autoSelectionId;
    void handleLoadSavedSelection(autoSelectionId).catch((e) => {
      setGisError(e instanceof Error ? e.message : "Caricamento layer da URL fallito");
    });
  }, [autoSelectionId, handleLoadSavedSelection, token]);

  const renderBasemapControl = (isDark: boolean) => (
    <div className={`rounded-2xl border p-3 ${isDark ? "border-white/15 bg-white/10" : "border-gray-100 bg-gray-50"}`}>
      <p className={`mb-2 text-[10px] font-semibold uppercase tracking-widest ${isDark ? "text-white/50" : "text-gray-400"}`}>
        Sfondo mappa
      </p>
      <div className="grid grid-cols-3 gap-1.5">
        {BASEMAP_OPTIONS.map((option) => {
          const disabled = option.requiresGoogleKey && !GOOGLE_MAP_TILES_CONFIGURED;
          const selected = basemap === option.id;
          return (
            <button
              key={option.id}
              type="button"
              onClick={() => {
                if (!disabled) setBasemap(option.id);
              }}
              disabled={disabled}
              title={disabled ? "Configura NEXT_PUBLIC_GOOGLE_MAPS_API_KEY per usare Google Map Tiles." : option.label}
              className={`inline-flex min-w-0 items-center justify-center gap-1.5 rounded-xl border px-2 py-2 text-[11px] font-semibold transition ${
                selected
                  ? "border-emerald-300 bg-white text-emerald-800 shadow-sm ring-1 ring-emerald-100"
                  : isDark
                    ? "border-white/15 bg-white/5 text-white/65 hover:bg-white/10"
                    : "border-gray-200 bg-white text-gray-600 hover:border-gray-300 hover:bg-gray-50"
              } ${disabled ? "cursor-not-allowed opacity-45" : ""}`}
            >
              <span className={`h-2 w-2 shrink-0 rounded-full ${option.swatch}`} />
              <span className="truncate">{option.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );

  const renderDistrettiPanel = (isDark: boolean) => (
    <div className={`rounded-2xl border p-3 ${isDark ? "border-white/15 bg-white/10" : "border-emerald-100 bg-emerald-50/30"}`}>
      <button
        type="button"
        onClick={() => setDistrettiOpen((value) => !value)}
        className="flex w-full items-center justify-between gap-3 text-left"
      >
        <div>
          <p className={`text-[10px] font-semibold uppercase tracking-widest ${isDark ? "text-emerald-200" : "text-emerald-700"}`}>Distretti irrigui</p>
          <p className={`mt-1 text-xs ${isDark ? "text-white/60" : "text-gray-500"}`}>
            {selectedDistretto
              ? `Filtro attivo: distretto ${selectedDistretto.num_distretto}`
              : "Seleziona un distretto per centrare la mappa e isolare il perimetro."}
          </p>
        </div>
        <span className={`material-symbols-outlined text-[20px] transition ${distrettiOpen ? "rotate-180" : ""} ${isDark ? "text-white/60" : "text-emerald-700"}`}>
          expand_more
        </span>
      </button>

      {selectedDistretto ? (
        <div className={`mt-3 rounded-xl border px-3 py-2 ${isDark ? "border-white/15 bg-white/10" : "border-white bg-white/80"}`}>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span
                  className="h-3 w-3 shrink-0 rounded-full ring-2 ring-white"
                  style={{ backgroundColor: distrettoColorMap[selectedDistretto.num_distretto] ?? "#1D4E35" }}
                />
                <p className={`truncate text-sm font-semibold ${isDark ? "text-white" : "text-gray-900"}`}>
                  Distretto {selectedDistretto.num_distretto}
                </p>
              </div>
              <p className={`mt-0.5 truncate text-[11px] ${isDark ? "text-white/55" : "text-gray-500"}`}>
                {selectedDistretto.nome_distretto ?? "Senza nome"}
              </p>
            </div>
            <button
              type="button"
              onClick={handleClearDistretto}
              className={`rounded-full px-2.5 py-1 text-[11px] font-semibold transition ${isDark ? "bg-white/10 text-white/70 hover:bg-white/15" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
            >
              Tutti
            </button>
          </div>
          <button
            type="button"
            onClick={() => setShowParticelle((value) => !value)}
            className={`mt-2 w-full rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${
              showParticelle
                ? "border-indigo-200 bg-indigo-50 text-indigo-700"
                : isDark
                  ? "border-white/15 bg-white/10 text-white/70 hover:bg-white/15"
                  : "border-gray-200 bg-white text-gray-600 hover:bg-gray-50"
            }`}
          >
            {showParticelle ? "Nascondi particelle del distretto" : "Mostra particelle del distretto"}
          </button>
        </div>
      ) : null}

      {distrettiOpen ? (
        <div className="mt-3 max-h-56 space-y-1.5 overflow-y-auto pr-1">
          {distrettiLoading ? (
            <div className={`rounded-xl border border-dashed px-3 py-4 text-center text-xs ${isDark ? "border-white/15 text-white/50" : "border-emerald-100 text-gray-500"}`}>
              Caricamento distretti...
            </div>
          ) : distretti.length === 0 ? (
            <div className={`rounded-xl border border-dashed px-3 py-4 text-center text-xs ${isDark ? "border-white/15 text-white/50" : "border-emerald-100 text-gray-500"}`}>
              Nessun distretto disponibile.
            </div>
          ) : (
            distretti.map((distretto) => {
              const isSelected = distretto.num_distretto === distrettoLayer.trim();
              const color = distrettoColorMap[distretto.num_distretto] ?? "#1D4E35";
              return (
                <button
                  key={distretto.id}
                  type="button"
                  onClick={() => void handleSelectDistretto(distretto)}
                  className={`flex w-full items-center gap-2 rounded-xl border px-3 py-2 text-left transition ${
                    isSelected
                      ? "border-emerald-300 bg-white shadow-sm ring-1 ring-emerald-100"
                      : isDark
                        ? "border-white/10 bg-white/5 hover:bg-white/10"
                        : "border-white/70 bg-white/70 hover:border-emerald-200 hover:bg-white"
                  }`}
                >
                  <span className="h-3 w-3 shrink-0 rounded-full ring-2 ring-white" style={{ backgroundColor: color }} />
                  <span className="min-w-0 flex-1">
                    <span className={`block truncate text-xs font-semibold ${isDark ? "text-white" : "text-gray-900"}`}>
                      Distretto {distretto.num_distretto}
                    </span>
                    <span className={`block truncate text-[10px] ${isDark ? "text-white/45" : "text-gray-500"}`}>
                      {distretto.nome_distretto ?? "Senza nome"}
                    </span>
                  </span>
                  {isSelected ? (
                    <span className="material-symbols-outlined text-[16px] text-emerald-600">check_circle</span>
                  ) : null}
                </button>
              );
            })
          )}
        </div>
      ) : null}
    </div>
  );

  const renderArchivioList = (isDark: boolean) => (
    <>
      <div className="mb-2 flex items-center justify-between">
        <p className={`text-[10px] font-semibold uppercase tracking-widest ${isDark ? "text-white/50" : "text-gray-400"}`}>Archivio layer salvati</p>
        <button
          type="button"
          onClick={() => void refreshSavedSelections()}
          disabled={savedBusy}
          className={`text-[11px] font-medium ${isDark ? "text-indigo-300 hover:text-indigo-200" : "text-indigo-600 hover:text-indigo-800"} disabled:opacity-50`}
        >
          Aggiorna
        </button>
      </div>
      <div className="max-h-44 space-y-2 overflow-y-auto pr-1">
        {savedSelections.length === 0 ? (
          <div className={`rounded-xl border border-dashed px-3 py-4 text-center text-xs ${isDark ? "border-white/20 bg-white/5 text-white/50" : "border-gray-200 bg-gray-50 text-gray-400"}`}>
            Nessuna selezione salvata.
          </div>
        ) : (
          savedSelections.map((selection) => {
            const loadedLayer = loadedSavedSelectionLayerMap.get(selection.id);
            const effectiveShowFill = loadedLayer?.showFill ?? savedSelectionFills[selection.id] ?? true;
            const effectiveOpacity = loadedLayer?.opacity ?? savedSelectionOpacities[selection.id] ?? 0.55;

            return (
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
                  <button
                    type="button"
                    onClick={() => handleArchiveFillChange(selection.id, !effectiveShowFill)}
                    className={`mb-2 inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-medium transition-all ${
                      effectiveShowFill
                        ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                        : "border-gray-200 bg-white text-gray-500 hover:border-emerald-100 hover:text-emerald-700"
                    }`}
                  >
                    <span className={`h-1.5 w-1.5 rounded-full transition-colors ${effectiveShowFill ? "bg-emerald-400" : "bg-gray-300"}`} />
                    Riempimento
                  </button>
                  <div className="mb-1 flex items-center justify-between text-[11px]">
                    <span className="font-medium text-gray-600">Opacità</span>
                    <span className="font-semibold text-gray-700">
                      {Math.round(effectiveOpacity * 100)}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="5"
                    max="100"
                    step="5"
                    value={Math.round(effectiveOpacity * 100)}
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
            );
          })
        )}
      </div>
    </>
  );

  return (
    <CatastoPage
      title="GIS"
      description="Analisi spaziale delle particelle catastali con layer MVT e selezione GIS."
      breadcrumb="Catasto / GIS"
      requiredModule="catasto"
      hideContentHeader
    >
      <div className="relative -mx-7 -mb-6 -mt-6 flex h-[calc(100vh-72px)] min-h-[760px] flex-col overflow-hidden border-y border-slate-200 bg-[#101b17] shadow-[0_24px_80px_rgba(15,23,42,0.18)]">
        <div className="absolute left-4 top-4 z-20 flex max-w-[calc(100%-2rem)] flex-col gap-3 lg:left-6 lg:right-[452px] lg:max-w-none lg:flex-row lg:items-start lg:justify-between">
          <div className="flex min-w-0 items-center gap-3 rounded-2xl border border-white/20 bg-white/95 px-3 py-2 shadow-2xl backdrop-blur">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#1D4E35] text-white shadow-sm">
              <span className="material-symbols-outlined text-[22px]">map</span>
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h2 className="truncate text-sm font-bold uppercase tracking-[0.18em] text-slate-950">GAIA GIS</h2>
                <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                  Catasto
                </span>
              </div>
              <p className="truncate text-xs text-slate-500">
                Distretti, particelle, selezioni e layer importati nel comprensorio consortile.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-white/20 bg-white/95 p-2 shadow-2xl backdrop-blur">
            <button
              type="button"
              onClick={openExpanded}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-slate-950 px-3 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <span className="material-symbols-outlined text-[16px]">open_in_full</span>
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
          <div className="absolute left-4 right-4 top-[118px] z-20 rounded-xl border border-red-200 bg-red-50/95 px-3 py-2 text-sm font-medium text-red-700 shadow-xl backdrop-blur lg:right-[452px]">
            {error || exportError || gisError}
          </div>
        ) : gisInfo ? (
          <div className="absolute left-4 right-4 top-[118px] z-20 rounded-xl border border-amber-200 bg-amber-50/95 px-3 py-2 text-sm font-medium text-amber-700 shadow-xl backdrop-blur lg:right-[452px]">
            {gisInfo}
          </div>
        ) : null}

        <div className={`grid min-h-0 flex-1 overflow-hidden ${isExpanded ? "lg:grid-cols-1" : "grid-rows-[minmax(0,1fr)_minmax(360px,45vh)] lg:grid-cols-[minmax(0,1fr)_432px] lg:grid-rows-none"}`}>
          <div
            className={
              isExpanded
                ? "fixed inset-0 z-50 flex flex-col"
                : "h-full bg-[#101b17]"
            }
          >
            {isExpanded ? (
              <div className="absolute inset-0 bg-black/50" onClick={closeExpanded} />
            ) : null}

            {isExpanded ? (
              <div className="relative flex items-center justify-between gap-3 border-b border-gray-200 bg-white/95 px-4 py-2 text-gray-900 backdrop-blur">
                <div>
                  <div className="text-sm font-semibold">Vista estesa GIS</div>
                  <div className="text-[11px] text-gray-500">Premi Esc per uscire</div>
                </div>
                <button
                  type="button"
                  onClick={closeExpanded}
                  className="inline-flex items-center justify-center rounded-full border border-gray-200 bg-gray-50 px-3.5 py-1.5 text-sm font-semibold text-gray-700 transition hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-200"
                >
                  Chiudi
                </button>
              </div>
            ) : null}

            <div className={isExpanded ? "relative pointer-events-none flex min-h-0 flex-1 gap-3 p-3" : "h-full"}>
              <div
                className={
                  isExpanded
                    ? "pointer-events-auto relative min-h-0 flex-1 overflow-hidden rounded-2xl bg-white shadow-2xl ring-1 ring-black/5"
                    : "relative h-full"
                }
              >
                <MapContainer
                  token={token}
                  onGeometryDrawn={handleGeometryDrawn}
                  onSelectionCleared={handleClearSelection}
                  onParticellaClick={handlePopupParticella}
                  selectedIds={result?.particelle.map((particella) => particella.id) ?? []}
                  filters={activeFilters}
                  mapLayers={{
                    showDistretti,
                    showDistrettiFill,
                    showParticelle,
                    showParticelleFill,
                    distrettiOpacity,
                    particelleOpacity,
                    distretto: distrettoLayer.trim() ? distrettoLayer.trim() : null,
                    highlightSelected,
                    distrettoColors: distrettoColorMap,
                  }}
                  overlayLayers={visibleOverlayLayers}
                  focusGeojson={focusGeojson}
                  focusSignal={focusSignal}
                  drawSignal={drawSignal}
                  clearSignal={clearSignal}
                  resizeSignal={resizeSignal}
                  basemap={basemap}
                  className={isExpanded ? "min-h-0 h-full rounded-2xl" : "min-h-0 rounded-none"}
                />
                {popupParticella ? (
                  <div className="pointer-events-none absolute inset-x-3 bottom-3 z-10 sm:inset-x-auto sm:bottom-4 sm:left-4 sm:top-24 sm:w-[380px]">
                    <div className="pointer-events-auto rounded-2xl border border-slate-200 bg-white/96 p-4 shadow-2xl ring-1 ring-black/5 backdrop-blur">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="truncate text-sm font-bold text-slate-900">
                              {popupParticella.cfm || `${popupParticella.foglio ?? "-"} / ${popupParticella.particella ?? "-"}`}
                            </p>
                            <span
                              className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                                popupParticella.ha_ruolo ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600"
                              }`}
                            >
                              {popupParticella.ha_ruolo ? "A ruolo" : "Fuori ruolo"}
                            </span>
                            {popupParticella.n_anomalie_aperte > 0 ? (
                              <span className="rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-semibold text-red-700">
                                {popupParticella.n_anomalie_aperte} anomalie
                              </span>
                            ) : null}
                          </div>
                          <p className="mt-1 text-xs text-slate-500">
                            {popupParticella.nome_comune ?? popupParticella.codice_catastale ?? "Comune ND"} · Fg. {popupParticella.foglio ?? "-"} · Part. {popupParticella.particella ?? "-"}
                            {popupParticella.subalterno ? ` · Sub. ${popupParticella.subalterno}` : ""}
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => setPopupParticella(null)}
                          className="rounded-full border border-slate-200 bg-slate-50 p-1.5 text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
                          aria-label="Chiudi dettaglio particella GIS"
                        >
                          <span className="material-symbols-outlined text-[16px]">close</span>
                        </button>
                      </div>

                      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                        <div className="rounded-xl bg-slate-50 px-3 py-2">
                          <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">Superficie</div>
                          <div className="mt-1 font-semibold text-slate-800">
                            {(popupParticella.superficie_mq ?? popupParticella.superficie_grafica_mq)?.toLocaleString("it-IT") ?? "-"} mq
                          </div>
                        </div>
                        <div className="rounded-xl bg-slate-50 px-3 py-2">
                          <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">Distretto</div>
                          <div className="mt-1 font-semibold text-slate-800">
                            {popupParticella.num_distretto ?? "-"}
                            {popupParticella.nome_distretto ? ` · ${popupParticella.nome_distretto}` : ""}
                          </div>
                        </div>
                      </div>

                      <div className="mt-3 rounded-2xl border border-sky-100 bg-sky-50/70 px-3 py-3">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="text-[10px] font-semibold uppercase tracking-widest text-sky-700">
                              Titolare
                            </div>
                            {popupParticella.titolare ? (
                              <>
                                <div className="mt-1 truncate text-sm font-semibold text-slate-900">
                                  {popupParticella.titolare.denominazione ?? "Nominativo non disponibile"}
                                </div>
                                <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-slate-600">
                                  {popupParticella.titolare.codice_fiscale ? (
                                    <span>
                                      CF <span className="font-mono font-semibold text-slate-800">{popupParticella.titolare.codice_fiscale}</span>
                                    </span>
                                  ) : null}
                                  {!popupParticella.titolare.codice_fiscale && popupParticella.titolare.partita_iva ? (
                                    <span>
                                      P.IVA <span className="font-mono font-semibold text-slate-800">{popupParticella.titolare.partita_iva}</span>
                                    </span>
                                  ) : null}
                                  {popupParticella.titolare.titoli ? <span>{popupParticella.titolare.titoli}</span> : null}
                                </div>
                              </>
                            ) : (
                              <div className="mt-1 text-xs font-medium text-slate-500">
                                Nessun titolare collegato alla particella.
                              </div>
                            )}
                          </div>
                          {popupParticella.titolare ? (
                            <span className="shrink-0 rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-semibold text-sky-700">
                              {popupParticella.titolare.source === "intestatario" ? "Intestatario" : "Utenza"}
                            </span>
                          ) : null}
                        </div>
                      </div>

                      {popupParticella.ruolo_summary ? (
                        <div className="mt-3 rounded-2xl border border-emerald-100 bg-emerald-50/60 p-3">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div>
                              <div className="text-[10px] font-semibold uppercase tracking-widest text-emerald-700">Ruolo</div>
                              <div className="mt-1 text-xs font-semibold text-emerald-900">
                                {popupParticella.ruolo_summary.n_righe} quote · {popupParticella.ruolo_summary.n_subalterni} sub · anno {popupParticella.ruolo_summary.anno_tributario_latest}
                              </div>
                              {popupParticella.ruolo_summary.anno_tributario_richiesto &&
                              popupParticella.ruolo_summary.anno_tributario_richiesto !== popupParticella.ruolo_summary.anno_tributario_latest ? (
                                <div className="mt-0.5 text-[11px] font-medium text-emerald-700">
                                  Ultimo ruolo disponibile per l&apos;anno richiesto {popupParticella.ruolo_summary.anno_tributario_richiesto}
                                </div>
                              ) : null}
                            </div>
                            <div className="text-right text-[11px] text-emerald-900">
                              <div>{formatHectares(popupParticella.ruolo_summary.sup_irrigata_ha_totale)} irrigati</div>
                              <div>{formatEuro(popupParticella.ruolo_summary.importo_totale_euro)}</div>
                            </div>
                          </div>
                          <div className="mt-3 grid grid-cols-3 gap-1.5 text-[11px] text-emerald-950">
                            <div className="rounded-lg bg-white/75 px-2 py-1.5">
                              <div className="text-[9px] font-semibold uppercase tracking-widest text-emerald-600">Manut.</div>
                              <div className="mt-0.5 font-semibold">{formatEuro(popupParticella.ruolo_summary.importo_manut_euro_totale)}</div>
                            </div>
                            <div className="rounded-lg bg-white/75 px-2 py-1.5">
                              <div className="text-[9px] font-semibold uppercase tracking-widest text-emerald-600">Irrig.</div>
                              <div className="mt-0.5 font-semibold">{formatEuro(popupParticella.ruolo_summary.importo_irrig_euro_totale)}</div>
                            </div>
                            <div className="rounded-lg bg-white/75 px-2 py-1.5">
                              <div className="text-[9px] font-semibold uppercase tracking-widest text-emerald-600">Istr.</div>
                              <div className="mt-0.5 font-semibold">{formatEuro(popupParticella.ruolo_summary.importo_ist_euro_totale)}</div>
                            </div>
                          </div>
                          <div className="mt-3 max-h-44 space-y-2 overflow-y-auto pr-1">
                            {popupParticella.ruolo_summary.items.map((item, index) => (
                              <div key={`${item.anno_tributario}-${item.subalterno ?? "sub"}-${item.codice_partita ?? index}`} className="rounded-xl border border-emerald-100 bg-white/90 px-3 py-2 text-xs">
                                <div className="flex items-center justify-between gap-2">
                                  <div className="font-semibold text-slate-800">
                                    {item.subalterno ? `Sub ${item.subalterno}` : "Sub ND"}
                                    {item.coltura ? ` · ${item.coltura}` : ""}
                                  </div>
                                  <div className="text-[11px] font-medium text-slate-500">Anno {item.anno_tributario}</div>
                                </div>
                                <div className="mt-1 text-[11px] text-slate-500">
                                  {item.domanda_irrigua ? `Domanda ${item.domanda_irrigua}` : "Domanda ND"}
                                  {item.codice_partita ? ` · Partita ${item.codice_partita}` : ""}
                                </div>
                                <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-slate-700">
                                  <span>Irrigata: {formatHectares(item.sup_irrigata_ha)}</span>
                                  <span>Catastale: {formatHectares(item.sup_catastale_ha)}</span>
                                  <span>Manut.: {formatEuro(item.importo_manut_euro)}</span>
                                  <span>Irrig.: {formatEuro(item.importo_irrig_euro)}</span>
                                  <span>Istr.: {formatEuro(item.importo_ist_euro)}</span>
                                  <span>Totale: {formatEuro(item.importo_totale_euro)}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : null}

                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => setPopupDetailOpen(true)}
                          className="inline-flex items-center justify-center rounded-xl bg-slate-950 px-3 py-2 text-xs font-semibold text-white transition hover:bg-slate-800"
                        >
                          Apri dettaglio particella
                        </button>
                        <a
                          href={`/catasto/particelle/${popupParticella.id}`}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
                        >
                          Apri in pagina
                        </a>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
              {isExpanded ? (
                <aside className="pointer-events-auto hidden w-[340px] shrink-0 overflow-y-auto rounded-2xl border border-gray-200 bg-white/95 p-4 text-gray-900 shadow-2xl ring-1 ring-black/5 lg:block backdrop-blur">
                  <div className="flex flex-col gap-4">
                    <div className="rounded-2xl border border-gray-100 bg-gray-50 p-3">
                      <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-gray-400">Disegna area</p>
                      <DrawingTools
                        onDrawPolygon={() => setDrawSignal((value) => value + 1)}
                        onClearDrawing={handleClearSelection}
                        isLoading={isLoading}
                        hasSelection={hasDrawing}
                        nParticelle={result?.n_particelle}
                        orientation="vertical"
                      />
                      {hasDrawing && result?.particelle && result.particelle.length > 0 && (
                        <div className="mt-4 border-t border-gray-200 pt-3">
                          <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-gray-500">
                            Particelle Selezionate ({result.particelle.length})
                          </p>
                          <div className="max-h-48 space-y-1.5 overflow-y-auto pr-1">
                            {result.particelle.map((p) => (
                              <div key={p.id} className="flex items-center justify-between rounded-xl border border-gray-200 bg-white px-3 py-2 shadow-sm transition hover:border-indigo-200">
                                <div className="min-w-0">
                                  <p className="truncate text-xs font-bold text-gray-800">
                                    {p.nome_comune || "Comune ignoto"}
                                  </p>
                                  <p className="truncate text-[10px] font-medium text-gray-500">
                                    Fg. <span className="text-indigo-600">{p.foglio || "-"}</span> · Part. <span className="text-indigo-600">{p.particella || "-"}</span>
                                    {p.subalterno ? ` · Sub. ${p.subalterno}` : ""}
                                  </p>
                                </div>
                                <div className="shrink-0 text-right">
                                  {p.superficie_mq ? (
                                    <p className="text-[11px] font-bold text-emerald-600">{p.superficie_mq.toLocaleString("it-IT")} mq</p>
                                  ) : p.superficie_grafica_mq ? (
                                    <p className="text-[11px] font-bold text-emerald-600">{p.superficie_grafica_mq.toLocaleString("it-IT")} mq</p>
                                  ) : (
                                    <p className="text-[10px] text-gray-400">Area ND</p>
                                  )}
                                  {p.ha_anomalie && (
                                    <span className="mt-0.5 inline-block rounded-full bg-amber-100 px-1.5 py-0.5 text-[8px] font-bold text-amber-700">
                                      ANOMALIE
                                    </span>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                    {renderBasemapControl(false)}
                    <div>
                      <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-gray-400">Layer visibili</p>
                      <div className="flex flex-wrap gap-1.5">
                        <div className="group relative">
                          <button
                            type="button"
                            onClick={() => setShowDistretti((v) => !v)}
                            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-all ${
                              showDistretti
                                ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                                : "border-gray-200 bg-white text-gray-400 hover:border-gray-300 hover:text-gray-600"
                            }`}
                          >
                            <span className={`h-1.5 w-1.5 rounded-full transition-colors ${showDistretti ? "bg-emerald-500" : "bg-gray-300"}`} />
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
                              Aree colorate
                            </button>
                            <div className="flex items-center justify-between text-[11px]">
                              <span className="font-medium text-emerald-900/75">Opacità aree distretto</span>
                              <span className="rounded-full bg-emerald-50 px-2 py-0.5 font-semibold text-emerald-700">
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
                              className="mt-2 w-full accent-emerald-600"
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
                            <button
                              type="button"
                              onClick={() => setShowParticelleFill((v) => !v)}
                              className={`mb-3 inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-medium transition-all ${
                                showParticelleFill
                                  ? "border-violet-200 bg-violet-50 text-violet-700"
                                  : "border-gray-200 bg-white text-gray-500 hover:border-violet-100 hover:text-violet-700"
                              }`}
                            >
                              <span className={`h-1.5 w-1.5 rounded-full transition-colors ${showParticelleFill ? "bg-violet-400" : "bg-gray-300"}`} />
                              Riempimento
                            </button>
                            <div className="flex items-center justify-between text-[11px]">
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
                    {renderDistrettiPanel(false)}
                    <div className="rounded-2xl border border-gray-100 bg-gray-50 p-3">
                      {renderArchivioList(false)}
                    </div>
                    <div className="rounded-2xl border border-gray-100 bg-gray-50 px-3 py-3 text-xs text-gray-500">
                      Il layout esteso usa una sidebar destra per lasciare più altezza utile al comprensorio in mappa e raccogliere i controlli operativi fuori dall&apos;header.
                    </div>
                  </div>
                </aside>
              ) : null}
            </div>
          </div>

          {!isExpanded ? (
            <aside className="z-10 flex h-full min-h-0 flex-col overflow-hidden border-t border-slate-200 bg-white/95 shadow-[-18px_0_50px_rgba(15,23,42,0.18)] backdrop-blur lg:border-l lg:border-t-0">

              {/* ── Controls ── */}
              <div className="shrink-0 border-b border-slate-200 bg-[linear-gradient(180deg,#ffffff_0%,#f8faf7_100%)] px-4 py-4">
                <div className="mb-4 flex items-start justify-between gap-3">
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-emerald-700">Console GIS</p>
                    <h3 className="mt-1 text-base font-semibold text-slate-950">Layer e strumenti</h3>
                    <p className="mt-1 text-xs leading-5 text-slate-500">Pannello operativo persistente, ispirato ai GIS web: layer, import, archivio e risultati restano sempre a destra.</p>
                  </div>
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                    Online
                  </span>
                </div>

                {/* Layer toggles */}
                <div className="flex flex-col gap-4">
                  {renderBasemapControl(false)}
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-gray-400">Layer visibili</p>
                  <div className="flex flex-wrap gap-1.5">
                    <div className="group relative">
                      <button
                        type="button"
                        onClick={() => setShowDistretti((v) => !v)}
                        className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-all ${
                          showDistretti
                            ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                            : "border-gray-200 bg-white text-gray-400 hover:border-gray-300 hover:text-gray-600"
                        }`}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full transition-colors ${showDistretti ? "bg-emerald-500" : "bg-gray-300"}`} />
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
                          Aree colorate
                        </button>
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-medium text-emerald-900/75">Opacità aree distretto</span>
                          <span className="rounded-full bg-emerald-50 px-2 py-0.5 font-semibold text-emerald-700">
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
                          className="mt-2 w-full accent-emerald-600"
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
                        <button
                          type="button"
                          onClick={() => setShowParticelleFill((v) => !v)}
                          className={`mb-3 inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-medium transition-all ${
                            showParticelleFill
                              ? "border-violet-200 bg-violet-50 text-violet-700"
                              : "border-gray-200 bg-white text-gray-500 hover:border-violet-100 hover:text-violet-700"
                          }`}
                        >
                          <span className={`h-1.5 w-1.5 rounded-full transition-colors ${showParticelleFill ? "bg-violet-400" : "bg-gray-300"}`} />
                          Riempimento
                        </button>
                        <div className="flex items-center justify-between text-[11px]">
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

                {renderDistrettiPanel(false)}

                {/* Excel import */}
                <div className="rounded-2xl border border-emerald-100 bg-emerald-50/30 p-2.5">
                  <div className="mb-1.5 flex items-center justify-between gap-2">
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-emerald-700">Import da Excel</p>
                    <span className="text-[11px] text-gray-500">{overlayLayers.length.toLocaleString("it-IT")} layer in workspace</span>
                  </div>
                  <label
                    className={`group flex cursor-pointer flex-col items-center gap-1.5 rounded-xl border-2 border-dashed px-4 py-3.5 text-center transition-all ${
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
                        <svg className="h-6 w-6 animate-spin text-emerald-500" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        <span className="text-sm font-medium text-emerald-600">Caricamento…</span>
                      </>
                    ) : xlsxFile ? (
                      <>
                        <svg className="h-6 w-6 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                        </svg>
                        <span className="max-w-full truncate text-sm font-semibold text-emerald-700">{xlsxFile.name}</span>
                        <span className="text-[11px] text-emerald-500">Clicca per cambiare file</span>
                      </>
                    ) : (
                      <>
                        <svg className="h-6 w-6 text-gray-400 transition group-hover:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                        </svg>
                        <span className="text-sm font-medium text-gray-600 transition group-hover:text-indigo-600">Clicca per selezionare</span>
                        <span className="text-[11px] text-gray-400">.xlsx · .xls · max 5 000 righe</span>
                      </>
                    )}
                  </label>
                  <p className="mt-1.5 text-[10px] leading-4 text-gray-500">
                    Colonne attese: <span className="font-medium">comune</span>, <span className="font-medium">sezione</span>, <span className="font-medium">foglio</span>, <span className="font-medium">particella</span>, <span className="font-medium">sub</span>. Nel campo{" "}
                    <span className="font-medium">comune</span> puoi usare nome comune, codice Capacitas numerico oppure codice catastale/Belfiore.
                  </p>
                </div>
              </div>

              <div className="min-h-0 flex-1 overflow-hidden px-4 pt-4">
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
                            <button
                              type="button"
                              onClick={() => updateOverlayLayer(layer.layer_key, (item) => ({ ...item, showFill: !(item.showFill ?? true) }))}
                              className={`mb-2.5 inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-medium transition-all ${
                                (layer.showFill ?? true)
                                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                                  : "border-gray-200 bg-white text-gray-500 hover:border-emerald-100 hover:text-emerald-700"
                              }`}
                            >
                              <span className={`h-1.5 w-1.5 rounded-full transition-colors ${(layer.showFill ?? true) ? "bg-emerald-400" : "bg-gray-300"}`} />
                              Riempimento
                            </button>
                            <div className="flex items-center justify-between text-[11px] text-gray-500">
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
                    {renderArchivioList(false)}
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
      <ParticellaDetailDialog open={popupDetailOpen} match={popupMatch} onClose={() => setPopupDetailOpen(false)} />
    </CatastoPage>
  );
}
