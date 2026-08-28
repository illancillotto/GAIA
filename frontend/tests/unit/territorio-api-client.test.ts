import { afterEach, describe, expect, test, vi } from "vitest";

import {
  getGisTerritorioLegend,
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
      }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(listGisTerritorioLayers("token")).resolves.toEqual({ groups: [], total: 0 });
    await expect(getGisTerritorioLegend("token", "/gis/external/layer-1/wms?request=GetLegendGraphic")).resolves.toBeInstanceOf(Blob);
    await expect(interrogaGisTerritorio("token", { lon: 9, lat: 40, layer_ids: [] })).resolves.toEqual({ gaia: { sources: [] } });
    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/gis/territorio/layers", expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer token" }) }));
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/gis/external/layer-1/wms?request=GetLegendGraphic", expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer token" }) }));
    expect(fetchMock).toHaveBeenNthCalledWith(3, "/api/gis/interroga", expect.objectContaining({ method: "POST", body: JSON.stringify({ lon: 9, lat: 40, layer_ids: [] }) }));
  });
});
