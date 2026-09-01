import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { useTerritorioUnifiedSearch } from "@/components/catasto/gis/use-territorio-unified-search";

const api = vi.hoisted(() => ({
  catastoGisSearch: vi.fn(),
  catastoListDistretti: vi.fn(),
  catastoGetDistrettoGeojson: vi.fn(),
  catastoGisGetDeliveryPointPopup: vi.fn(),
  getGisTerritorioMunicipalities: vi.fn(),
}));
vi.mock("@/lib/api/catasto", () => api);
vi.mock("@/lib/api/territorio", () => ({ getGisTerritorioMunicipalities: api.getGisTerritorioMunicipalities }));

const municipalLayer = { id: "municipal", name: "ras_limiti_comunali" } as never;

function mapMock() {
  return {
    querySourceFeatures: vi.fn(() => [{ type: "Feature", properties: { id: "dp1", punto_consegna_code: "Arborea-1" }, geometry: { type: "Point", coordinates: [8.6, 39.9] } }]),
    flyTo: vi.fn(),
    fitBounds: vi.fn(),
  };
}

describe("useTerritorioUnifiedSearch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.catastoGisSearch.mockResolvedValue({ results: [], geojson: null });
    api.catastoListDistretti.mockResolvedValue([{ id: "d1", num_distretto: "12", nome_distretto: "Arborea" }]);
    api.getGisTerritorioMunicipalities.mockResolvedValue({ type: "FeatureCollection", features: [
      { type: "Feature", properties: { nome: "Arborea" }, geometry: { type: "Point", coordinates: [8.61, 39.91] } },
    ] });
    api.catastoGetDistrettoGeojson.mockResolvedValue({ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [8.62, 39.92] } });
    api.catastoGisGetDeliveryPointPopup.mockResolvedValue({ id: "dp1" });
  });

  test("combines sources and focuses coordinates, districts and bboxes", async () => {
    const map = mapMock();
    const { result } = renderHook(() => useTerritorioUnifiedSearch({ token: "token", map: map as never, municipalityLayer: municipalLayer }));
    act(() => result.current.setQuery("39.9, 8.6"));
    await act(() => result.current.runSearch());
    expect(result.current.results[0]).toMatchObject({ kind: "coordinata", source: "Coordinate GAIA" });
    expect(api.getGisTerritorioMunicipalities).toHaveBeenCalledWith("token", "municipal");
    await act(() => result.current.selectResult(result.current.results[0]));
    expect(map.flyTo).toHaveBeenCalledWith({ center: [8.6, 39.9], zoom: 16 });

    act(() => result.current.setQuery("Arborea"));
    await act(() => result.current.runSearch());
    const district = result.current.results.find((item) => item.kind === "distretto")!;
    await act(() => result.current.selectResult(district));
    expect(api.catastoGetDistrettoGeojson).toHaveBeenCalledWith("token", "d1");
    expect(map.fitBounds).toHaveBeenCalled();
    const municipality = result.current.results.find((item) => item.kind === "comune")!;
    await act(() => result.current.selectResult(municipality));
    expect(map.fitBounds).toHaveBeenCalledTimes(2);
    const pdc = result.current.results.find((item) => item.kind === "pdc")!;
    await act(() => result.current.selectResult(pdc));
    expect(api.catastoGisGetDeliveryPointPopup).toHaveBeenCalledWith("token", "dp1");
  });

  test("governs empty input, missing session, outside results and request failures", async () => {
    const map = mapMock();
    const missing = renderHook(() => useTerritorioUnifiedSearch({ token: null, map: map as never, municipalityLayer: null }));
    await act(() => missing.result.current.runSearch());
    expect(missing.result.current.message).toBe("Sessione non disponibile.");

    const active = renderHook(() => useTerritorioUnifiedSearch({ token: "token", map: map as never, municipalityLayer: null }));
    await act(() => active.result.current.runSearch());
    expect(active.result.current.message).toBe("Inserisci un criterio di ricerca.");
    act(() => active.result.current.setQuery("nessuno"));
    api.catastoListDistretti.mockResolvedValueOnce([]);
    await act(() => active.result.current.runSearch());
    expect(active.result.current.message).toContain("Nessun risultato nel comprensorio");
    expect(api.getGisTerritorioMunicipalities).not.toHaveBeenCalled();

    await act(() => active.result.current.selectResult({ id: "x", kind: "coordinata", label: "Roma", detail: "", source: "", center: [12.5, 41.9] }));
    expect(active.result.current.message).toContain("fuori dal comprensorio");
    expect(map.flyTo).not.toHaveBeenCalled();

    api.catastoGisSearch.mockRejectedValueOnce(new Error("API offline"));
    act(() => active.result.current.setQuery("errore"));
    await act(() => active.result.current.runSearch());
    expect(active.result.current.message).toBe("API offline");
    act(() => active.result.current.clear());
    expect(active.result.current).toMatchObject({ query: "", results: [], message: null });
  });

  test("handles unavailable map sources and ignores selection without map", async () => {
    const map = mapMock();
    map.querySourceFeatures.mockImplementationOnce(() => { throw new Error("source missing"); });
    const { result } = renderHook(() => useTerritorioUnifiedSearch({ token: "token", map: map as never, municipalityLayer: null }));
    act(() => result.current.setQuery("Arborea"));
    await act(() => result.current.runSearch());
    expect(result.current.results.some((item) => item.kind === "pdc")).toBe(false);
    const noMap = renderHook(() => useTerritorioUnifiedSearch({ token: "token", map: null, municipalityLayer: null }));
    act(() => noMap.result.current.setQuery("40° 0' 0\" N 8° 36' 0\" E"));
    await act(() => noMap.result.current.runSearch());
    expect(noMap.result.current.results[0].detail).toBe("Coordinate DMS");
    await act(() => noMap.result.current.selectResult({ id: "x", kind: "pdc", label: "x", detail: "", source: "" }));
    expect(noMap.result.current.message).toBeNull();

    api.catastoGisSearch.mockRejectedValueOnce("offline");
    act(() => result.current.setQuery("errore non Error"));
    await act(() => result.current.runSearch());
    expect(result.current.message).toBe("Ricerca GIS non disponibile.");

    api.catastoGetDistrettoGeojson.mockResolvedValueOnce({ type: "Feature", properties: {}, geometry: null });
    await act(() => result.current.selectResult({ id: "distretto:d2", kind: "distretto", label: "D2", detail: "", source: "" }));
    expect(result.current.message).toContain("fuori dal comprensorio");
  });
});
