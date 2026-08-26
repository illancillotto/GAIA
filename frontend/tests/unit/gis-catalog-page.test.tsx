import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import GisCatalogPage from "@/app/gis/catalogo/page";
import type {
  GisCatalogAnnotation,
  GisCatalogChangeRequest,
  GisCatalogDashboardResponse,
  GisCatalogLayer,
} from "@/types/gis";

const mocks = vi.hoisted(() => ({
  createGisLayerChangeRequest: vi.fn(),
  createGisLayerAnnotation: vi.fn(),
  getGisCatalogDashboard: vi.fn(),
  getStoredAccessToken: vi.fn(),
  listGisChangeRequests: vi.fn(),
  listGisCatalogLayers: vi.fn(),
  listGisLayerAnnotations: vi.fn(),
  listGisLayerFeatures: vi.fn(),
  setGisChangeRequestStatus: vi.fn(),
  setGisLayerAnnotationStatus: vi.fn(),
  updateGisChangeRequest: vi.fn(),
  updateGisLayerAnnotation: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
    ...props
  }: {
    href: string;
    children: ReactNode;
    className?: string;
    "aria-label"?: string;
  }) => (
    <a href={href} className={className} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({
    title,
    requiredModule,
    children,
  }: {
    title: string;
    requiredModule?: string;
    children: ReactNode;
  }) => (
    <section
      data-testid="protected-page"
      data-title={title}
      data-required-module={requiredModule}
    >
      {children}
    </section>
  ),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: () => mocks.getStoredAccessToken(),
}));

vi.mock("@/lib/api/gis", () => ({
  createGisLayerChangeRequest: (...args: unknown[]) =>
    mocks.createGisLayerChangeRequest(...args),
  createGisLayerAnnotation: (...args: unknown[]) =>
    mocks.createGisLayerAnnotation(...args),
  getGisCatalogDashboard: (...args: unknown[]) =>
    mocks.getGisCatalogDashboard(...args),
  listGisChangeRequests: (...args: unknown[]) =>
    mocks.listGisChangeRequests(...args),
  listGisCatalogLayers: (...args: unknown[]) =>
    mocks.listGisCatalogLayers(...args),
  listGisLayerAnnotations: (...args: unknown[]) =>
    mocks.listGisLayerAnnotations(...args),
  listGisLayerFeatures: (...args: unknown[]) =>
    mocks.listGisLayerFeatures(...args),
  setGisChangeRequestStatus: (...args: unknown[]) =>
    mocks.setGisChangeRequestStatus(...args),
  setGisLayerAnnotationStatus: (...args: unknown[]) =>
    mocks.setGisLayerAnnotationStatus(...args),
  updateGisChangeRequest: (...args: unknown[]) =>
    mocks.updateGisChangeRequest(...args),
  updateGisLayerAnnotation: (...args: unknown[]) =>
    mocks.updateGisLayerAnnotation(...args),
}));

const catastoLayer: GisCatalogLayer = {
  id: "layer-catasto",
  workspace: "catasto",
  name: "cat_particelle_current",
  title: "Particelle catastali correnti",
  description: "Vista PostGIS operativa",
  domain_module: "catasto",
  source_type: "postgis",
  official_source: "postgis",
  postgis_schema: "public",
  postgis_table: "cat_particelle_current",
  geometry_column: "geometry",
  geometry_type: "MULTIPOLYGON",
  srid: 4326,
  feature_id_column: "id",
  martin_layer_id: "cat_particelle_current",
  ogc_service_url: null,
  qgis_project_path: null,
  nas_export_root: null,
  metadata: {
    qgis: { mode: "read_only" },
    tiles: { provider: "martin" },
  },
  is_active: true,
  effective_access_level: "viewer",
  can_view: true,
  can_annotate: false,
  can_edit: false,
  can_approve: false,
  can_manage: false,
  created_at: "2026-07-14T08:00:00Z",
  updated_at: "2026-07-14T08:00:00Z",
};

const reteLayer: GisCatalogLayer = {
  ...catastoLayer,
  id: "layer-rete",
  workspace: "rete",
  name: "rete_condotte",
  title: "Condotte irrigue",
  description: null,
  domain_module: "network",
  official_source: "survey",
  postgis_schema: null,
  postgis_table: null,
  geometry_type: null,
  srid: null,
  martin_layer_id: null,
  metadata: {},
  is_active: false,
  effective_access_level: "admin",
  can_manage: true,
};

const riordinoLayer: GisCatalogLayer = {
  ...catastoLayer,
  id: "layer-riordino",
  workspace: "riordino",
  name: "riordino_pratiche",
  title: "Pratiche di riordino",
  description: "Registro delle pratiche consortili",
  domain_module: "riordino",
  source_type: "domain_registry",
  official_source: "riordino",
  postgis_schema: null,
  postgis_table: null,
  geometry_column: null,
  geometry_type: null,
  srid: null,
  feature_id_column: "id",
  martin_layer_id: null,
  metadata: {},
};

const unmappedLayer: GisCatalogLayer = {
  ...catastoLayer,
  id: "layer-unmapped",
  workspace: "ambiente",
  name: "aree_verdi",
  title: "Aree verdi",
  description: "Aree senza un modulo operativo dedicato",
  domain_module: "ambiente",
  geometry_type: null,
};

const networkDomainLayer: GisCatalogLayer = {
  ...reteLayer,
  id: "layer-network-domain",
  workspace: "infrastrutture",
  domain_module: "network",
};

const okDashboard: GisCatalogDashboardResponse = {
  generated_at: "2026-07-14T08:00:00Z",
  total_layers: 2,
  active_layers: 1,
  inactive_layers: 1,
  workspace_count: 2,
  source_type_counts: { postgis: 2 },
  official_source_counts: { postgis: 1, survey: 1 },
  qgis_publishable_layers: 1,
  exportable_layers: 1,
  health_status: "ok",
  issues: [],
  latest_exports: [
    {
      layer_id: "layer-catasto",
      workspace: "catasto",
      layer_name: "cat_particelle_current",
      version_label: "scheduled-20260714T023000Z",
      status: "completed",
      nas_path: "/tmp/catasto.zip",
      trigger: "scheduled",
      completed_at: "2026-07-14T02:31:00Z",
      created_at: "2026-07-14T02:30:00Z",
    },
    {
      layer_id: "layer-rete",
      workspace: "rete",
      layer_name: "rete_condotte",
      version_label: "manual-20260714",
      status: "completed",
      nas_path: "/tmp/rete.zip",
      trigger: null,
      completed_at: "2026-07-14T03:01:00Z",
      created_at: "2026-07-14T03:00:00Z",
    },
  ],
  workspaces: [
    {
      workspace: "catasto",
      total_layers: 1,
      active_layers: 1,
      inactive_layers: 0,
      postgis_layers: 1,
      domain_registry_layers: 0,
      qgis_publishable_layers: 1,
      exportable_layers: 1,
      issue_count: 0,
      health_status: "ok",
    },
    {
      workspace: "rete",
      total_layers: 1,
      active_layers: 0,
      inactive_layers: 1,
      postgis_layers: 1,
      domain_registry_layers: 0,
      qgis_publishable_layers: 0,
      exportable_layers: 0,
      issue_count: 0,
      health_status: "ok",
    },
  ],
};

const warningDashboard: GisCatalogDashboardResponse = {
  ...okDashboard,
  total_layers: 1,
  active_layers: 1,
  inactive_layers: 0,
  workspace_count: 1,
  qgis_publishable_layers: 1,
  exportable_layers: 1,
  health_status: "warning",
  latest_exports: [],
  issues: [
    {
      layer_id: "layer-rete",
      workspace: "rete",
      layer_name: "rete_condotte",
      severity: "warning",
      code: "qgis_edit_policy_missing",
      message: "Layer QGIS editabile senza policy controlled.",
    },
  ],
  workspaces: [
    {
      workspace: "rete",
      total_layers: 1,
      active_layers: 1,
      inactive_layers: 0,
      postgis_layers: 1,
      domain_registry_layers: 0,
      qgis_publishable_layers: 1,
      exportable_layers: 1,
      issue_count: 1,
      health_status: "warning",
    },
  ],
};

const ogcPocResponse = {
  mode: "read_only_poc" as const,
  recommended_server: "qgis_server" as const,
  proxy_path: "/gis/ogc/",
  auth_policy: "gaia_auth_or_vpn_required",
  qgis_project_endpoint: "/gis/qgis/project",
  publishable_layer_count: 1,
  warnings: ["POC read-only only: keep WFS-T disabled."],
  config_snippets: {
    rollout_note: "Publish 1 read-only layer(s). Keep WFS-T disabled.",
  },
  layers: [
    {
      layer_id: "layer-catasto",
      workspace: "catasto",
      layer_name: "cat_particelle_current",
      title: "Particelle catastali correnti",
      service_layer_name: "catasto__cat_particelle_current",
      source_table: "public.cat_particelle_current",
      geometry_type: "MULTIPOLYGON",
      srid: 4326,
      wms_enabled: true,
      wfs_enabled: true,
      wfs_transactional: false,
    },
  ],
};

const managedLayer: GisCatalogLayer = {
  ...reteLayer,
  can_annotate: true,
  can_edit: true,
  can_approve: true,
};

const openAnnotation: GisCatalogAnnotation = {
  id: "annotation-open",
  layer_id: "layer-rete",
  feature_id: "parcel-1",
  title: "Nota campo",
  body: "Verificare argine",
  geometry: null,
  attachment_refs: [],
  status: "open",
  created_by_user_id: 2,
  created_at: "2026-07-14T08:00:00Z",
  updated_at: "2026-07-14T08:00:00Z",
};

const closedAnnotation: GisCatalogAnnotation = {
  ...openAnnotation,
  id: "annotation-closed",
  title: "Nota chiusa",
  status: "closed",
};

const detachedAnnotation: GisCatalogAnnotation = {
  ...openAnnotation,
  id: "annotation-detached",
  feature_id: null,
  title: "Nota senza feature",
};

const submittedChangeRequest: GisCatalogChangeRequest = {
  id: "change-submitted",
  layer_id: "layer-rete",
  feature_id: "parcel-1",
  change_type: "attribute_update",
  status: "submitted",
  payload: { before: { coltura: "grano" }, after: { coltura: "mais" } },
  justification: "Rilievo tecnico",
  requested_by_user_id: 2,
  reviewed_by_user_id: null,
  review_notes: null,
  reviewed_at: null,
  created_at: "2026-07-14T08:00:00Z",
  updated_at: "2026-07-14T08:00:00Z",
};

const approvedChangeRequest: GisCatalogChangeRequest = {
  ...submittedChangeRequest,
  id: "change-approved",
  feature_id: null,
  change_type: "feature_create",
  status: "approved",
  payload: { geometry: { type: "Point" }, properties: { coltura: "mais" } },
  justification: null,
  review_notes: "validata",
};


function renderGisCatalogWorkspace(token: string | null = "token") {
  mocks.getStoredAccessToken.mockReturnValue(token);
  render(<GisCatalogPage />);
}

describe("GisCatalogPage", () => {
  beforeEach(() => {
    mocks.createGisLayerChangeRequest.mockReset();
    mocks.createGisLayerAnnotation.mockReset();
    mocks.getGisCatalogDashboard.mockReset();
    mocks.getGisCatalogDashboard.mockResolvedValue(okDashboard);
    mocks.getStoredAccessToken.mockReset();
    mocks.listGisChangeRequests.mockReset();
    mocks.listGisCatalogLayers.mockReset();
    mocks.listGisLayerAnnotations.mockReset();
    mocks.listGisLayerFeatures.mockReset();
    mocks.listGisLayerFeatures.mockResolvedValue({
      items: [
        {
          feature_id: "parcel-1",
          label: "parcel-1 - Condotta principale",
          attributes: { id: "parcel-1", coltura: "grano", diameter: 120 },
          geometry: {
            type: "LineString",
            coordinates: [
              [8.4, 39.9],
              [8.5, 40],
            ],
          },
        },
      ],
      total: 1,
      limit: 20,
      offset: 0,
      has_more: false,
    });
    mocks.setGisChangeRequestStatus.mockReset();
    mocks.setGisLayerAnnotationStatus.mockReset();
    mocks.updateGisChangeRequest.mockReset();
    mocks.updateGisLayerAnnotation.mockReset();
  });

  test("renders a session loading card before the token is available", () => {
    renderGisCatalogWorkspace(null);

    expect(
      screen.getByText("Sessione catalogo in caricamento."),
    ).toBeInTheDocument();
    expect(mocks.listGisCatalogLayers).not.toHaveBeenCalled();
    expect(mocks.getGisCatalogDashboard).not.toHaveBeenCalled();
  });

  test("loads catalog layers and renders read-only metadata", async () => {
    mocks.listGisCatalogLayers.mockResolvedValueOnce({
      items: [catastoLayer, reteLayer],
      total: 2,
    });

    renderGisCatalogWorkspace();

    expect(
      await screen.findByText("Particelle catastali correnti"),
    ).toBeInTheDocument();
    expect(screen.getByText("Condotte irrigue")).toBeInTheDocument();
    expect(
      screen.getByText("public.cat_particelle_current"),
    ).toBeInTheDocument();
    expect(screen.getByText("read_only")).toBeInTheDocument();
    expect(screen.getByText("martin")).toBeInTheDocument();
    expect(screen.getAllByText("Non configurato").length).toBeGreaterThan(0);
    expect(screen.getByText("Health catalogo GIS")).toBeInTheDocument();
    expect(screen.getByText("Layer = una mappa tematica")).toBeInTheDocument();
    expect(screen.getByText("Import shapefile")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Strumenti per import e QGIS" })).toHaveAttribute("href", "/gis/strumenti");
    expect(screen.getAllByText(/Permesso effettivo:/)).toHaveLength(2);
    expect(
      screen.getByText("Nessuna criticita rilevata sui layer visibili."),
    ).toBeInTheDocument();
    expect(screen.getByText("Ultimi export")).toBeInTheDocument();
    expect(screen.getByText("scheduled-20260714T023000Z")).toBeInTheDocument();
    expect(screen.getByText("scheduled")).toBeInTheDocument();
    expect(screen.getByText("manual-20260714")).toBeInTheDocument();
    expect(screen.getByText("manual")).toBeInTheDocument();
    expect(screen.getAllByText("1 layer / 0 issue")).toHaveLength(2);
    expect(screen.getAllByText("Azioni disponibili:")).toHaveLength(2);
    expect(
      screen.getByRole("link", { name: "Apri mappa Particelle catastali correnti" }),
    ).toHaveAttribute("href", "/gis/catalogo/layer-catasto");
    expect(mocks.listGisCatalogLayers).toHaveBeenCalledWith("token");
    expect(mocks.getGisCatalogDashboard).toHaveBeenCalledWith("token");
  });

  test("offers an essential catalog search, categories, counts, and module destinations", async () => {
    const catalogLayers = [
      catastoLayer,
      reteLayer,
      riordinoLayer,
      unmappedLayer,
      networkDomainLayer,
    ];
    mocks.listGisCatalogLayers.mockResolvedValue({
      items: catalogLayers,
      total: catalogLayers.length,
    });

    renderGisCatalogWorkspace();

    expect(await screen.findByText("5 mappe trovate")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Apri mappa Particelle catastali correnti" }),
    ).toHaveAttribute("href", "/gis/catalogo/layer-catasto");
    const reteLinks = screen.getAllByRole("link", {
      name: "Apri modulo Rete Condotte irrigue",
    });
    expect(reteLinks).toHaveLength(2);
    expect(reteLinks[0]).toHaveAttribute("href", "/network");
    expect(
      screen.getByRole("link", { name: "Apri modulo Riordino Pratiche di riordino" }),
    ).toHaveAttribute("href", "/riordino");
    expect(
      screen.queryByRole("link", { name: /Apri.*Ambiente/i }),
    ).not.toBeInTheDocument();

    const search = screen.getByRole("searchbox", {
      name: "Cerca per nome o contenuto",
    });
    for (const value of ["c", "co", "con", "cond", "condo", "condot", "condott", "condotte"]) {
      fireEvent.input(search, { target: { value } });
    }
    expect(search).toHaveValue("condotte");
    expect(screen.getByText("2 mappe trovate")).toBeInTheDocument();
    expect(screen.getAllByText("Condotte irrigue")).toHaveLength(2);

    fireEvent.change(search, { target: { value: "particelle" } });
    expect(screen.getByText("1 mappa trovata")).toBeInTheDocument();
    expect(
      screen.getByText("Particelle catastali correnti"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Condotte irrigue")).not.toBeInTheDocument();

    fireEvent.change(search, { target: { value: "vista operativa" } });
    expect(
      screen.getByText("Particelle catastali correnti"),
    ).toBeInTheDocument();

    fireEvent.change(search, { target: { value: "network" } });
    expect(screen.getAllByText("Condotte irrigue")).toHaveLength(2);

    fireEvent.change(search, { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Rete" }));
    expect(screen.getByText("1 mappa trovata")).toBeInTheDocument();
    expect(screen.getByText("Condotte irrigue")).toBeInTheDocument();
    expect(
      screen.queryByText("Particelle catastali correnti"),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Riordino" }));
    expect(screen.getByText("Pratiche di riordino")).toBeInTheDocument();
    expect(screen.getByText(/non contiene una geometria/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Tutte" }));
    fireEvent.change(search, { target: { value: "mappa assente" } });
    expect(screen.getByText("0 mappe trovate")).toBeInTheDocument();
    expect(
      screen.getByText("Nessuna mappa trovata con questi filtri"),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Azzera tutto" }));
    expect(await screen.findByText("5 mappe trovate")).toBeInTheDocument();
    expect(search).toHaveValue("");
  });

  test("renders catalog dashboard health warnings", async () => {
    mocks.getGisCatalogDashboard.mockResolvedValueOnce(warningDashboard);
    mocks.listGisCatalogLayers.mockResolvedValueOnce({
      items: [managedLayer],
      total: 1,
    });

    renderGisCatalogWorkspace();

    expect(await screen.findByText("Health catalogo GIS")).toBeInTheDocument();
    expect(screen.getByText("qgis_edit_policy_missing")).toBeInTheDocument();
    expect(
      screen.getByText("Layer QGIS editabile senza policy controlled."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Nessun export registrato sui layer visibili."),
    ).toBeInTheDocument();
    expect(screen.getByText("1 layer / 1 issue")).toBeInTheDocument();
  });

  test("applies catalog filters through the GIS client", async () => {
    mocks.listGisCatalogLayers
      .mockResolvedValueOnce({ items: [], total: 0 })
      .mockResolvedValueOnce({ items: [catastoLayer], total: 1 })
      .mockResolvedValueOnce({ items: [catastoLayer], total: 1 });

    renderGisCatalogWorkspace();

    expect(
      await screen.findByText("Nessuna mappa trovata con questi filtri"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Catasto" }));
    fireEvent.change(screen.getByLabelText("Dominio"), {
      target: { value: " catasto " },
    });
    fireEvent.change(screen.getByLabelText("Source"), {
      target: { value: " postgis " },
    });
    fireEvent.change(screen.getByLabelText("Ufficiale"), {
      target: { value: " postgis " },
    });
    fireEvent.change(screen.getByLabelText("Stato"), {
      target: { value: "active" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Applica filtri avanzati" }),
    );

    await waitFor(() => {
      expect(mocks.listGisCatalogLayers).toHaveBeenLastCalledWith("token", {
        workspace: "catasto",
        domainModule: "catasto",
        sourceType: "postgis",
        officialSource: "postgis",
        isActive: true,
      });
    });

    fireEvent.change(screen.getByLabelText("Stato"), {
      target: { value: "inactive" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Applica filtri avanzati" }),
    );

    await waitFor(() => {
      expect(mocks.listGisCatalogLayers).toHaveBeenLastCalledWith("token", {
        workspace: "catasto",
        domainModule: "catasto",
        sourceType: "postgis",
        officialSource: "postgis",
        isActive: false,
      });
    });
  });

  test("shows load errors and empty catalog state", async () => {
    mocks.listGisCatalogLayers.mockRejectedValueOnce("backend offline");

    renderGisCatalogWorkspace();

    expect(
      await screen.findByText("Errore caricamento catalogo GIS"),
    ).toBeInTheDocument();

    mocks.listGisCatalogLayers.mockRejectedValueOnce(
      new Error("backend offline"),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Applica filtri avanzati" }),
    );
    expect(await screen.findByText("backend offline")).toBeInTheDocument();

    mocks.listGisCatalogLayers.mockRejectedValueOnce("filter offline");
    fireEvent.click(
      screen.getByRole("button", { name: "Applica filtri avanzati" }),
    );
    expect(
      await screen.findByText("Errore caricamento catalogo GIS"),
    ).toBeInTheDocument();

    mocks.listGisCatalogLayers.mockResolvedValueOnce({ items: [], total: 0 });
    fireEvent.click(screen.getByRole("button", { name: "Azzera tutto" }));

    expect(
      await screen.findByText("Nessuna mappa trovata con questi filtri"),
    ).toBeInTheDocument();
  });

  test("shows initial Error instances from the catalog load", async () => {
    mocks.listGisCatalogLayers.mockRejectedValueOnce(
      new Error("initial backend offline"),
    );

    renderGisCatalogWorkspace();

    expect(
      await screen.findByText("initial backend offline"),
    ).toBeInTheDocument();
  });

  test("manages annotation lifecycle from the catalog layer panel", async () => {
    const updatedAnnotation = {
      ...openAnnotation,
      title: "Nota aggiornata",
      body: "Testo aggiornato",
    };
    const inReviewAnnotation = {
      ...updatedAnnotation,
      status: "in_review" as const,
    };
    const rejectableAnnotation = {
      ...openAnnotation,
      id: "annotation-rejectable",
      title: "Nota da rigettare",
    };
    const rejectedAnnotation = {
      ...rejectableAnnotation,
      status: "rejected" as const,
    };
    mocks.listGisCatalogLayers.mockResolvedValueOnce({
      items: [managedLayer],
      total: 1,
    });
    mocks.listGisLayerAnnotations
      .mockResolvedValueOnce([openAnnotation, closedAnnotation])
      .mockResolvedValueOnce([openAnnotation])
      .mockResolvedValueOnce([openAnnotation])
      .mockResolvedValueOnce([updatedAnnotation, rejectableAnnotation]);
    mocks.createGisLayerAnnotation.mockResolvedValueOnce(openAnnotation);
    mocks.updateGisLayerAnnotation.mockResolvedValueOnce(updatedAnnotation);
    mocks.setGisLayerAnnotationStatus
      .mockResolvedValueOnce(inReviewAnnotation)
      .mockResolvedValueOnce({ ...inReviewAnnotation, status: "closed" })
      .mockResolvedValueOnce(rejectedAnnotation);

    renderGisCatalogWorkspace();

    expect(await screen.findByText("Condotte irrigue")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Apri note" }));
    expect(await screen.findByText("Nota campo")).toBeInTheDocument();
    expect(screen.getByText("Nota chiusa")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Stato note"), {
      target: { value: "open" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Filtra note" }));
    await waitFor(() => {
      expect(mocks.listGisLayerAnnotations).toHaveBeenLastCalledWith(
        "token",
        "layer-rete",
        {
          status: "open",
          featureId: "",
        },
      );
    });

    await screen.findByRole("option", {
      name: "parcel-1 - Condotta principale",
    });
    fireEvent.change(screen.getByLabelText("Elemento della mappa"), {
      target: { value: "parcel-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continua" }));
    fireEvent.click(screen.getByRole("button", { name: "Rivedi nota" }));
    expect(
      screen.getByText("Inserisci un titolo breve e descrivi la nota."),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Titolo breve"), {
      target: { value: " Nuova nota " },
    });
    fireEvent.change(screen.getByLabelText("Descrizione"), {
      target: { value: " Nuovo testo " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Rivedi nota" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Conferma e crea nota" }),
    );
    await waitFor(() => {
      expect(mocks.createGisLayerAnnotation).toHaveBeenCalledWith(
        "token",
        "layer-rete",
        {
          featureId: "parcel-1",
          title: "Nuova nota",
          body: "Nuovo testo",
          attachmentRefs: [],
        },
      );
    });

    fireEvent.click(screen.getByRole("button", { name: "Modifica" }));
    expect(screen.getByLabelText("Elemento della mappa")).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Continua" }));
    fireEvent.change(screen.getByLabelText("Titolo breve"), {
      target: { value: " Nota aggiornata " },
    });
    fireEvent.change(screen.getByLabelText("Descrizione"), {
      target: { value: " Testo aggiornato " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Rivedi nota" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Conferma aggiornamento" }),
    );
    await waitFor(() => {
      expect(mocks.updateGisLayerAnnotation).toHaveBeenCalledWith(
        "token",
        "layer-rete",
        "annotation-open",
        {
          title: "Nota aggiornata",
          body: "Testo aggiornato",
        },
      );
    });

    fireEvent.click(screen.getAllByRole("button", { name: "In revisione" })[0]);
    await waitFor(() => {
      expect(mocks.setGisLayerAnnotationStatus).toHaveBeenCalledWith(
        "token",
        "layer-rete",
        "annotation-open",
        "in_review",
      );
    });
    fireEvent.click(screen.getAllByRole("button", { name: "Chiudi" })[0]);
    await waitFor(() => {
      expect(mocks.setGisLayerAnnotationStatus).toHaveBeenCalledWith(
        "token",
        "layer-rete",
        "annotation-open",
        "closed",
      );
    });
    fireEvent.click(screen.getAllByRole("button", { name: "Rigetta" })[0]);
    await waitFor(() => {
      expect(mocks.setGisLayerAnnotationStatus).toHaveBeenCalledWith(
        "token",
        "layer-rete",
        "annotation-rejectable",
        "rejected",
      );
    });

    fireEvent.click(screen.getByRole("button", { name: "Chiudi note" }));
    expect(screen.queryByText("Nota campo")).not.toBeInTheDocument();
  });

  test("renders read-only annotations and hides the panel entry point without view access", async () => {
    const hiddenLayer: GisCatalogLayer = {
      ...catastoLayer,
      id: "layer-hidden",
      title: "Layer riservato",
      can_view: false,
    };
    const readOnlyLayer: GisCatalogLayer = {
      ...catastoLayer,
      id: "layer-readonly",
      workspace: "rete",
      domain_module: "network",
      title: "Layer note read-only",
    };
    mocks.listGisCatalogLayers.mockResolvedValueOnce({
      items: [hiddenLayer, readOnlyLayer],
      total: 2,
    });
    mocks.listGisLayerAnnotations.mockResolvedValueOnce([detachedAnnotation]);
    mocks.listGisChangeRequests.mockResolvedValueOnce([submittedChangeRequest]);

    renderGisCatalogWorkspace();

    expect(await screen.findByText("Layer riservato")).toBeInTheDocument();
    expect(screen.getByText("Layer note read-only")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Apri note" })).toHaveLength(
      1,
    );
    expect(
      screen.getAllByRole("button", { name: "Proponi/vedi modifiche" }),
    ).toHaveLength(1);

    fireEvent.click(screen.getByRole("button", { name: "Apri note" }));

    expect(await screen.findByText("Nota senza feature")).toBeInTheDocument();
    expect(screen.getByText("feature non associata")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Crea nota" }),
    ).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Proponi/vedi modifiche" }),
    );
    expect(await screen.findByText("Rilievo tecnico")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Crea richiesta" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Note revisione")).not.toBeInTheDocument();
  });

  test("shows annotation load, save and status errors", async () => {
    mocks.listGisCatalogLayers.mockResolvedValueOnce({
      items: [managedLayer],
      total: 1,
    });
    mocks.listGisLayerAnnotations
      .mockRejectedValueOnce("annotations offline")
      .mockRejectedValueOnce(new Error("annotations denied"))
      .mockResolvedValueOnce([detachedAnnotation]);
    mocks.createGisLayerAnnotation
      .mockRejectedValueOnce("save offline")
      .mockRejectedValueOnce(new Error("save denied"));
    mocks.setGisLayerAnnotationStatus
      .mockRejectedValueOnce(new Error("status denied"))
      .mockRejectedValueOnce("status offline");

    renderGisCatalogWorkspace();

    expect(await screen.findByText("Condotte irrigue")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Apri note" }));
    expect(
      await screen.findByText("Errore caricamento annotazioni GIS"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi note" }));
    fireEvent.click(screen.getByRole("button", { name: "Apri note" }));
    expect(await screen.findByText("annotations denied")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Continua" }));
    fireEvent.change(screen.getByLabelText("Titolo breve"), {
      target: { value: "Nota" },
    });
    fireEvent.change(screen.getByLabelText("Descrizione"), {
      target: { value: "Testo" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Rivedi nota" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Conferma e crea nota" }),
    );
    expect(
      await screen.findByText("Errore salvataggio annotazione GIS"),
    ).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Conferma e crea nota" }),
    );
    expect(await screen.findByText("save denied")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Filtra note" }));
    expect(await screen.findByText("Nota senza feature")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Modifica" }));
    expect(screen.getByLabelText("Elemento della mappa")).toHaveValue("");
    fireEvent.click(screen.getByRole("button", { name: "In revisione" }));
    expect(await screen.findByText("status denied")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "In revisione" }));
    expect(
      await screen.findByText("Errore stato annotazione GIS"),
    ).toBeInTheDocument();
  });

  test("manages change request workflow from the catalog layer panel", async () => {
    const rejectableChangeRequest = {
      ...submittedChangeRequest,
      id: "change-rejectable",
      feature_id: null,
      justification: null,
    };
    const updatedChangeRequest = {
      ...submittedChangeRequest,
      payload: { before: { coltura: "grano" }, after: { coltura: "riso" } },
      justification: "Dato aggiornato",
    };
    mocks.listGisCatalogLayers.mockResolvedValueOnce({
      items: [managedLayer],
      total: 1,
    });
    mocks.listGisChangeRequests
      .mockResolvedValueOnce([
        submittedChangeRequest,
        approvedChangeRequest,
        rejectableChangeRequest,
      ])
      .mockResolvedValueOnce([approvedChangeRequest])
      .mockResolvedValueOnce([
        submittedChangeRequest,
        approvedChangeRequest,
        rejectableChangeRequest,
      ])
      .mockResolvedValueOnce([
        updatedChangeRequest,
        approvedChangeRequest,
        rejectableChangeRequest,
      ]);
    mocks.createGisLayerChangeRequest.mockResolvedValueOnce(
      submittedChangeRequest,
    );
    mocks.updateGisChangeRequest.mockResolvedValueOnce(updatedChangeRequest);
    mocks.setGisChangeRequestStatus
      .mockResolvedValueOnce({
        ...submittedChangeRequest,
        status: "needs_changes",
        review_notes: "integra",
      })
      .mockResolvedValueOnce({
        ...submittedChangeRequest,
        status: "approved",
        review_notes: "validata",
      })
      .mockResolvedValueOnce({ ...submittedChangeRequest, status: "applied" })
      .mockResolvedValueOnce({
        ...rejectableChangeRequest,
        status: "rejected",
      });

    renderGisCatalogWorkspace();

    expect(await screen.findByText("Condotte irrigue")).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Proponi/vedi modifiche" }),
    );
    expect(await screen.findByText("Rilievo tecnico")).toBeInTheDocument();
    expect(screen.getAllByText(/Diff attributi/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Nuova feature/)).toBeInTheDocument();
    expect(screen.getByText("Review: validata")).toBeInTheDocument();
    expect(
      screen.getAllByText("Richiesta senza motivazione").length,
    ).toBeGreaterThan(0);

    fireEvent.click(
      screen.getAllByRole("button", { name: "Modifica richiesta" })[1],
    );
    fireEvent.click(screen.getByRole("button", { name: "Annulla modifica" }));

    fireEvent.change(screen.getByLabelText("Stato richiesta"), {
      target: { value: "approved" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Filtra richieste" }));
    await waitFor(() => {
      expect(mocks.listGisChangeRequests).toHaveBeenLastCalledWith("token", {
        layerId: "layer-rete",
        status: "approved",
      });
    });

    await screen.findByRole("option", {
      name: "parcel-1 - Condotta principale",
    });
    fireEvent.change(screen.getByLabelText("Elemento della mappa"), {
      target: { value: "parcel-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continua" }));
    fireEvent.change(screen.getByLabelText("Dato da correggere"), {
      target: { value: "coltura" },
    });
    fireEvent.change(screen.getByLabelText("Nuovo valore"), {
      target: { value: "mais" },
    });
    fireEvent.change(screen.getByLabelText("Motivazione"), {
      target: { value: " Rilievo " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Rivedi richiesta" }));
    fireEvent.click(screen.getByRole("button", { name: "Conferma e invia" }));
    await waitFor(() => {
      expect(mocks.createGisLayerChangeRequest).toHaveBeenCalledWith(
        "token",
        "layer-rete",
        {
          featureId: "parcel-1",
          changeType: "attribute_update",
          payload: { before: { coltura: "grano" }, after: { coltura: "mais" } },
          justification: "Rilievo",
        },
      );
    });

    fireEvent.click(
      screen.getAllByRole("button", { name: "Modifica richiesta" })[0],
    );
    fireEvent.click(screen.getByRole("button", { name: "Continua" }));
    expect(
      await screen.findByText("Descrivi la correzione"),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Nuovo valore"), {
      target: { value: "riso" },
    });
    fireEvent.change(screen.getByLabelText("Motivazione"), {
      target: { value: " Dato aggiornato " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Rivedi richiesta" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Conferma aggiornamento" }),
    );
    await waitFor(() => {
      expect(mocks.updateGisChangeRequest).toHaveBeenCalledWith(
        "token",
        "change-submitted",
        {
          featureId: "parcel-1",
          changeType: "attribute_update",
          payload: { before: { coltura: "grano" }, after: { coltura: "riso" } },
          justification: "Dato aggiornato",
        },
      );
    });

    fireEvent.change(screen.getByLabelText("Note revisione"), {
      target: { value: " integra " },
    });
    fireEvent.click(
      screen.getAllByRole("button", { name: "Richiedi modifiche" })[0],
    );
    await waitFor(() => {
      expect(mocks.setGisChangeRequestStatus).toHaveBeenCalledWith(
        "token",
        "change-submitted",
        "needs_changes",
        " integra ",
      );
    });
    fireEvent.change(screen.getByLabelText("Note revisione"), {
      target: { value: " valida " },
    });
    fireEvent.click(screen.getAllByRole("button", { name: "Approva" })[0]);
    await waitFor(() => {
      expect(mocks.setGisChangeRequestStatus).toHaveBeenCalledWith(
        "token",
        "change-submitted",
        "approved",
        " valida ",
      );
    });
    fireEvent.click(
      screen.getAllByRole("button", { name: "Applica richiesta" })[0],
    );
    expect(
      screen.getByRole("dialog", { name: "Applicare questa modifica?" }),
    ).toHaveTextContent("dati PostGIS possono cambiare");
    fireEvent.click(screen.getByRole("button", { name: "Annulla" }));
    expect(screen.queryByRole("dialog", { name: "Applicare questa modifica?" })).not.toBeInTheDocument();
    fireEvent.click(
      screen.getAllByRole("button", { name: "Applica richiesta" })[0],
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Conferma applicazione" }),
    );
    await waitFor(() => {
      expect(mocks.setGisChangeRequestStatus).toHaveBeenCalledWith(
        "token",
        "change-submitted",
        "applied",
        "",
      );
    });
    fireEvent.click(screen.getByRole("button", { name: "Chiudi messaggio" }));
    fireEvent.click(screen.getByRole("button", { name: "Rigetta richiesta" }));
    await waitFor(() => {
      expect(mocks.setGisChangeRequestStatus).toHaveBeenCalledWith(
        "token",
        "change-rejectable",
        "rejected",
        "",
      );
    });

    fireEvent.click(screen.getByRole("button", { name: "Chiudi modifiche" }));
    expect(screen.queryByText("Rilievo tecnico")).not.toBeInTheDocument();
  });

  test("shows change request load, save and status errors", async () => {
    mocks.listGisCatalogLayers.mockResolvedValueOnce({
      items: [managedLayer],
      total: 1,
    });
    mocks.listGisChangeRequests
      .mockRejectedValueOnce("change requests offline")
      .mockRejectedValueOnce(new Error("change requests denied"))
      .mockResolvedValueOnce([submittedChangeRequest]);
    mocks.createGisLayerChangeRequest
      .mockRejectedValueOnce("save offline")
      .mockRejectedValueOnce(new Error("save denied"));
    mocks.setGisChangeRequestStatus
      .mockRejectedValueOnce(new Error("status denied"))
      .mockRejectedValueOnce("status offline");

    renderGisCatalogWorkspace();

    expect(await screen.findByText("Condotte irrigue")).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Proponi/vedi modifiche" }),
    );
    expect(
      await screen.findByText("Errore caricamento change request GIS"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi modifiche" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Proponi/vedi modifiche" }),
    );
    expect(
      await screen.findByText("change requests denied"),
    ).toBeInTheDocument();

    await screen.findByRole("option", {
      name: "parcel-1 - Condotta principale",
    });
    fireEvent.change(screen.getByLabelText("Elemento della mappa"), {
      target: { value: "parcel-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continua" }));
    fireEvent.click(screen.getByRole("button", { name: "Rivedi richiesta" }));
    expect(
      screen.getByText("Spiega il motivo della richiesta prima di continuare."),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Dato da correggere"), {
      target: { value: "coltura" },
    });
    fireEvent.change(screen.getByLabelText("Nuovo valore"), {
      target: { value: "mais" },
    });
    fireEvent.change(screen.getByLabelText("Motivazione"), {
      target: { value: "Rilievo" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Rivedi richiesta" }));
    fireEvent.click(screen.getByRole("button", { name: "Conferma e invia" }));
    expect(
      await screen.findByText("Errore salvataggio change request GIS"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Conferma e invia" }));
    expect(await screen.findByText("save denied")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Filtra richieste" }));
    expect(await screen.findByText("Rilievo tecnico")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Richiedi modifiche" }));
    expect(await screen.findByText("status denied")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Richiedi modifiche" }));
    expect(
      await screen.findByText("Errore stato change request GIS"),
    ).toBeInTheDocument();
  });

  test("keeps the confirmation open when applying a change fails", async () => {
    mocks.listGisCatalogLayers.mockResolvedValueOnce({ items: [managedLayer], total: 1 });
    mocks.listGisChangeRequests.mockResolvedValueOnce([approvedChangeRequest]);
    mocks.setGisChangeRequestStatus.mockRejectedValueOnce(new Error("apply denied"));
    renderGisCatalogWorkspace();

    expect(await screen.findByText("Condotte irrigue")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Proponi/vedi modifiche" }));
    expect(await screen.findByText("Review: validata")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Applica richiesta" }));
    fireEvent.click(screen.getByRole("button", { name: "Conferma applicazione" }));
    expect(await screen.findByText("Operazione non completata. Controlla il messaggio di errore e riprova.")).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Applicare questa modifica?" })).toBeInTheDocument();
  });

  test("wraps the catalog workspace in the protected GIS page", async () => {
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.listGisCatalogLayers.mockResolvedValueOnce({ items: [], total: 0 });

    render(<GisCatalogPage />);

    const wrapper = screen.getByTestId("protected-page");
    expect(wrapper).toHaveAttribute("data-title", "GIS Platform");
    expect(wrapper).toHaveAttribute("data-required-module", "gis");
    expect(wrapper.querySelector(".gis-touch-targets")).toBeInTheDocument();
    expect(
      await screen.findByText("Nessuna mappa trovata con questi filtri"),
    ).toBeInTheDocument();
  });
});
