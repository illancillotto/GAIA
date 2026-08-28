import { afterEach, describe, expect, test, vi } from "vitest";

import {
  createGisSchedaTerritoriale,
  downloadGisSchedaTerritoriale,
  getGisTerritorioLegend,
  getGisSchedaTerritoriale,
  interrogaGisTerritorio,
  listGisTerritorioLayers,
} from "@/lib/api/territorio";

describe("territorio API client", () => {
  afterEach(() => vi.unstubAllGlobals());

  test("loads groups and authenticated legends through GAIA", async () => {
    const legend = new Blob(["png"], { type: "image/png" });
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ groups: [], total: 0 }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }))
      .mockResolvedValueOnce(new Response(legend, {
        status: 200,
        headers: { "content-type": "image/png" },
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ gaia: { sources: [] } }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: "sheet-1" }), { status: 200, headers: { "content-type": "application/json" } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: "sheet-1", status: "completed" }), { status: 200, headers: { "content-type": "application/json" } }))
      .mockResolvedValueOnce(new Response(new Blob(["pdf"]), { status: 200, headers: { "content-type": "application/pdf" } }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(listGisTerritorioLayers("token")).resolves.toEqual({ groups: [], total: 0 });
    await expect(getGisTerritorioLegend("token", "/gis/external/layer-1/wms?request=GetLegendGraphic")).resolves.toBeInstanceOf(Blob);
    await expect(interrogaGisTerritorio("token", { lon: 9, lat: 40, layer_ids: [] })).resolves.toEqual({ gaia: { sources: [] } });
    await expect(createGisSchedaTerritoriale("token", "parcel-1")).resolves.toEqual({ id: "sheet-1" });
    await expect(getGisSchedaTerritoriale("token", "sheet-1")).resolves.toEqual({ id: "sheet-1", status: "completed" });
    await expect(downloadGisSchedaTerritoriale("token", "sheet-1")).resolves.toBeInstanceOf(Blob);
    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/gis/territorio/layers", expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer token" }) }));
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/gis/external/layer-1/wms?request=GetLegendGraphic", expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer token" }) }));
    expect(fetchMock).toHaveBeenNthCalledWith(3, "/api/gis/interroga", expect.objectContaining({ method: "POST", body: JSON.stringify({ lon: 9, lat: 40, layer_ids: [] }) }));
    expect(fetchMock).toHaveBeenNthCalledWith(4, "/api/gis/scheda-territoriale", expect.objectContaining({ method: "POST", body: JSON.stringify({ particella_id: "parcel-1" }) }));
    expect(fetchMock).toHaveBeenNthCalledWith(5, "/api/gis/scheda-territoriale/sheet-1", expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer token" }) }));
    expect(fetchMock).toHaveBeenNthCalledWith(6, "/api/gis/scheda-territoriale/sheet-1/pdf", expect.any(Object));
  });
});
