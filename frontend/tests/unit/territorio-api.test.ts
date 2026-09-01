import { afterEach, describe, expect, test, vi } from "vitest";

import { getGisTerritorioMunicipalities } from "@/lib/api/territorio";

describe("territorio API", () => {
  afterEach(() => vi.unstubAllGlobals());

  test("queries municipality features only through the governed WFS proxy", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ type: "FeatureCollection", features: [] }), {
      status: 200,
      headers: { "content-type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(getGisTerritorioMunicipalities("token", "layer-1")).resolves.toMatchObject({ type: "FeatureCollection" });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/gis/external/layer-1/wfs?"),
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer token" }) }),
    );
    expect(fetchMock.mock.calls[0][0]).toContain("request=GetFeature");
    expect(fetchMock.mock.calls[0][0]).not.toContain("webgis.regione.sardegna.it");
  });
});
