"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { catastoGisListSavedSelections } from "@/lib/api/catasto";
import type { GisSavedSelectionSummary } from "@/types/gis";
import type { ArchiveOptions } from "./gis-archive-types";
import { GisArchivePersistence } from "./gis-archive-persistence";
export type { ImportStats, OverlayLayerState } from "./gis-archive-types";

function useArchiveCatalog(token: ArchiveOptions["token"], setGisError: ArchiveOptions["setGisError"]) {
  const [savedSelections, setSavedSelections] = useState<GisSavedSelectionSummary[]>([]);
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
  }, [refreshSavedSelections, setGisError, token]);
  return { savedSelections, setSavedSelections, refreshSavedSelections };
}

function useArchiveAutoload(token: ArchiveOptions["token"], autoSelectionId: string | null, handleLoadSavedSelection: GisArchivePersistence["handleLoadSavedSelection"], setGisError: ArchiveOptions["setGisError"]) {
  const autoLoadedSelectionRef = useRef<string | null>(null);
  useEffect(() => {
    if (!token || !autoSelectionId) return;
    if (autoLoadedSelectionRef.current === autoSelectionId) return;
    autoLoadedSelectionRef.current = autoSelectionId;
    void handleLoadSavedSelection(autoSelectionId).catch((e) => {
      setGisError(e instanceof Error ? e.message : "Caricamento layer da URL fallito");
    });
  }, [autoSelectionId, handleLoadSavedSelection, setGisError, token]);
}

export function useGisArchive(options: ArchiveOptions) {
  const { token, autoSelectionId, overlayLayers, setOverlayLayers, setGisError } = options;
  const [savedSelectionOpacities, setSavedSelectionOpacities] = useState<Record<string, number>>({});
  const [savedSelectionFills, setSavedSelectionFills] = useState<Record<string, boolean>>({});
  const [savedBusy, setSavedBusy] = useState(false);
  const { savedSelections, setSavedSelections, refreshSavedSelections } = useArchiveCatalog(token, setGisError);
  const persistence = new GisArchivePersistence({ ...options, setSavedBusy, refreshSavedSelections, savedSelectionOpacities, savedSelectionFills });
  const { handleSaveImportedLayer, handleLoadSavedSelection, handleUpdatePersistedLayer, handleDeleteSavedSelection, handleUpdateArchivedSelectionColor } = persistence;

  const handleArchiveOpacityChange = useCallback(async (selectionId: string, opacity: number) => {
    setSavedSelectionOpacities((prev) => ({ ...prev, [selectionId]: opacity }));
    setOverlayLayers((layers) =>
      layers.map((l) => l.saved_selection_id === selectionId ? { ...l, opacity } : l),
    );
    if (!overlayLayers.some((layer) => layer.saved_selection_id === selectionId)) {
      await handleLoadSavedSelection(selectionId, { opacity });
    }
  }, [handleLoadSavedSelection, overlayLayers, setOverlayLayers]);

  const handleArchiveFillChange = useCallback(async (selectionId: string, showFill: boolean) => {
    setSavedSelectionFills((prev) => ({ ...prev, [selectionId]: showFill }));
    setOverlayLayers((layers) =>
      layers.map((l) => l.saved_selection_id === selectionId ? { ...l, showFill } : l),
    );
    if (!overlayLayers.some((layer) => layer.saved_selection_id === selectionId)) {
      await handleLoadSavedSelection(selectionId, { showFill });
    }
  }, [handleLoadSavedSelection, overlayLayers, setOverlayLayers]);

  useArchiveAutoload(token, autoSelectionId, handleLoadSavedSelection, setGisError);

  return { savedSelections, setSavedSelections, savedSelectionOpacities, savedSelectionFills, savedBusy, refreshSavedSelections, handleSaveImportedLayer, handleLoadSavedSelection, handleUpdatePersistedLayer, handleDeleteSavedSelection, handleUpdateArchivedSelectionColor, handleArchiveOpacityChange, handleArchiveFillChange };
}
