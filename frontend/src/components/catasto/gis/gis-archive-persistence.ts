import { catastoGisCreateSavedSelection, catastoGisDeleteSavedSelection, catastoGisGetSavedSelection, catastoGisUpdateSavedSelection } from "@/lib/api/catasto";
import type { GisSavedSelectionDetail } from "@/types/gis";
import type { ArchiveOptions, ImportStats, OverlayLayerState } from "./gis-archive-types";

type PersistenceOptions = ArchiveOptions & {
  setSavedBusy: (busy: boolean) => void;
  refreshSavedSelections: () => Promise<void>;
  savedSelectionOpacities: Record<string, number>;
  savedSelectionFills: Record<string, boolean>;
};

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

// Each instance captures the same render snapshot as the original async callbacks.
export class GisArchivePersistence {
  constructor(private readonly options: PersistenceOptions) {}

  handleSaveImportedLayer = async (layerKey: string) => {
    const { token, overlayLayers, setSavedBusy, setGisError, setGisInfo, setOverlayLayers, refreshSavedSelections } = this.options;
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
  };

  handleLoadSavedSelection = async (
    selectionId: string,
    overrides?: { opacity?: number; showFill?: boolean },
  ) => {
    const { token, overlayLayers, updateOverlayLayer, focusLayerGeojson, setGisInfo, setGisError, setSavedBusy, savedSelectionOpacities, savedSelectionFills, setOverlayLayers } = this.options;
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
  };

  handleUpdatePersistedLayer = async (layerKey: string) => {
    const { token, overlayLayers, setSavedBusy, setGisError, setGisInfo, setOverlayLayers, refreshSavedSelections } = this.options;
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
  };

  handleDeleteSavedSelection = async (selectionId: string) => {
    const { token, setSavedBusy, setGisError, setGisInfo, setOverlayLayers, refreshSavedSelections } = this.options;
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
  };

  handleUpdateArchivedSelectionColor = async (selectionId: string, color: string) => {
    const { token, setOverlayLayers, setGisError } = this.options;
    if (!token) return;
    try {
      await catastoGisUpdateSavedSelection(token, selectionId, { color });
      setOverlayLayers((layers) => layers.map((l) => l.saved_selection_id === selectionId ? { ...l, color } : l));
    } catch (e) {
      setGisError(e instanceof Error ? e.message : "Aggiornamento colore fallito");
    }
  };
}
