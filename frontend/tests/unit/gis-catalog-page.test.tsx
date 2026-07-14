import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import GisCatalogPage, { GisCatalogWorkspace } from "@/app/gis/catalogo/page";
import type { GisCatalogLayer } from "@/types/gis";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  listGisCatalogLayers: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: ReactNode; className?: string }) => (
    <a href={href} className={className}>
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
    <section data-testid="protected-page" data-title={title} data-required-module={requiredModule}>
      {children}
    </section>
  ),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: () => mocks.getStoredAccessToken(),
}));

vi.mock("@/lib/api/gis", () => ({
  listGisCatalogLayers: (...args: unknown[]) => mocks.listGisCatalogLayers(...args),
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

describe("GisCatalogPage", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReset();
    mocks.listGisCatalogLayers.mockReset();
  });

  test("renders a session loading card before the token is available", () => {
    render(<GisCatalogWorkspace token={null} />);

    expect(screen.getByText("Sessione catalogo in caricamento.")).toBeInTheDocument();
    expect(mocks.listGisCatalogLayers).not.toHaveBeenCalled();
  });

  test("loads catalog layers and renders read-only metadata", async () => {
    mocks.listGisCatalogLayers.mockResolvedValueOnce({ items: [catastoLayer, reteLayer], total: 2 });

    render(<GisCatalogWorkspace token="token" />);

    expect(await screen.findByText("Particelle catastali correnti")).toBeInTheDocument();
    expect(screen.getByText("Condotte irrigue")).toBeInTheDocument();
    expect(screen.getByText("public.cat_particelle_current")).toBeInTheDocument();
    expect(screen.getByText("read_only")).toBeInTheDocument();
    expect(screen.getByText("martin")).toBeInTheDocument();
    expect(screen.getAllByText("Non configurato").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Apri workspace Catasto" })).toHaveAttribute("href", "/catasto/gis");
    expect(mocks.listGisCatalogLayers).toHaveBeenCalledWith("token");
  });

  test("applies catalog filters through the GIS client", async () => {
    mocks.listGisCatalogLayers
      .mockResolvedValueOnce({ items: [], total: 0 })
      .mockResolvedValueOnce({ items: [catastoLayer], total: 1 })
      .mockResolvedValueOnce({ items: [catastoLayer], total: 1 });

    render(<GisCatalogWorkspace token="token" />);

    expect(await screen.findByText("Nessun layer nel filtro corrente")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Workspace"), { target: { value: " catasto " } });
    fireEvent.change(screen.getByLabelText("Dominio"), { target: { value: " catasto " } });
    fireEvent.change(screen.getByLabelText("Source"), { target: { value: " postgis " } });
    fireEvent.change(screen.getByLabelText("Ufficiale"), { target: { value: " postgis " } });
    fireEvent.change(screen.getByLabelText("Stato"), { target: { value: "active" } });
    fireEvent.click(screen.getByRole("button", { name: "Applica filtri" }));

    await waitFor(() => {
      expect(mocks.listGisCatalogLayers).toHaveBeenLastCalledWith("token", {
        workspace: "catasto",
        domainModule: "catasto",
        sourceType: "postgis",
        officialSource: "postgis",
        isActive: true,
      });
    });

    fireEvent.change(screen.getByLabelText("Stato"), { target: { value: "inactive" } });
    fireEvent.click(screen.getByRole("button", { name: "Applica filtri" }));

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

    render(<GisCatalogWorkspace token="token" />);

    expect(await screen.findByText("Errore caricamento catalogo GIS")).toBeInTheDocument();

    mocks.listGisCatalogLayers.mockRejectedValueOnce(new Error("backend offline"));
    fireEvent.click(screen.getByRole("button", { name: "Applica filtri" }));
    expect(await screen.findByText("backend offline")).toBeInTheDocument();

    mocks.listGisCatalogLayers.mockRejectedValueOnce("filter offline");
    fireEvent.click(screen.getByRole("button", { name: "Applica filtri" }));
    expect(await screen.findByText("Errore caricamento catalogo GIS")).toBeInTheDocument();

    mocks.listGisCatalogLayers.mockResolvedValueOnce({ items: [], total: 0 });
    fireEvent.click(screen.getByRole("button", { name: "Reset" }));

    expect(await screen.findByText("Nessun layer nel filtro corrente")).toBeInTheDocument();
  });

  test("shows initial Error instances from the catalog load", async () => {
    mocks.listGisCatalogLayers.mockRejectedValueOnce(new Error("initial backend offline"));

    render(<GisCatalogWorkspace token="token" />);

    expect(await screen.findByText("initial backend offline")).toBeInTheDocument();
  });

  test("wraps the catalog workspace in the protected GIS page", async () => {
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.listGisCatalogLayers.mockResolvedValueOnce({ items: [], total: 0 });

    render(<GisCatalogPage />);

    const wrapper = screen.getByTestId("protected-page");
    expect(wrapper).toHaveAttribute("data-title", "GIS Platform");
    expect(wrapper).toHaveAttribute("data-required-module", "catasto");
    expect(await screen.findByText("Nessun layer nel filtro corrente")).toBeInTheDocument();
  });
});
