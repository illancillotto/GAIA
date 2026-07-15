import { afterEach, describe, expect, test, vi } from "vitest";

import {
  createGisLayerChangeRequest,
  createGisLayerAnnotation,
  createGisShapefileImportChangeRequests,
  createGisShapefileImport,
  downloadGisQgisProject,
  getGisCatalogDashboard,
  getGisOgcPoc,
  getGisShapefileImport,
  listGisChangeRequests,
  listGisCatalogLayers,
  listGisLayerAnnotations,
  listGisLayerPermissions,
  previewGisShapefileImport,
  publishGisShapefileImport,
  rejectGisShapefileImport,
  revokeGisLayerPermission,
  setGisChangeRequestStatus,
  setGisLayerAnnotationStatus,
  updateGisChangeRequest,
  updateGisLayerAnnotation,
  upsertGisLayerPermission,
  validateGisShapefileImport,
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

  test("loads catalog dashboard health", async () => {
    const dashboard = {
      generated_at: "2026-07-14T08:00:00Z",
      total_layers: 1,
      active_layers: 1,
      inactive_layers: 0,
      workspace_count: 1,
      source_type_counts: { postgis: 1 },
      official_source_counts: { postgis: 1 },
      qgis_publishable_layers: 1,
      exportable_layers: 1,
      health_status: "ok",
      issues: [],
      latest_exports: [],
      workspaces: [],
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(dashboard), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getGisCatalogDashboard("token")).resolves.toEqual(dashboard);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/gis/catalog/dashboard",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer token" }),
      }),
    );
  });

  test("downloads the QGIS project archive", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("qgz", {
        status: 200,
        headers: { "content-type": "application/vnd.qgis.qgisproject+zip" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await downloadGisQgisProject("token");

    await expect(response.text()).resolves.toBe("qgz");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/gis/qgis/project",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer token" }),
      }),
    );
  });

  test("loads the OGC read-only POC plan", async () => {
    const responsePayload = {
      mode: "read_only_poc",
      recommended_server: "qgis_server",
      proxy_path: "/gis/ogc/",
      auth_policy: "gaia_auth_or_vpn_required",
      qgis_project_endpoint: "/gis/qgis/project",
      publishable_layer_count: 1,
      layers: [],
      warnings: ["POC read-only only: keep WFS-T disabled."],
      config_snippets: { rollout_note: "Publish 1 read-only layer(s)." },
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(responsePayload), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getGisOgcPoc("token")).resolves.toEqual(responsePayload);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/gis/ogc/poc",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer token" }),
      }),
    );
  });

  test("creates, fetches, validates and rejects shapefile imports", async () => {
    const file = new File(["zip"], "rete.zip", { type: "application/zip" });
    const importResponse = {
      id: "import-1",
      status: "validated",
      original_filename: "rete.zip",
      workspace: "rete",
      target_layer_name: "rete_upload",
      target_layer_title: "Rete upload",
      official_source: "survey",
      source_srid: 4326,
      encoding: "utf-8",
      staging_table: "gis_staging_import_1",
      feature_count: 2,
      fields: [],
      validation_report: {},
      metadata: {},
      checksum_sha256: "a".repeat(64),
      created_at: "2026-07-14T08:00:00Z",
      updated_at: "2026-07-14T08:00:00Z",
    };
    const importPreviewResponse = {
      import_id: "import-1",
      status: "validated",
      staging_schema: null,
      staging_table: "gis_staging_import_1",
      feature_count: 2,
      returned_count: 1,
      limit: 2,
      offset: 1,
      has_more: false,
      fields: [{ name: "name" }],
      bbox: [8.4, 39.9, 8.5, 40],
      features: [
        {
          feature_seq: 2,
          attributes: { name: "feature-2" },
          geometry: { type: "Point", coordinates: [8.5, 40] },
          geometry_type: "Point",
          source_srid: 4326,
        },
      ],
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify(importResponse), {
          status: 201,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(importResponse), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(importPreviewResponse), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(importResponse), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...importResponse, status: "rejected" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...importResponse, status: "published", published_layer_id: "layer-1" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      createGisShapefileImport("token", {
        file,
        workspace: " rete ",
        domainModule: " network ",
        targetLayerName: " rete_upload ",
        targetLayerTitle: " Rete upload ",
        officialSource: " survey ",
        sourceSrid: 4326,
        encoding: " utf-8 ",
      }),
    ).resolves.toMatchObject({ id: "import-1" });
    await expect(getGisShapefileImport("token", "import-1")).resolves.toMatchObject({ id: "import-1" });
    await expect(previewGisShapefileImport("token", "import-1", 2, 1)).resolves.toMatchObject({ returned_count: 1 });
    await expect(validateGisShapefileImport("token", "import-1")).resolves.toMatchObject({ status: "validated" });
    await expect(rejectGisShapefileImport("token", "import-1")).resolves.toMatchObject({ status: "rejected" });
    await expect(publishGisShapefileImport("token", "import-1")).resolves.toMatchObject({ status: "published" });

    const createCall = fetchMock.mock.calls[0];
    expect(createCall[0]).toBe("/api/gis/imports/shapefile");
    expect(createCall[1]).toEqual(expect.objectContaining({ method: "POST" }));
    expect(createCall[1].headers).toEqual(expect.objectContaining({ Authorization: "Bearer token" }));
    expect(createCall[1].headers).not.toHaveProperty("Content-Type");
    const formData = createCall[1].body as FormData;
    expect(formData.get("file")).toBe(file);
    expect(formData.get("workspace")).toBe(" rete ");
    expect(formData.get("domain_module")).toBe("network");
    expect(formData.get("target_layer_name")).toBe(" rete_upload ");
    expect(formData.get("target_layer_title")).toBe(" Rete upload ");
    expect(formData.get("official_source")).toBe("survey");
    expect(formData.get("source_srid")).toBe("4326");
    expect(formData.get("encoding")).toBe("utf-8");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/gis/imports/import-1");
    expect(fetchMock.mock.calls[1][1].method).toBeUndefined();
    expect(fetchMock).toHaveBeenNthCalledWith(3, "/api/gis/imports/import-1/preview?limit=2&offset=1", expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer token" }) }));
    expect(fetchMock).toHaveBeenNthCalledWith(4, "/api/gis/imports/import-1/validate", expect.objectContaining({ method: "POST" }));
    expect(fetchMock).toHaveBeenNthCalledWith(5, "/api/gis/imports/import-1/reject", expect.objectContaining({ method: "POST" }));
    expect(fetchMock).toHaveBeenNthCalledWith(6, "/api/gis/imports/import-1/publish", expect.objectContaining({ method: "POST" }));
  });

  test("creates change requests from a shapefile import", async () => {
    const responsePayload = {
      import_id: "import-1",
      target_layer_id: "layer-1",
      created_count: 2,
      existing_count: 0,
      returned_count: 2,
      skipped_count: 0,
      total_features: 2,
      limit: 25,
      offset: 0,
      has_more: false,
      change_requests: [],
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(responsePayload), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      createGisShapefileImportChangeRequests("token", "import-1", {
        targetLayerId: "layer-1",
        justification: " rilievo ",
        limit: 25,
        offset: 0,
      }),
    ).resolves.toEqual(responsePayload);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/gis/imports/import-1/change-requests",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ Authorization: "Bearer token" }),
        body: JSON.stringify({
          target_layer_id: "layer-1",
          justification: "rilievo",
          limit: 25,
          offset: 0,
        }),
      }),
    );
  });

  test("omits blank optional shapefile import form fields", async () => {
    const file = new File(["zip"], "rete.zip", { type: "application/zip" });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "import-blank",
          status: "validated",
          original_filename: "rete.zip",
          workspace: "rete",
          target_layer_name: "rete_upload",
          target_layer_title: "Rete upload",
          official_source: "shapefile_upload",
          source_srid: 4326,
          encoding: "utf-8",
          staging_table: "gis_staging_import_blank",
          feature_count: 1,
          fields: [],
          validation_report: {},
          metadata: {},
          checksum_sha256: "b".repeat(64),
          created_at: "2026-07-14T08:00:00Z",
          updated_at: "2026-07-14T08:00:00Z",
        }),
        {
          status: 201,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await createGisShapefileImport("token", {
      file,
      workspace: "rete",
      domainModule: " ",
      targetLayerName: "rete_upload",
      targetLayerTitle: "Rete upload",
      officialSource: "",
    });

    const formData = fetchMock.mock.calls[0][1].body as FormData;
    expect(formData.has("domain_module")).toBe(false);
    expect(formData.has("official_source")).toBe(false);
    expect(formData.has("source_srid")).toBe(false);
    expect(formData.has("encoding")).toBe(false);
  });

  test("keeps blank shapefile encoding and source SRID as automatic import intent", async () => {
    const file = new File(["zip"], "rete.zip", { type: "application/zip" });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "import-auto-encoding",
          status: "validated",
          original_filename: "rete.zip",
          workspace: "rete",
          target_layer_name: "rete_upload",
          target_layer_title: "Rete upload",
          official_source: "shapefile_upload",
          source_srid: 4326,
          encoding: "UTF-8",
          staging_table: "gis_staging_import_auto_encoding",
          feature_count: 1,
          fields: [],
          validation_report: {},
          metadata: {},
          checksum_sha256: "c".repeat(64),
          created_at: "2026-07-14T08:00:00Z",
          updated_at: "2026-07-14T08:00:00Z",
        }),
        {
          status: 201,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await createGisShapefileImport("token", {
      file,
      workspace: "rete",
      targetLayerName: "rete_upload",
      targetLayerTitle: "Rete upload",
      sourceSrid: " ",
      encoding: " ",
    });

    const formData = fetchMock.mock.calls[0][1].body as FormData;
    expect(formData.has("source_srid")).toBe(false);
    expect(formData.get("encoding")).toBe("");
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

  test("lists, creates, updates and transitions change requests", async () => {
    const changeRequest = {
      id: "cr-1",
      layer_id: "layer-1",
      feature_id: "parcel-1",
      change_type: "attribute_update",
      status: "submitted",
      payload: { after: { coltura: "mais" } },
      justification: "Rilievo",
      created_at: "2026-07-14T08:00:00Z",
      updated_at: "2026-07-14T08:00:00Z",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify([changeRequest]), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(changeRequest), {
          status: 201,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...changeRequest, status: "submitted" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...changeRequest, status: "needs_changes" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...changeRequest, status: "approved" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...changeRequest, status: "rejected" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...changeRequest, status: "applied" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await listGisChangeRequests("token", { status: "submitted", layerId: " layer-1 " });
    await createGisLayerChangeRequest("token", "layer-1", {
      featureId: " parcel-1 ",
      changeType: "attribute_update",
      payload: { after: { coltura: "mais" } },
      justification: " Rilievo ",
    });
    await updateGisChangeRequest("token", "cr-1", {
      featureId: " parcel-2 ",
      changeType: "geometry_update",
      payload: { geometry: { type: "Point" } },
      justification: " Aggiornata ",
    });
    await setGisChangeRequestStatus("token", "cr-1", "needs_changes", " integra ");
    await setGisChangeRequestStatus("token", "cr-1", "approved", " valida ");
    await setGisChangeRequestStatus("token", "cr-1", "rejected", " duplicata ");
    await setGisChangeRequestStatus("token", "cr-1", "applied");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/gis/change-requests?status=submitted&layer_id=layer-1",
      expect.any(Object),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/gis/layers/layer-1/change-requests",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          feature_id: "parcel-1",
          change_type: "attribute_update",
          payload: { after: { coltura: "mais" } },
          justification: "Rilievo",
        }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/gis/change-requests/cr-1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({
          feature_id: "parcel-2",
          change_type: "geometry_update",
          payload: { geometry: { type: "Point" } },
          justification: "Aggiornata",
        }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      "/api/gis/change-requests/cr-1/request-changes",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ review_notes: "integra" }) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      5,
      "/api/gis/change-requests/cr-1/approve",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ review_notes: "valida" }) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      6,
      "/api/gis/change-requests/cr-1/reject",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ review_notes: "duplicata" }) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      7,
      "/api/gis/change-requests/cr-1/apply",
      expect.objectContaining({ method: "POST", body: undefined }),
    );
  });
});
