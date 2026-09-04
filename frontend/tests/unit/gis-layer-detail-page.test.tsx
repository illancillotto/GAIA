import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import GisLayerDetailPage from "@/app/gis/catalogo/[layerId]/page";
import { GisLayerDetailWorkspace } from "@/app/gis/catalogo/[layerId]/layer-detail-workspace";
import type { GisCatalogLayer } from "@/types/gis";

const mocks = vi.hoisted(() => ({
  getGisCatalogLayer: vi.fn(),
  getStoredAccessToken: vi.fn(),
  layerId: "layer-1",
}));

vi.mock("next/navigation", () => ({ useParams: () => ({ layerId: mocks.layerId }) }));
vi.mock("next/link", () => ({ default: ({ href, children, className }: { href: string; children: ReactNode; className?: string }) => <a href={href} className={className}>{children}</a> }));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ title, requiredModule, children }: { title: string; requiredModule: string; children: ReactNode }) => <section data-testid="protected-page" data-title={title} data-module={requiredModule}>{children}</section>,
}));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: () => mocks.getStoredAccessToken() }));
vi.mock("@/lib/api/gis", () => ({ getGisCatalogLayer: (...args: unknown[]) => mocks.getGisCatalogLayer(...args) }));
vi.mock("@/app/gis/catalogo/layer-viewer", () => ({ GisLayerViewer: ({ layer }: { layer: GisCatalogLayer }) => <div data-testid="layer-viewer">Viewer {layer.title}</div> }));

const geometricLayer = {
  id: "layer-1",
  workspace: "rete",
  name: "rete_condotte",
  title: "Condotte irrigue",
  description: "Rete principale",
  domain_module: "network",
  source_type: "postgis",
  official_source: "postgis",
  postgis_schema: "network",
  postgis_table: "rete_condotte",
  geometry_type: "MULTILINESTRING",
  srid: 4326,
  feature_id_column: "id",
  martin_layer_id: null,
  metadata: {},
  is_active: true,
  effective_access_level: "editor",
  can_view: true,
  can_annotate: true,
  can_edit: true,
  can_approve: false,
  can_manage: false,
  created_at: "2026-08-25T08:00:00Z",
  updated_at: "2026-08-25T08:00:00Z",
} satisfies GisCatalogLayer;

describe("GIS layer detail page", () => {
  beforeEach(() => {
    mocks.getGisCatalogLayer.mockReset();
    mocks.getStoredAccessToken.mockReset();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.layerId = "layer-1";
  });

  test("loads a geometric layer into the real map detail", async () => {
    mocks.getGisCatalogLayer.mockResolvedValue(geometricLayer);
    render(<GisLayerDetailPage />);

    expect(screen.getByTestId("protected-page")).toHaveAttribute("data-module", "gis");
    expect(screen.getByTestId("protected-page").querySelector(".gis-touch-targets")).toBeInTheDocument();
    expect(await screen.findByText("Condotte irrigue")).toBeInTheDocument();
    expect(screen.getByTestId("layer-viewer").closest(".gis-touch-targets")).toBeInTheDocument();
    expect(screen.getByTestId("layer-viewer")).toHaveTextContent("Viewer Condotte irrigue");
    expect(screen.getByRole("link", { name: "Torna al catalogo" })).toHaveAttribute("href", "/gis/catalogo");
    expect(screen.getByRole("link", { name: "Torna al catalogo" })).toHaveClass("btn-secondary");
    expect(screen.getByText("Puoi proporre modifiche")).toBeInTheDocument();
    expect(screen.getByText("MULTILINESTRING")).toBeInTheDocument();
    expect(mocks.getGisCatalogLayer).toHaveBeenCalledWith("token", "layer-1");
  });

  test("redirects non-geometric registries to their domain context", async () => {
    mocks.getGisCatalogLayer.mockResolvedValue({
      ...geometricLayer,
      id: "registry-1",
      workspace: "riordino",
      domain_module: "riordino",
      title: "Collegamenti riordino",
      description: null,
      source_type: "domain_registry",
      geometry_type: null,
      srid: null,
      postgis_table: null,
      feature_id_column: null,
      effective_access_level: "viewer",
      can_annotate: false,
      can_edit: false,
    });
    render(<GisLayerDetailWorkspace token="token" layerId="registry-1" />);

    expect(await screen.findByText("Questo elemento non contiene una geometria")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Apri modulo Riordino" })).toHaveAttribute("href", "/riordino");
    expect(screen.getAllByText("Non disponibile").length).toBeGreaterThan(0);
    expect(screen.getByText("Puoi consultare")).toBeInTheDocument();
  });

  test("renders inactive annotatable maps and registries without a domain destination", async () => {
    mocks.getGisCatalogLayer.mockResolvedValueOnce({
      ...geometricLayer,
      is_active: false,
      description: null,
      can_edit: false,
      can_annotate: true,
    });
    const inactive = render(<GisLayerDetailWorkspace token="token" layerId="layer-1" />);
    expect(await screen.findByText(/Mappa non attiva/)).toBeInTheDocument();
    expect(screen.getByText("Nessuna descrizione disponibile per questa mappa.")).toBeInTheDocument();
    expect(screen.getByText("Puoi aggiungere note")).toBeInTheDocument();
    inactive.unmount();

    mocks.getGisCatalogLayer.mockResolvedValueOnce({
      ...geometricLayer,
      workspace: "ambiente",
      domain_module: "ambiente",
      source_type: "domain_registry",
      geometry_type: null,
    });
    render(<GisLayerDetailWorkspace token="token" layerId="registry-unknown" />);
    expect(await screen.findByText("Questo elemento non contiene una geometria")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Apri modulo/ })).not.toBeInTheDocument();
  });

  test("shows the not-found fallback for an empty successful response", async () => {
    mocks.getGisCatalogLayer.mockResolvedValueOnce(null);
    render(<GisLayerDetailWorkspace token="token" layerId="missing" />);
    expect(await screen.findByText("Mappa non trovata")).toBeInTheDocument();
  });

  test("shows session loading and backend errors", async () => {
    const { unmount } = render(<GisLayerDetailWorkspace token={null} layerId="layer-1" />);
    expect(screen.getByText("Caricamento dettaglio mappa...")).toBeInTheDocument();
    unmount();

    mocks.getGisCatalogLayer.mockRejectedValueOnce(new Error("mappa offline"));
    const failed = render(<GisLayerDetailWorkspace token="token" layerId="layer-1" />);
    expect(await screen.findByText("mappa offline")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Torna al catalogo" })).toHaveAttribute("href", "/gis/catalogo");
    failed.unmount();

    mocks.getGisCatalogLayer.mockRejectedValueOnce("offline");
    render(<GisLayerDetailWorkspace token="token" layerId="layer-2" />);
    expect(await screen.findByText("Dettaglio mappa non disponibile")).toBeInTheDocument();
  });

  test("ignores a response after unmount", async () => {
    let resolveLayer: (layer: GisCatalogLayer) => void = () => undefined;
    mocks.getGisCatalogLayer.mockReturnValue(new Promise((resolve) => { resolveLayer = resolve; }));
    const { unmount } = render(<GisLayerDetailWorkspace token="token" layerId="layer-1" />);
    unmount();
    resolveLayer(geometricLayer);
    await waitFor(() => expect(mocks.getGisCatalogLayer).toHaveBeenCalled());

    let rejectLayer: (reason: unknown) => void = () => undefined;
    mocks.getGisCatalogLayer.mockReturnValueOnce(new Promise((_, reject) => { rejectLayer = reject; }));
    const rejected = render(<GisLayerDetailWorkspace token="token" layerId="layer-2" />);
    rejected.unmount();
    rejectLayer(new Error("late error"));
    await waitFor(() => expect(mocks.getGisCatalogLayer).toHaveBeenCalledTimes(2));
  });
});
