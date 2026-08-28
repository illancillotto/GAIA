import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { GisToolsWorkspace } from "@/app/gis/strumenti/tools-workspace";
import type { GisCatalogLayer, GisShapefileImport } from "@/types/gis";

const mocks = vi.hoisted(() => ({
  createGisShapefileImport: vi.fn(),
  createGisShapefileImportChangeRequests: vi.fn(),
  listGisCatalogLayers: vi.fn(),
  previewGisShapefileImport: vi.fn(),
  publishGisShapefileImport: vi.fn(),
  rejectGisShapefileImport: vi.fn(),
}));

vi.mock("next/link", () => ({ default: ({ href, children, className }: { href: string; children: ReactNode; className?: string }) => <a href={href} className={className}>{children}</a> }));
vi.mock("@/lib/api/gis", () => ({
  createGisShapefileImport: (...args: unknown[]) => mocks.createGisShapefileImport(...args),
  createGisShapefileImportChangeRequests: (...args: unknown[]) => mocks.createGisShapefileImportChangeRequests(...args),
  listGisCatalogLayers: (...args: unknown[]) => mocks.listGisCatalogLayers(...args),
  previewGisShapefileImport: (...args: unknown[]) => mocks.previewGisShapefileImport(...args),
  publishGisShapefileImport: (...args: unknown[]) => mocks.publishGisShapefileImport(...args),
  rejectGisShapefileImport: (...args: unknown[]) => mocks.rejectGisShapefileImport(...args),
}));

vi.mock("@/app/gis/strumenti/activity-center", () => ({
  GisActivityCenter: ({ onResumeImport }: { onResumeImport?: (item: GisShapefileImport) => void }) => <>
    <button type="button" onClick={() => onResumeImport?.(importItem)}>Riprendi import test</button>
    <button type="button" onClick={() => onResumeImport?.({ ...importItem, status: "rejected" })}>Riprendi import rigettato</button>
  </>,
}));
vi.mock("@/app/gis/strumenti/qgis-tools", () => ({ GisQgisTools: () => <div>QGIS tools</div> }));

const editableLayer = {
  id: "layer-1",
  workspace: "rete",
  name: "rete_condotte",
  title: "Condotte ufficiali",
  source_type: "postgis",
  official_source: "postgis",
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

const importItem = {
  id: "import-1",
  status: "validated",
  original_filename: "rilievo.zip",
  workspace: "rete",
  domain_module: "network",
  target_layer_name: "rilievo_rete",
  target_layer_title: "Rilievo rete",
  official_source: "shapefile_upload",
  source_srid: 4326,
  encoding: "utf-8",
  staging_table: "import_1",
  feature_count: 2,
  fields: [],
  validation_report: {},
  metadata: {},
  checksum_sha256: "a".repeat(64),
  created_at: "2026-08-25T08:00:00Z",
  updated_at: "2026-08-25T08:00:00Z",
} satisfies GisShapefileImport;

const preview = {
  import_id: importItem.id,
  status: "validated" as const,
  staging_table: "import_1",
  feature_count: 2,
  returned_count: 1,
  limit: 10,
  offset: 0,
  has_more: false,
  fields: [],
  features: [{ feature_seq: 1, attributes: { nome: "Condotta A", diametro: 120 }, source_srid: 4326 }],
};

describe("GisToolsWorkspace", () => {
  beforeEach(() => {
    Object.values(mocks).forEach((mock) => mock.mockReset());
    mocks.listGisCatalogLayers.mockResolvedValue({ items: [editableLayer], total: 1 });
    mocks.previewGisShapefileImport.mockResolvedValue(preview);
  });

  test("renders a session state without calling the catalog", () => {
    render(<GisToolsWorkspace token={null} />);
    expect(screen.getByText("Verifica sessione GIS...")).toBeInTheDocument();
    expect(mocks.listGisCatalogLayers).not.toHaveBeenCalled();
  });

  test("uploads, previews and publishes a guided import", async () => {
    mocks.createGisShapefileImport.mockResolvedValue(importItem);
    mocks.publishGisShapefileImport.mockResolvedValue({ ...importItem, status: "published" });
    render(<GisToolsWorkspace token="token" />);
    await screen.findByText("QGIS tools");

    fireEvent.change(screen.getByLabelText("File shapefile ZIP"), { target: { files: [new File(["zip"], "Rilievo Rète 2026.zip", { type: "application/zip" })] } });
    expect(screen.getByLabelText("Nome tecnico")).toHaveValue("rilievo_rete_2026");
    expect(screen.getByLabelText("Titolo comprensibile")).toHaveValue("rilievo rete 2026");
    fireEvent.click(screen.getByRole("button", { name: "Controlla e carica" }));

    await waitFor(() => expect(mocks.createGisShapefileImport).toHaveBeenCalledWith("token", expect.objectContaining({
      file: expect.any(File),
      workspace: "rete",
      domainModule: "network",
      targetLayerName: "rilievo_rete_2026",
      targetLayerTitle: "rilievo rete 2026",
      officialSource: "shapefile_upload",
      sourceSrid: undefined,
      encoding: "",
    })));
    expect(await screen.findByText("Anteprima dei primi 1 elementi")).toBeInTheDocument();
    expect(screen.getByText(/nome: Condotta A/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Mostra anteprima" }));
    await waitFor(() => expect(mocks.previewGisShapefileImport).toHaveBeenCalledTimes(2));
    fireEvent.click(screen.getByRole("button", { name: "Pubblica nel catalogo" }));
    expect(mocks.publishGisShapefileImport).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Conferma pubblicazione" }));
    await waitFor(() => expect(mocks.publishGisShapefileImport).toHaveBeenCalledWith("token", "import-1"));
    expect(screen.getByText("Import pubblicato nel catalogo.")).toBeInTheDocument();
  });

  test("validates the import form and rejects a resumed import", async () => {
    mocks.rejectGisShapefileImport.mockResolvedValue({ ...importItem, status: "rejected" });
    render(<GisToolsWorkspace token="token" />);
    fireEvent.click(screen.getByRole("button", { name: "Controlla e carica" }));
    expect(screen.getByText("Scegli un file ZIP e indica area e titolo della mappa.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Riprendi import test" }));
    expect(await screen.findByText("Rilievo rete")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Rigetta import" }));
    fireEvent.click(screen.getByRole("button", { name: "Conferma rigetto" }));
    await waitFor(() => expect(mocks.rejectGisShapefileImport).toHaveBeenCalledWith("token", "import-1"));
    expect(screen.getByText("Import rigettato e area di prova rimossa.")).toBeInTheDocument();
  });

  test("validates technical fields and handles file clearing and non-previewable imports", async () => {
    render(<GisToolsWorkspace token="token" />);
    const fileInput = screen.getByLabelText("File shapefile ZIP");
    fireEvent.change(fileInput, { target: { files: [new File(["zip"], "Dati.zip")] } });
    fireEvent.change(screen.getByLabelText("Titolo comprensibile"), { target: { value: "Titolo scelto" } });
    fireEvent.change(fileInput, { target: { files: [new File(["zip"], "Altro.zip")] } });
    expect(screen.getByLabelText("Titolo comprensibile")).toHaveValue("Titolo scelto");
    fireEvent.change(screen.getByLabelText("Sistema coordinate"), { target: { value: "zero" } });
    fireEvent.change(screen.getByLabelText("Codifica testo"), { target: { value: "latin1" } });
    fireEvent.change(screen.getByLabelText("Area"), { target: { value: "catasto" } });
    fireEvent.change(screen.getByLabelText("Nome tecnico"), { target: { value: "altro_tecnico" } });
    fireEvent.click(screen.getByRole("button", { name: "Controlla e carica" }));
    expect(screen.getByText("Il sistema di coordinate deve essere un numero valido.")).toBeInTheDocument();

    fireEvent.change(fileInput, { target: { files: [] } });
    fireEvent.click(screen.getByRole("button", { name: "Riprendi import rigettato" }));
    expect(await screen.findByText("Rilievo rete")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Mostra anteprima" })).not.toBeInTheDocument();
  });

  test("reports upload error variants and preserves non-network domain metadata", async () => {
    mocks.createGisShapefileImport
      .mockRejectedValueOnce(new Error("upload offline"))
      .mockRejectedValueOnce("offline")
      .mockResolvedValueOnce(importItem);
    render(<GisToolsWorkspace token="token" />);
    const fileInput = screen.getByLabelText("File shapefile ZIP");
    fireEvent.change(fileInput, { target: { files: [new File(["zip"], "rilievo.zip")] } });
    fireEvent.change(screen.getByLabelText("Area"), { target: { value: "catasto" } });
    fireEvent.click(screen.getByRole("button", { name: "Controlla e carica" }));
    expect(await screen.findByText("upload offline")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Controlla e carica" }));
    expect(await screen.findByText("Import non riuscito")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Controlla e carica" }));
    await waitFor(() => expect(mocks.createGisShapefileImport).toHaveBeenLastCalledWith("token", expect.objectContaining({ domainModule: "catasto" })));
  });

  test("uploads a valid SRID, encoding and trimmed title without rewriting domain mapping", async () => {
    mocks.createGisShapefileImport.mockResolvedValue(importItem);
    render(<GisToolsWorkspace token="token" />);
    fireEvent.change(screen.getByLabelText("File shapefile ZIP"), { target: { files: [new File(["zip"], "rilievo.zip")] } });
    fireEvent.change(screen.getByLabelText("Titolo comprensibile"), { target: { value: "  Rilievo ufficiale  " } });
    fireEvent.change(screen.getByLabelText("Sistema coordinate"), { target: { value: "3003" } });
    fireEvent.change(screen.getByLabelText("Codifica testo"), { target: { value: "latin1" } });
    fireEvent.change(screen.getByLabelText("Area"), { target: { value: "riordino" } });
    fireEvent.click(screen.getByRole("button", { name: "Controlla e carica" }));
    await waitFor(() => expect(mocks.createGisShapefileImport).toHaveBeenCalledWith("token", expect.objectContaining({
      workspace: "riordino",
      domainModule: "riordino",
      targetLayerTitle: "Rilievo ufficiale",
      sourceSrid: 3003,
      encoding: "latin1",
      officialSource: "shapefile_upload",
    })));
  });

  test("creates all guided change proposals without exposing batches", async () => {
    mocks.createGisShapefileImportChangeRequests
      .mockResolvedValueOnce({ created_count: 2, existing_count: 0, returned_count: 2, has_more: true })
      .mockResolvedValueOnce({ created_count: 1, existing_count: 1, returned_count: 1, has_more: false });
    render(<GisToolsWorkspace token="token" />);
    fireEvent.click(screen.getByRole("button", { name: "Riprendi import test" }));
    await screen.findByText("Crea proposte di modifica");
    fireEvent.click(screen.getByRole("button", { name: "Crea proposte di modifica" }));
    expect(screen.getByText("Scegli la mappa da correggere e descrivi il motivo della proposta.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Mappa da correggere"), { target: { value: "layer-1" } });
    fireEvent.change(screen.getByLabelText("Motivo della proposta"), { target: { value: "Rilievo aggiornato" } });
    fireEvent.click(screen.getByRole("button", { name: "Crea proposte di modifica" }));

    await waitFor(() => expect(mocks.createGisShapefileImportChangeRequests).toHaveBeenCalledTimes(2));
    expect(mocks.createGisShapefileImportChangeRequests).toHaveBeenNthCalledWith(2, "token", "import-1", {
      targetLayerId: "layer-1",
      justification: "Rilievo aggiornato",
      limit: 100,
      offset: 2,
    });
    expect(screen.getByText("3 proposte create, 1 già presenti.")).toBeInTheDocument();
    expect(screen.queryByLabelText(/offset|batch/i)).not.toBeInTheDocument();
  });

  test("stops guided proposals when a page reports more results but returns none", async () => {
    mocks.createGisShapefileImportChangeRequests.mockResolvedValueOnce({
      created_count: 0,
      existing_count: 2,
      returned_count: 0,
      has_more: true,
    });
    render(<GisToolsWorkspace token="token" />);
    fireEvent.click(screen.getByRole("button", { name: "Riprendi import test" }));
    fireEvent.change(await screen.findByLabelText("Motivo della proposta"), { target: { value: "Motivo" } });
    fireEvent.click(screen.getByRole("button", { name: "Crea proposte di modifica" }));
    await waitFor(() => expect(mocks.createGisShapefileImportChangeRequests).toHaveBeenCalledTimes(1));
    expect(screen.getByText("0 proposte create, 2 già presenti.")).toBeInTheDocument();
  });

  test("creates proposals without duplicate notices and renders empty preview attributes", async () => {
    mocks.previewGisShapefileImport.mockResolvedValueOnce({
      ...preview,
      features: [{ feature_seq: 2, attributes: {}, source_srid: 4326 }],
    });
    mocks.createGisShapefileImportChangeRequests.mockResolvedValueOnce({ created_count: 1, existing_count: 0, returned_count: 1, has_more: false });
    render(<GisToolsWorkspace token="token" />);
    fireEvent.click(screen.getByRole("button", { name: "Riprendi import test" }));
    expect(await screen.findByText("Nessun attributo")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Motivo della proposta"), { target: { value: "Motivo" } });
    fireEvent.click(screen.getByRole("button", { name: "Crea proposte di modifica" }));
    expect(await screen.findByText("1 proposte create.")).toBeInTheDocument();
  });

  test("reports catalog, validation, preview, action and proposal errors", async () => {
    mocks.listGisCatalogLayers.mockRejectedValueOnce("catalog offline");
    const failedCatalog = render(<GisToolsWorkspace token="token" />);
    expect(await screen.findByText("Catalogo GIS non disponibile")).toBeInTheDocument();
    failedCatalog.unmount();

    mocks.listGisCatalogLayers.mockResolvedValueOnce({ items: [editableLayer], total: 1 });
    mocks.previewGisShapefileImport.mockRejectedValueOnce(new Error("preview offline"));
    const failedPreview = render(<GisToolsWorkspace token="token" />);
    fireEvent.click(screen.getByRole("button", { name: "Riprendi import test" }));
    expect(await screen.findByText("preview offline")).toBeInTheDocument();
    failedPreview.unmount();

    mocks.listGisCatalogLayers.mockResolvedValueOnce({ items: [editableLayer], total: 1 });
    mocks.previewGisShapefileImport.mockResolvedValueOnce(preview);
    mocks.publishGisShapefileImport.mockRejectedValueOnce("publish offline");
    mocks.createGisShapefileImportChangeRequests.mockRejectedValueOnce(new Error("proposal denied"));
    render(<GisToolsWorkspace token="token" />);
    fireEvent.click(screen.getByRole("button", { name: "Riprendi import test" }));
    await screen.findByText("Pubblica nel catalogo");
    fireEvent.click(screen.getByRole("button", { name: "Pubblica nel catalogo" }));
    fireEvent.click(screen.getByRole("button", { name: "Conferma pubblicazione" }));
    expect(await screen.findAllByText("Operazione import non riuscita")).toHaveLength(2);
    fireEvent.click(screen.getByRole("button", { name: "Annulla" }));
    fireEvent.change(screen.getByLabelText("Motivo della proposta"), { target: { value: "Motivo" } });
    fireEvent.click(screen.getByRole("button", { name: "Crea proposte di modifica" }));
    expect(await screen.findByText("proposal denied")).toBeInTheDocument();
  });

  test("ignores a late catalog response after unmount", async () => {
    let resolveCatalog: (value: unknown) => void = () => undefined;
    mocks.listGisCatalogLayers.mockReturnValueOnce(new Promise((resolve) => { resolveCatalog = resolve; }));
    const { unmount } = render(<GisToolsWorkspace token="token" />);
    unmount();
    resolveCatalog({ items: [editableLayer], total: 1 });
    await waitFor(() => expect(mocks.listGisCatalogLayers).toHaveBeenCalledWith("token"));

    let rejectCatalog: (reason: unknown) => void = () => undefined;
    mocks.listGisCatalogLayers.mockReturnValueOnce(new Promise((_, reject) => { rejectCatalog = reject; }));
    const rejected = render(<GisToolsWorkspace token="token" />);
    rejected.unmount();
    rejectCatalog(new Error("late"));
    await waitFor(() => expect(mocks.listGisCatalogLayers).toHaveBeenCalled());
  });

  test("handles catalogs without editable maps and the numeric lower bound", async () => {
    mocks.listGisCatalogLayers.mockResolvedValueOnce({ items: [{ ...editableLayer, can_edit: false }], total: 1 });
    render(<GisToolsWorkspace token="token" />);
    await screen.findByText("QGIS tools");
    fireEvent.change(screen.getByLabelText("File shapefile ZIP"), { target: { files: [new File(["zip"], "dato.zip")] } });
    fireEvent.change(screen.getByLabelText("Sistema coordinate"), { target: { value: "0" } });
    fireEvent.click(screen.getByRole("button", { name: "Controlla e carica" }));
    expect(screen.getByText("Il sistema di coordinate deve essere un numero valido.")).toBeInTheDocument();
  });
});
