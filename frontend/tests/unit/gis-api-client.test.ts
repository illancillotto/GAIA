import { afterEach, describe, expect, test, vi } from "vitest";

import { listGisCatalogLayers } from "@/lib/api/gis";

describe("GIS platform api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("lists catalog layers with optional filters", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0 }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      listGisCatalogLayers("token", {
        workspace: " catasto ",
        domainModule: " catasto ",
        sourceType: " postgis ",
        officialSource: " postgis ",
        isActive: false,
      }),
    ).resolves.toEqual({ items: [], total: 0 });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/gis/layers?workspace=catasto&domain_module=catasto&source_type=postgis&official_source=postgis&is_active=false",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer token" }),
      }),
    );
  });

  test("omits blank filters from the catalog query", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0 }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await listGisCatalogLayers("token", { workspace: " ", isActive: true });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/gis/layers?is_active=true",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer token" }),
      }),
    );
  });

  test("uses the plain catalog path when no filters are provided", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0 }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await listGisCatalogLayers("token");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/gis/layers",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer token" }),
      }),
    );
  });
});
