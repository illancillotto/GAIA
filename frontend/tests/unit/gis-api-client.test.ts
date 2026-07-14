import { afterEach, describe, expect, test, vi } from "vitest";

import {
  createGisLayerAnnotation,
  listGisCatalogLayers,
  listGisLayerAnnotations,
  listGisLayerPermissions,
  revokeGisLayerPermission,
  setGisLayerAnnotationStatus,
  updateGisLayerAnnotation,
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

  test("lists, creates, updates and transitions annotations", async () => {
    const annotation = {
      id: "ann-1",
      layer_id: "layer-1",
      feature_id: "parcel-1",
      title: "Nota",
      body: "Testo",
      attachment_refs: [],
      status: "open",
      created_at: "2026-07-14T08:00:00Z",
      updated_at: "2026-07-14T08:00:00Z",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify([annotation]), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(annotation), {
          status: 201,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...annotation, title: "Aggiornata" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...annotation, status: "in_review" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...annotation, status: "closed" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...annotation, status: "rejected" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await listGisLayerAnnotations("token", "layer-1", { status: "open", featureId: " parcel-1 " });
    await createGisLayerAnnotation("token", "layer-1", {
      featureId: " parcel-1 ",
      title: "Nota",
      body: "Testo",
      attachmentRefs: [{ filename: "foto.jpg" }],
    });
    await updateGisLayerAnnotation("token", "layer-1", "ann-1", { title: "Aggiornata", body: "Testo aggiornato" });
    await setGisLayerAnnotationStatus("token", "layer-1", "ann-1", "in_review");
    await setGisLayerAnnotationStatus("token", "layer-1", "ann-1", "closed");
    await setGisLayerAnnotationStatus("token", "layer-1", "ann-1", "rejected");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/gis/layers/layer-1/annotations?status=open&feature_id=parcel-1",
      expect.any(Object),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/gis/layers/layer-1/annotations",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          feature_id: "parcel-1",
          title: "Nota",
          body: "Testo",
          attachment_refs: [{ filename: "foto.jpg" }],
        }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/gis/layers/layer-1/annotations/ann-1",
      expect.objectContaining({ method: "PATCH" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      "/api/gis/layers/layer-1/annotations/ann-1/in-review",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      5,
      "/api/gis/layers/layer-1/annotations/ann-1/close",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      6,
      "/api/gis/layers/layer-1/annotations/ann-1/reject",
      expect.objectContaining({ method: "POST" }),
    );
  });

  test("defaults omitted annotation attachments to an empty list", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "ann-1" }), {
        status: 201,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await createGisLayerAnnotation("token", "layer-1", {
      featureId: "",
      title: "Nota",
      body: "Testo",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/gis/layers/layer-1/annotations",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          title: "Nota",
          body: "Testo",
          attachment_refs: [],
        }),
      }),
    );
  });
});
