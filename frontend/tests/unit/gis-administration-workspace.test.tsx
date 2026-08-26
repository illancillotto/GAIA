import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { GisAdministrationWorkspace } from "@/app/gis/amministrazione/administration-workspace";
import type { GisCatalogLayer } from "@/types/gis";

const mocks = vi.hoisted(() => ({
  createGisCatalogLayer: vi.fn(),
  getGisQgisGovernance: vi.fn(),
  listGisCatalogLayers: vi.fn(),
  requestGisCatalogLayerExport: vi.fn(),
  setGisCatalogLayerActive: vi.fn(),
  updateGisCatalogLayerMetadata: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: ReactNode; className?: string }) =>
    <a href={href} className={className}>{children}</a>,
}));

vi.mock("@/lib/api/gis", () => ({
  createGisCatalogLayer: (...args: unknown[]) => mocks.createGisCatalogLayer(...args),
  getGisQgisGovernance: (...args: unknown[]) => mocks.getGisQgisGovernance(...args),
  listGisCatalogLayers: (...args: unknown[]) => mocks.listGisCatalogLayers(...args),
  requestGisCatalogLayerExport: (...args: unknown[]) => mocks.requestGisCatalogLayerExport(...args),
  setGisCatalogLayerActive: (...args: unknown[]) => mocks.setGisCatalogLayerActive(...args),
  updateGisCatalogLayerMetadata: (...args: unknown[]) => mocks.updateGisCatalogLayerMetadata(...args),
}));

vi.mock("@/app/gis/amministrazione/permissions-panel", () => ({
  GisPermissionsPanel: () => <div>Permessi assistiti</div>,
}));
vi.mock("@/app/gis/strumenti/activity-center", () => ({
  GisActivityCenter: () => <div>Storico amministrativo</div>,
}));
vi.mock("@/app/gis/catalogo/runtime-health-panel", () => ({
  GisRuntimeHealthPanel: () => <div>Stato servizi runtime</div>,
}));

const layer = {
  id: "layer-1",
  workspace: "rete",
  name: "rete_condotte",
  title: "Condotte irrigue",
  description: "Rete principale",
  domain_module: "network",
  source_type: "postgis",
  official_source: "postgis",
  postgis_schema: "network",
  postgis_table: "condotte",
  geometry_column: "geometry",
  geometry_type: "MULTILINESTRING",
  srid: 4326,
  feature_id_column: "id",
  martin_layer_id: "rete_condotte",
  ogc_service_url: "https://gis.test/ogc",
  qgis_project_path: "/qgis/rete.qgz",
  nas_export_root: "/nas/gis/rete",
  metadata: {},
  is_active: true,
  effective_access_level: "admin",
  can_view: true,
  can_annotate: true,
  can_edit: true,
  can_approve: true,
  can_manage: true,
  created_at: "2026-08-25T08:00:00Z",
  updated_at: "2026-08-25T08:00:00Z",
} satisfies GisCatalogLayer;

const governance = {
  schema: "gis_qgis",
  roles: {},
  connection_policy: {},
  layers: [{ layer_id: layer.id, workspace: "rete", layer_name: layer.name, source_table: "network.condotte", view_name: "rete_condotte", read_role: "gis_read", editable: false, edit_reason: "read only" }],
  statements: ["CREATE VIEW"],
  sql: "CREATE VIEW gis_qgis.rete_condotte AS SELECT * FROM network.condotte;",
};

describe("GisAdministrationWorkspace", () => {
  beforeEach(() => {
    Object.values(mocks).forEach((mock) => mock.mockReset());
    mocks.listGisCatalogLayers.mockResolvedValue({ items: [layer], total: 1 });
    mocks.getGisQgisGovernance.mockResolvedValue(governance);
  });

  test("shows the session/loading state and loads all administrative sections", async () => {
    const first = render(<GisAdministrationWorkspace token={null} />);
    expect(screen.getByText("Caricamento amministrazione GIS...")).toBeInTheDocument();
    expect(mocks.listGisCatalogLayers).not.toHaveBeenCalled();
    first.unmount();

    render(<GisAdministrationWorkspace token="token" />);
    expect(await screen.findByText("Registra una mappa PostGIS")).toBeInTheDocument();
    expect(screen.getByText("Permessi assistiti")).toBeInTheDocument();
    expect(screen.getByText("Storico amministrativo")).toBeInTheDocument();
    expect(screen.getByText("Stato servizi runtime")).toBeInTheDocument();
    expect(screen.getByText("gis_qgis")).toBeInTheDocument();
    expect(screen.getByText(/CREATE VIEW gis_qgis/)).toBeInTheDocument();
  });

  test("validates and registers a new PostGIS map", async () => {
    const created = { ...layer, id: "layer-2", name: "rete_valvole", title: "Valvole", description: null, ogc_service_url: null, qgis_project_path: null, nas_export_root: null };
    mocks.createGisCatalogLayer.mockResolvedValue(created);
    render(<GisAdministrationWorkspace token="token" />);
    await screen.findByText("Registra una mappa PostGIS");

    fireEvent.click(screen.getByRole("button", { name: "Registra nuova mappa" }));
    expect(screen.getByText(/Compila area, nome, titolo/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Area di lavoro"), { target: { value: " rete " } });
    fireEvent.change(screen.getByLabelText("Nome tecnico"), { target: { value: " rete_valvole " } });
    fireEvent.change(screen.getAllByLabelText("Titolo visibile")[0], { target: { value: "Valvole" } });
    fireEvent.change(screen.getByLabelText("Dominio responsabile"), { target: { value: "network_ops" } });
    fireEvent.change(screen.getByLabelText("Fonte ufficiale"), { target: { value: "rilievo" } });
    fireEvent.change(screen.getByLabelText("Tabella PostGIS"), { target: { value: "valvole" } });
    fireEvent.change(screen.getByLabelText("Descrizione per gli utenti"), { target: { value: "Valvole di rete" } });
    fireEvent.change(screen.getByLabelText("Schema PostGIS"), { target: { value: "network_ops" } });
    fireEvent.change(screen.getByLabelText("Colonna geometria"), { target: { value: "geom" } });
    fireEvent.change(screen.getByLabelText("Tipo geometria"), { target: { value: "POINT" } });
    fireEvent.change(screen.getByLabelText("Sistema coordinate (SRID)"), { target: { value: "3003" } });
    fireEvent.change(screen.getByLabelText("Campo identificativo"), { target: { value: "gid" } });
    fireEvent.change(screen.getByLabelText("Layer tile Martin (facoltativo)"), { target: { value: "rete_valvole" } });
    fireEvent.click(screen.getByRole("button", { name: "Registra nuova mappa" }));

    await waitFor(() => expect(mocks.createGisCatalogLayer).toHaveBeenCalledWith("token", expect.objectContaining({
      name: "rete_valvole",
      title: "Valvole",
      postgisTable: "valvole",
      srid: 3003,
      geometryColumn: "geom",
      geometryType: "POINT",
      featureIdColumn: "gid",
    })));
    expect(screen.getByText("Valvole è stato aggiunto al catalogo.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi messaggio" }));
    expect(screen.queryByText("Valvole è stato aggiunto al catalogo.")).not.toBeInTheDocument();
  });

  test("updates metadata, lifecycle and governed exports with confirmations", async () => {
    const untouchedLayer = { ...layer, id: "layer-other", title: "Canali secondari" };
    mocks.listGisCatalogLayers.mockResolvedValueOnce({ items: [layer, untouchedLayer], total: 2 });
    mocks.updateGisCatalogLayerMetadata.mockResolvedValue({ ...layer, title: "Condotte aggiornate" });
    mocks.setGisCatalogLayerActive.mockResolvedValue({ ...layer, is_active: false });
    mocks.requestGisCatalogLayerExport.mockResolvedValue({
      id: "export-1", layer_id: layer.id, version_label: "v2026", status: "completed",
      nas_path: "/nas/gis/rete/v2026.zip", checksum_sha256: "abc", metadata: {}, created_at: "2026-08-25T10:00:00Z",
    });
    render(<GisAdministrationWorkspace token="token" />);
    await screen.findByText("Informazioni, disponibilità ed export");

    fireEvent.change(screen.getAllByLabelText("Titolo visibile")[1], { target: { value: "Condotte aggiornate" } });
    fireEvent.change(screen.getByLabelText("Descrizione"), { target: { value: "Descrizione aggiornata" } });
    fireEvent.change(screen.getByLabelText("URL servizio OGC (facoltativo)"), { target: { value: "https://new.test/ogc" } });
    fireEvent.change(screen.getByLabelText("Percorso progetto QGIS (facoltativo)"), { target: { value: "/qgis/new.qgz" } });
    fireEvent.change(screen.getByLabelText("Cartella NAS export"), { target: { value: "/nas/new" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva informazioni" }));
    await waitFor(() => expect(mocks.updateGisCatalogLayerMetadata).toHaveBeenCalledWith("token", layer.id, expect.objectContaining({ title: "Condotte aggiornate" })));

    fireEvent.click(screen.getByRole("button", { name: "Rendi non attiva" }));
    expect(mocks.setGisCatalogLayerActive).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Conferma disattivazione" }));
    await waitFor(() => expect(mocks.setGisCatalogLayerActive).toHaveBeenCalledWith("token", layer.id, false));

    mocks.setGisCatalogLayerActive.mockResolvedValueOnce({ ...layer, is_active: true });
    fireEvent.click(screen.getByRole("button", { name: "Riattiva mappa" }));
    fireEvent.click(screen.getByRole("button", { name: "Conferma riattivazione" }));
    await waitFor(() => expect(mocks.setGisCatalogLayerActive).toHaveBeenLastCalledWith("token", layer.id, true));

    fireEvent.change(screen.getByLabelText("Etichetta versione (facoltativa)"), { target: { value: "v2026" } });
    fireEvent.change(screen.getByLabelText("Cartella NAS (facoltativa se già configurata)"), { target: { value: "/nas/override" } });
    fireEvent.click(screen.getByRole("button", { name: "Crea export shapefile" }));
    await waitFor(() => expect(mocks.requestGisCatalogLayerExport).toHaveBeenCalledWith("token", layer.id, expect.objectContaining({ versionLabel: "v2026" })));
    expect(screen.getByText("/nas/gis/rete/v2026.zip")).toBeInTheDocument();
    expect(screen.getByText("abc")).toBeInTheDocument();
    mocks.requestGisCatalogLayerExport.mockResolvedValueOnce({
      id: "export-2", layer_id: layer.id, version_label: "v2027", status: "completed",
      nas_path: "/nas/gis/rete/v2027.zip", checksum_sha256: null, metadata: {}, created_at: "2026-08-25T11:00:00Z",
    });
    fireEvent.click(screen.getByRole("button", { name: "Crea export shapefile" }));
    expect(await screen.findByText("Checksum non disponibile")).toBeInTheDocument();
  });

  test("handles empty catalogs and initial load errors", async () => {
    mocks.listGisCatalogLayers.mockResolvedValueOnce({ items: [], total: 0 });
    mocks.getGisQgisGovernance.mockResolvedValueOnce(null);
    const empty = render(<GisAdministrationWorkspace token="token" />);
    expect(await screen.findByText("Nessuna mappa amministrabile.")).toBeInTheDocument();
    expect(screen.getByText("Governance QGIS non disponibile.")).toBeInTheDocument();
    empty.unmount();

    mocks.listGisCatalogLayers.mockRejectedValueOnce("offline");
    render(<GisAdministrationWorkspace token="token" />);
    expect(await screen.findByText("Amministrazione GIS non disponibile")).toBeInTheDocument();
  });

  test("switches the selected map and ignores a late initial response", async () => {
    const second = { ...layer, id: "layer-2", title: "Valvole", nas_export_root: null };
    mocks.listGisCatalogLayers.mockResolvedValueOnce({ items: [{ ...layer, nas_export_root: null }, second], total: 2 });
    const rendered = render(<GisAdministrationWorkspace token="token" />);
    const selector = await screen.findByLabelText("Scegli la mappa");
    fireEvent.change(selector, { target: { value: second.id } });
    expect(screen.getAllByLabelText("Titolo visibile")[1]).toHaveValue("Valvole");
    rendered.unmount();

    let resolveCatalog: (value: unknown) => void = () => undefined;
    mocks.listGisCatalogLayers.mockReturnValueOnce(new Promise((resolve) => { resolveCatalog = resolve; }));
    const late = render(<GisAdministrationWorkspace token="token" />);
    late.unmount();
    resolveCatalog({ items: [layer], total: 1 });
    await waitFor(() => expect(mocks.listGisCatalogLayers).toHaveBeenCalled());

    let rejectCatalog: (reason: unknown) => void = () => undefined;
    mocks.listGisCatalogLayers.mockReturnValueOnce(new Promise((_, reject) => { rejectCatalog = reject; }));
    const rejected = render(<GisAdministrationWorkspace token="token" />);
    rejected.unmount();
    rejectCatalog(new Error("late"));
    await waitFor(() => expect(mocks.listGisCatalogLayers).toHaveBeenCalled());
  });

  test("reports operation errors without losing the selected map", async () => {
    mocks.createGisCatalogLayer.mockRejectedValueOnce(new Error("creazione negata"));
    mocks.updateGisCatalogLayerMetadata.mockRejectedValueOnce("metadata offline");
    mocks.setGisCatalogLayerActive.mockRejectedValueOnce(new Error("lifecycle offline"));
    mocks.requestGisCatalogLayerExport.mockRejectedValueOnce("export offline");
    render(<GisAdministrationWorkspace token="token" />);
    await screen.findByText("Informazioni, disponibilità ed export");

    fireEvent.change(screen.getByLabelText("Nome tecnico"), { target: { value: "rete_valvole" } });
    fireEvent.change(screen.getAllByLabelText("Titolo visibile")[0], { target: { value: "Valvole" } });
    fireEvent.change(screen.getByLabelText("Tabella PostGIS"), { target: { value: "valvole" } });
    fireEvent.click(screen.getByRole("button", { name: "Registra nuova mappa" }));
    expect(await screen.findByText("creazione negata")).toBeInTheDocument();

    fireEvent.change(screen.getAllByLabelText("Titolo visibile")[1], { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva informazioni" }));
    expect(screen.getByText("Il titolo visibile è obbligatorio.")).toBeInTheDocument();
    fireEvent.change(screen.getAllByLabelText("Titolo visibile")[1], { target: { value: "Condotte" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva informazioni" }));
    expect(await screen.findByText("Aggiornamento informazioni non riuscito")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Rendi non attiva" }));
    fireEvent.click(screen.getByRole("button", { name: "Conferma disattivazione" }));
    expect(await screen.findAllByText("lifecycle offline")).toHaveLength(2);
    fireEvent.click(screen.getByRole("button", { name: "Annulla" }));

    fireEvent.click(screen.getByRole("button", { name: "Crea export shapefile" }));
    expect(await screen.findByText("Export shapefile non riuscito")).toBeInTheDocument();
  });
});
