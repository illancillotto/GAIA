import { act, renderHook, waitFor } from "@testing-library/react";
import { useCallback, useState } from "react";
import { beforeEach, expect, test, vi } from "vitest";
import { useGisArchive, type OverlayLayerState } from "@/components/catasto/gis/use-gis-archive";
import * as api from "@/lib/api/catasto";

vi.mock("@/lib/api/catasto", () => ({ catastoGisCreateSavedSelection: vi.fn(), catastoGisDeleteSavedSelection: vi.fn(), catastoGisGetSavedSelection: vi.fn(), catastoGisListSavedSelections: vi.fn(), catastoGisUpdateSavedSelection: vi.fn() }));

const stats = { processed: 1, found: 1, notFound: 0, multiple: 0, invalid: 0, withGeometry: 1 };
const geometry = { type: "FeatureCollection" as const, features: [] };
function draft(key = "draft"): OverlayLayerState {
  return { layer_key: key, saved_selection_id: null, name: key, color: "#112233", opacity: 0.5, visible: true, geojson: geometry, importStats: stats, importedItems: [{ particella_id: "parcel" }], isPersisted: false };
}
const saved = { id: "saved", name: "Saved", color: "#445566", n_particelle: 1, n_with_geometry: 1, geojson: geometry, items: [] };
const focus = vi.fn();

function useArchiveHarness({ token, initial, selection = null }: { token: string | null; initial: OverlayLayerState[]; selection?: string | null }) {
  const [overlayLayers, setOverlayLayers] = useState(initial);
  const [error, setGisError] = useState<string | null>(null);
  const [info, setGisInfo] = useState<string | null>(null);
  const updateOverlayLayer = useCallback((key: string, update: (layer: OverlayLayerState) => OverlayLayerState) => setOverlayLayers((layers) => layers.map((layer) => layer.layer_key === key ? update(layer) : layer)), []);
  const archive = useGisArchive({ token, autoSelectionId: selection, overlayLayers, setOverlayLayers, setGisError, setGisInfo, focusLayerGeojson: focus, updateOverlayLayer });
  return { ...archive, overlayLayers, setOverlayLayers, error, info };
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.catastoGisListSavedSelections).mockResolvedValue([saved] as never);
  vi.mocked(api.catastoGisCreateSavedSelection).mockResolvedValue(saved as never);
  vi.mocked(api.catastoGisGetSavedSelection).mockResolvedValue(saved as never);
  vi.mocked(api.catastoGisUpdateSavedSelection).mockResolvedValue(saved as never);
});

test("fails closed without a session for every archive command", async () => {
  const { result } = renderHook(useArchiveHarness, { initialProps: { token: null, initial: [draft()] } });
  await act(async () => {
    await result.current.refreshSavedSelections();
    await result.current.handleSaveImportedLayer("draft");
    await result.current.handleLoadSavedSelection("saved");
    await result.current.handleUpdatePersistedLayer("draft");
    await result.current.handleDeleteSavedSelection("saved");
    await result.current.handleUpdateArchivedSelectionColor("saved", "#ffffff");
  });
  for (const method of Object.values(api)) expect(method).not.toHaveBeenCalled();
  expect(result.current.overlayLayers).toEqual([draft()]);
});

test("rejects invalid drafts and metadata updates without sending requests", async () => {
  const layers = [draft(), { ...draft("persisted"), isPersisted: true }, { ...draft("empty"), importedItems: [] }, { ...draft("no-stats"), importStats: null }, { ...draft("unnamed"), name: " " }];
  const { result } = renderHook(useArchiveHarness, { initialProps: { token: "token", initial: layers } });
  await waitFor(() => expect(result.current.savedSelections).toHaveLength(1));
  await act(async () => {
    for (const key of ["missing", "persisted", "empty", "no-stats", "unnamed"]) await result.current.handleSaveImportedLayer(key);
    await result.current.handleUpdatePersistedLayer("missing");
    await result.current.handleUpdatePersistedLayer("draft");
  });
  expect(api.catastoGisCreateSavedSelection).not.toHaveBeenCalled();
  expect(api.catastoGisUpdateSavedSelection).not.toHaveBeenCalled();
  expect(result.current.error).toBe("Inserisci un nome per salvare il layer.");
});

test("updates only the selected layer while preserving neighboring drafts", async () => {
  const other = draft("other");
  const { result } = renderHook(useArchiveHarness, { initialProps: { token: "token", initial: [draft(), other] } });
  await act(async () => { await result.current.handleSaveImportedLayer("draft"); });
  expect(api.catastoGisCreateSavedSelection).toHaveBeenCalledWith("token", expect.objectContaining({ source_filename: null }));
  expect(result.current.overlayLayers[1]).toBe(other);
  await act(async () => { await result.current.handleUpdatePersistedLayer("saved"); });
  expect(result.current.overlayLayers[1]).toBe(other);
  await act(async () => { await result.current.handleUpdateArchivedSelectionColor("saved", "#ffffff"); });
  await act(async () => { await result.current.handleArchiveOpacityChange("saved", 0.3); });
  await act(async () => { await result.current.handleArchiveFillChange("saved", false); });
  expect(result.current.overlayLayers[0]).toMatchObject({ color: "#ffffff", opacity: 0.3, showFill: false });
  expect(result.current.overlayLayers[1]).toBe(other);
  await act(async () => { await result.current.handleLoadSavedSelection("saved", { opacity: 0.8, showFill: true }); });
  expect(result.current.overlayLayers[0]).toMatchObject({ opacity: 0.8, showFill: true });
  await act(async () => { await result.current.handleLoadSavedSelection("saved"); });
  expect(result.current.overlayLayers[0]).toMatchObject({ opacity: 0.8, showFill: true });
  expect(api.catastoGisGetSavedSelection).not.toHaveBeenCalled();
});

test.each([null, {}, stats])("restores persisted import statistics and cached display settings: %s", async (import_summary) => {
  vi.mocked(api.catastoGisGetSavedSelection).mockResolvedValue({ ...saved, import_summary, source_filename: "original.xlsx" } as never);
  const { result } = renderHook(useArchiveHarness, { initialProps: { token: "token", initial: [] } });
  await act(async () => { await result.current.handleArchiveOpacityChange("saved", 0.25); });
  await act(async () => { await result.current.handleArchiveFillChange("saved", false); });
  act(() => result.current.setOverlayLayers([]));
  await act(async () => { await result.current.handleLoadSavedSelection("saved"); });
  expect(result.current.overlayLayers[0]).toMatchObject({ opacity: 0.25, showFill: false, importStats: stats });
});

test.each([new Error("Mappa non disponibile"), "map unavailable"])("surfaces autoload focus failure without a retry loop: %s", async (failure) => {
  focus.mockImplementation(() => { throw failure; });
  const existing = { ...draft("saved"), saved_selection_id: "saved", isPersisted: true };
  const { result, rerender } = renderHook(useArchiveHarness, { initialProps: { token: "token", initial: [existing], selection: "saved" } });
  await waitFor(() => expect(result.current.error).toBe(failure instanceof Error ? failure.message : "Caricamento layer da URL fallito"));
  rerender({ token: "token", initial: [existing], selection: "saved" });
  expect(focus).toHaveBeenCalledTimes(1);
});
