import { afterEach, describe, expect, test, vi } from "vitest";

import {
  listGisCatalogLayers,
  listGisLayerPermissions,
  revokeGisLayerPermission,
  upsertGisLayerPermission,
} from "@/lib/api/gis";

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

  test("lists, upserts and revokes layer permissions", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ id: "perm-1", principal_type: "role", principal_key: "viewer", access_level: "viewer" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(listGisLayerPermissions("token", "layer-1")).resolves.toEqual([]);
    await expect(
      upsertGisLayerPermission("token", "layer-1", {
        principalType: "role",
        principalKey: "viewer",
        accessLevel: "viewer",
      }),
    ).resolves.toMatchObject({ id: "perm-1" });
    await expect(revokeGisLayerPermission("token", "layer-1", "perm-1")).resolves.toBeUndefined();

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/gis/layers/layer-1/permissions",
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer token" }) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/gis/layers/layer-1/permissions",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ principal_type: "role", principal_key: "viewer", access_level: "viewer" }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/gis/layers/layer-1/permissions/perm-1",
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});
