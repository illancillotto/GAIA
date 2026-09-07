import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ComponentProps, ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });

const mocks = vi.hoisted(() => ({
  whiteProps: {} as ComponentProps<typeof import("@/components/catasto/gis/WhiteCompanyReportsPanel").default>,
  districtProps: {} as ComponentProps<typeof import("@/components/catasto/gis/DistrettiPanel").default>,
  archiveProps: {} as ComponentProps<typeof import("@/components/catasto/gis/ArchiveList").default>,
  mapProps: {} as Record<string, unknown>,
  mapLoader: null as null | (() => Promise<unknown>),
  mapLoading: null as null | (() => ReactNode),
  getStoredAccessToken: vi.fn(),
  runSelection: vi.fn(),
  clearSelection: vi.fn(),
  selectionResult: {
    particelle: [{ id: "parcel-1", foglio: "1", particella: "10" }],
    n_particelle: 1,
    truncated: false,
  } as unknown,
  selectionError: null as string | null,
  capacitasGetRptCertificatoLink: vi.fn(),
  catastoGetDistrettoGeojson: vi.fn(),
  catastoGisGetAdeAlignmentReport: vi.fn(),
  catastoGisGetDui2026DomandaDetail: vi.fn(),
  catastoGisGetDui2026LatestLayer: vi.fn(),
  catastoGisGetWhiteCompanyReportLayer: vi.fn(),
  catastoGisGetLatestAdeWfsRunStatus: vi.fn(),
  catastoGisGetAdeWfsRunStatus: vi.fn(),
  catastoGisCreateSavedSelection: vi.fn(),
  catastoGisDeleteSavedSelection: vi.fn(),
  catastoGisExport: vi.fn(),
  catastoGisGetSavedSelection: vi.fn(),
  catastoGisListSavedSelections: vi.fn(),
  catastoGisResolveRefs: vi.fn(),
  catastoGisUpdateSavedSelection: vi.fn(),
  catastoRefreshDeliveryPointsGisCache: vi.fn(),
  catastoListDistretti: vi.fn(),
  searchAnagraficaSubjects: vi.fn(),
  storeGisTileRevision: vi.fn(),
  xlsxRead: vi.fn(),
  sheetToJson: vi.fn(),
}));

const richParticella = {
  id: "parcel-1",
  cfm: "A001-1-10",
  nome_comune: "Marrubiu",
  cod_comune_capacitas: "001",
  codice_catastale: "A001",
  foglio: "1",
  particella: "10",
  subalterno: "2",
  num_distretto: "1",
  nome_distretto: "Nord",
  superficie_mq: 1234,
  superficie_grafica_mq: 1200,
  source_type: "catasto",
  is_current: true,
  suppressed: false,
  missing_reason: null,
  missing_fields: [],
  ha_ruolo: true,
  ha_ruolo_inferito: false,
  n_anomalie_aperte: 1,
  anomalie_aperte: [{ id: "anom-1", tipo: "chiave", severita: "warning", descrizione: "Verifica chiave" }],
  titolare: {
    cco: "123",
    subject_id: "subject-1",
    subject_display_name: "Mario Rossi",
    denominazione: "Rossi Mario",
    codice_fiscale: "RSSMRA80A01H501U",
    partita_iva: null,
  },
  ruolo_summary: {
    source_mode: "exact",
    anno_tributario_richiesto: 2025,
    anno_tributario_latest: 2025,
    n_righe: 1,
    n_subalterni: 1,
    source_note: "Fonte ruolo",
    sup_irrigata_ha_totale: 1.2,
    importo_totale_euro: 20,
    importo_manut_euro_totale: 5,
    importo_irrig_euro_totale: 10,
    importo_ist_euro_totale: 5,
    items: [{ anno_tributario: 2025, subalterno: "2", codice_partita: "P1", coltura: "Mais", sup_irrigata_ha: 1.2, importo_totale_euro: 20 }],
  },
  swapped_capacitas: {
    source_codice_catastale: "B002",
    source_comune_nome: "Terralba",
    source_foglio: "2",
    source_particella: "20",
    source_subalterno: "3",
  },
};

const incompleteParticella = {
  ...richParticella,
  id: "parcel-incomplete",
  cfm: null,
  codice_catastale: null,
  foglio: null,
  particella: null,
  subalterno: null,
  superficie_mq: null,
  suppressed: true,
  is_current: false,
  missing_reason: "Chiave incompleta",
  missing_fields: ["foglio", "particella"],
  ha_ruolo: false,
  ha_ruolo_inferito: true,
  n_anomalie_aperte: 0,
  anomalie_aperte: [],
  titolare: {
    cco: null,
    subject_id: null,
    subject_display_name: null,
    denominazione: "Impresa Alfa",
    codice_fiscale: " ALF 001 ",
    partita_iva: null,
  },
  ruolo_summary: {
    source_mode: "subject_comune_fallback",
    anno_tributario_richiesto: 2025,
    anno_tributario_latest: 2024,
    n_righe: 2,
    n_subalterni: 0,
    source_note: null,
    importo_manut_euro_totale: null,
    importo_irrig_euro_totale: null,
    importo_ist_euro_totale: null,
    items: [],
  },
  swapped_capacitas: null,
};

vi.mock("next/dynamic", () => ({
  default: (loader: () => Promise<unknown>, options: { loading: () => ReactNode }) => {
    mocks.mapLoader = loader;
    mocks.mapLoading = options.loading;
    return function MockMap(props: Record<string, unknown>) {
    mocks.mapProps = props;
    const call = (name: string, value: unknown) => () => void (props[name] as (arg: unknown) => unknown)(value);
    return (
      <div data-testid="map">
        <button onClick={call("onGeometryDrawn", { type: "Polygon", coordinates: [] })}>Map draw</button>
        <button onClick={() => void (props.onSelectionCleared as () => unknown)()}>Map clear</button>
        <button onClick={call("onParticellaClick", richParticella)}>Map parcel rich</button>
        <button onClick={call("onParticellaClick", incompleteParticella)}>Map parcel incomplete</button>
        <button onClick={call("onParticellaClick", null)}>Map parcel clear</button>
        <button onClick={call("onDeliveryPointClick", { id: "pdc-1", punto_consegna_code: "PDC-1", distretto_code: "1", has_meter: true, linked_meter_readings_count: 0, source_dataset: "PdC", source_file: "pdc.shp", source_updated_at: "2026-01-01", source_x: 9, source_y: 39 })}>Map delivery</button>
        <button onClick={call("onOverlayFeatureClick", { layer_key: "whitecompany-reports", properties: { id: "white-1", report_number: "W-1", title: "Perdita", status: "open", tipologia: "guasto", operatore: "Mario", area_code: "A", description: "Descrizione", assigned_responsibles: "Tecnico", created_at: "2026-08-01" } })}>Map white</button>
        <button onClick={call("onOverlayFeatureClick", { layer_key: "dui-2026-live", properties: { domanda_irrigua: "DUI-1", __overlayColor: "#123456", coltura: "Mais", sup_grafica_mq: 1000, contatore: "Si", telerilev: "No", codice_fiscale: "CF", tipo_domanda: "A", data_domanda: "2026-01-01" } })}>Map dui</button>
        <button onClick={call("onOverlayFeatureClick", { layer_key: "other", properties: {} })}>Map other</button>
      </div>
    );
    };
  },
}));

vi.mock("@/components/catasto/gis/TerritorioMapExperience", () => ({ default: () => <div>Territory map adapter</div> }));

vi.mock("@/components/catasto/catasto-page", () => ({
  CatastoPage: ({ children, title }: { children: ReactNode; title: string }) => <main><h1>{title}</h1>{children}</main>,
}));
vi.mock("@/components/catasto/gis/DrawingTools", () => ({
  default: ({ onDrawPolygon, onClearDrawing }: { onDrawPolygon: () => void; onClearDrawing: () => void }) => <div><button onClick={onDrawPolygon}>Draw polygon</button><button onClick={onClearDrawing}>Clear drawing</button></div>,
}));
vi.mock("@/components/catasto/gis/AnalysisPanel", () => ({
  default: ({ onExport }: { onExport: (format: "geojson" | "csv" | "xlsx") => void }) => <div><button onClick={() => onExport("geojson")}>Export geojson</button><button onClick={() => onExport("csv")}>Export csv</button><button onClick={() => onExport("xlsx")}>Export xlsx</button></div>,
}));
vi.mock("@/components/catasto/gis/SelectionPanel", () => ({ default: () => <div>Selection panel</div> }));
// Keep the real panels while exposing their current event contract for fail-closed tests.
vi.mock("@/components/catasto/gis/WhiteCompanyReportsPanel", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/components/catasto/gis/WhiteCompanyReportsPanel")>();
  return { ...original, default: (props: typeof mocks.whiteProps) => { mocks.whiteProps = props; return <original.default {...props} />; } };
});
vi.mock("@/components/catasto/gis/DistrettiPanel", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/components/catasto/gis/DistrettiPanel")>();
  return { ...original, default: (props: typeof mocks.districtProps) => { mocks.districtProps = props; return <original.default {...props} />; } };
});
vi.mock("@/components/catasto/gis/ArchiveList", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/components/catasto/gis/ArchiveList")>();
  return { ...original, default: (props: typeof mocks.archiveProps) => { mocks.archiveProps = props; return <original.default {...props} />; } };
});
vi.mock("@/components/catasto/gis/Dui2026LivePanel", () => ({
  Dui2026LivePanel: ({ onToggleVisible }: { onToggleVisible: () => void }) => <button onClick={onToggleVisible}>Toggle DUI</button>,
}));
vi.mock("@/components/catasto/anagrafica/ParticellaDetailDialog", () => ({ ParticellaDetailDialog: ({ open, onClose }: { open: boolean; onClose: () => void }) => open ? <div role="dialog">Parcel detail<button onClick={onClose}>Close parcel detail</button></div> : null }));
vi.mock("@/components/catasto/catasto-anomalia-explainer", () => ({ CatastoAnomaliaExplainer: ({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) => open ? <div>Explain anomaly<button onClick={() => onOpenChange(true)}>Keep anomaly open</button><button onClick={() => onOpenChange(false)}>Close anomaly</button></div> : null }));
vi.mock("@/components/utenze/utenze-subject-quick-view-dialog", () => ({ UtenzeSubjectQuickViewDialog: ({ subjectId, onClose }: { subjectId: string; onClose: () => void }) => <div role="dialog">Subject {subjectId}<button onClick={onClose}>Close subject</button></div> }));

vi.mock("@/hooks/useGisSelection", () => ({ useGisSelection: () => ({ result: mocks.selectionResult, isLoading: false, error: mocks.selectionError, runSelection: mocks.runSelection, clearSelection: mocks.clearSelection }) }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.getStoredAccessToken }));
vi.mock("@/lib/api", () => ({ searchAnagraficaSubjects: mocks.searchAnagraficaSubjects }));
vi.mock("@/lib/catasto-anomalie", () => ({ describeCatastoAnomalia: () => "Descrizione anomalia" }));
vi.mock("@/lib/catasto-gis-cache", () => ({ storeGisTileRevision: mocks.storeGisTileRevision }));
vi.mock("@/lib/api/catasto", () => ({
  capacitasGetRptCertificatoLink: mocks.capacitasGetRptCertificatoLink,
  catastoGetDistrettoGeojson: mocks.catastoGetDistrettoGeojson,
  catastoGisGetAdeAlignmentReport: mocks.catastoGisGetAdeAlignmentReport,
  catastoGisGetDui2026DomandaDetail: mocks.catastoGisGetDui2026DomandaDetail,
  catastoGisGetDui2026LatestLayer: mocks.catastoGisGetDui2026LatestLayer,
  catastoGisGetWhiteCompanyReportLayer: mocks.catastoGisGetWhiteCompanyReportLayer,
  catastoGisGetLatestAdeWfsRunStatus: mocks.catastoGisGetLatestAdeWfsRunStatus,
  catastoGisGetAdeWfsRunStatus: mocks.catastoGisGetAdeWfsRunStatus,
  catastoGisCreateSavedSelection: mocks.catastoGisCreateSavedSelection,
  catastoGisDeleteSavedSelection: mocks.catastoGisDeleteSavedSelection,
  catastoGisExport: mocks.catastoGisExport,
  catastoGisGetSavedSelection: mocks.catastoGisGetSavedSelection,
  catastoGisListSavedSelections: mocks.catastoGisListSavedSelections,
  catastoGisResolveRefs: mocks.catastoGisResolveRefs,
  catastoGisUpdateSavedSelection: mocks.catastoGisUpdateSavedSelection,
  catastoRefreshDeliveryPointsGisCache: mocks.catastoRefreshDeliveryPointsGisCache,
  catastoListDistretti: mocks.catastoListDistretti,
}));
vi.mock("xlsx", () => ({ read: mocks.xlsxRead, utils: { sheet_to_json: mocks.sheetToJson } }));

import CatastoGisPage from "@/app/catasto/gis/page";

const featureCollection = { type: "FeatureCollection", features: [{ type: "Feature", geometry: { type: "Point", coordinates: [9, 39] }, properties: {} }] };
const savedSummary = { id: "saved-1", name: "Archivio", color: "#10B981", n_particelle: 1, n_with_geometry: 1 };
const adeRun = { run_id: "run-12345678", status: "completed", tiles: 1, tiles_completed: 1, features: 1, with_geometry: 1, progress_phase: "completed", progress_percent: 100, progress_message: null, error: null, started_at: "2026-01-01", completed_at: "2026-01-01" };
const adeReport = { run_id: adeRun.run_id, completed_at: "2026-01-01", geometry_threshold_m: 1, counters: { allineate: 1, nuove_in_ade: 0, geometrie_variate: 0, mancanti_in_ade: 0 }, samples: [], geojson: featureCollection };
const whiteLayer = { stats: { total: 1, mapped: 1, unmapped: 0, truncated: false }, tipologie: ["guasto"], operatori: ["Mario"], geojson: featureCollection };

describe("CatastoGisPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mocks.selectionResult = { particelle: [{ id: "parcel-1", foglio: "1", particella: "10" }], n_particelle: 1, truncated: false };
    mocks.selectionError = null;
    window.history.replaceState({}, "", "/catasto/gis");
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.catastoGisListSavedSelections.mockResolvedValue([savedSummary]);
    mocks.catastoListDistretti.mockResolvedValue([{ id: "d2", num_distretto: "2", nome_distretto: "Sud" }, { id: "d1", num_distretto: "1", nome_distretto: "Nord" }]);
    mocks.catastoGisGetLatestAdeWfsRunStatus.mockResolvedValue(adeRun);
    mocks.catastoGisGetAdeAlignmentReport.mockResolvedValue(adeReport);
    mocks.catastoGisGetDui2026LatestLayer.mockResolvedValue({ geojson: featureCollection, stats: {} });
    mocks.catastoGisGetWhiteCompanyReportLayer.mockResolvedValue(whiteLayer);
    mocks.catastoGisGetDui2026DomandaDetail.mockResolvedValue({ domanda_irrigua: "DUI-1", intestatario: "Azienda", coltura: "Mais", sup_grafica_mq_totale: 1000, contatore: "Si", telerilev: "No", codice_fiscale: "CF", tipo_domanda: "A", data_domanda: "2026-01-01", telefono: "123", n_poligoni: 1, in_ruolo_2025: true, ruolo_summary: { n_righe: 1, n_subalterni: 1, source_note: "Nota", sup_irrigata_ha_totale: 1, importo_totale_euro: 20, importo_manut_euro_totale: 5, importo_irrig_euro_totale: 10, importo_ist_euro_totale: 5, items: [{ anno_tributario: 2025, foglio: "1", particella: "10", subalterno: "2", sup_irrigata_ha: 1, importo_totale_euro: 20 }] } });
    mocks.catastoGetDistrettoGeojson.mockResolvedValue(featureCollection.features[0]);
    mocks.catastoRefreshDeliveryPointsGisCache.mockResolvedValue({ tile_revision: "rev-1", martin_restarted: true, restart_error: null });
    mocks.catastoGisExport.mockResolvedValue(new Blob(["data"]));
    mocks.capacitasGetRptCertificatoLink.mockResolvedValue({ url: "https://capacitas.test" });
    mocks.searchAnagraficaSubjects.mockResolvedValue({ items: [{ id: "subject-resolved", codice_fiscale: "ALF001", partita_iva: null, display_name: "Impresa Alfa" }] });
    mocks.xlsxRead.mockReturnValue({ SheetNames: ["Foglio1"], Sheets: { Foglio1: {} } });
    mocks.sheetToJson.mockReturnValue([{ Comune: "Marrubiu", Foglio: "1", Particella: "10", Subalterno: "2" }]);
    mocks.catastoGisResolveRefs.mockResolvedValue({ processed: 1, found: 1, not_found: 0, multiple: 0, invalid: 0, results: [{ esito: "FOUND", particella_id: "parcel-1", row_index: 2, comune_input: "Marrubiu", sezione_input: null, foglio_input: "1", particella_input: "10", sub_input: "2" }], geojson: featureCollection });
    mocks.catastoGisGetSavedSelection.mockResolvedValue({ ...savedSummary, source_filename: "file.xlsx", geojson: featureCollection, import_summary: null });
    mocks.catastoGisCreateSavedSelection.mockResolvedValue({ ...savedSummary, geojson: featureCollection });
    mocks.catastoGisUpdateSavedSelection.mockResolvedValue(savedSummary);
    mocks.catastoGisDeleteSavedSelection.mockResolvedValue(undefined);
    vi.spyOn(window, "open").mockImplementation(() => null);
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:test");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  });

  test("exercises the primary map, popup and tool workflows", async () => {
    render(<CatastoGisPage />);

    expect(await screen.findByRole("heading", { name: "GIS" })).toBeInTheDocument();
    await waitFor(() => expect(mocks.catastoGisGetWhiteCompanyReportLayer).toHaveBeenCalled());
    expect(screen.getByText("Selection panel")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Map draw"));
    await waitFor(() => expect(mocks.runSelection).toHaveBeenCalled());
    fireEvent.click(screen.getAllByText("Clear drawing")[0]);
    expect(mocks.clearSelection).toHaveBeenCalled();

    fireEvent.click(screen.getByText("Map parcel rich"));
    expect(await screen.findByText("A001-1-10")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Apri dettaglio particella" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("Parcel detail");
    fireEvent.click(screen.getByText("Close parcel detail"));
    fireEvent.click(screen.getByRole("button", { name: "RSSMRA80A01H501U" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("Subject subject-1");
    fireEvent.click(screen.getByText("Close subject"));
    fireEvent.click(screen.getByRole("button", { name: /Apri intestatario su Capacitas/i }));
    await waitFor(() => expect(window.open).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: /Approfondisci come e stato determinato/i }));
    expect(screen.getByText("Approfondimento ruolo")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi approfondimento ruolo" }));
    fireEvent.click(screen.getByRole("button", { name: "Approfondisci" }));
    expect(screen.getByText("Explain anomaly")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Keep anomaly open"));
    expect(screen.getByText("Explain anomaly")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Close anomaly"));

    fireEvent.click(screen.getByText("Map parcel incomplete"));
    expect(await screen.findByText("Particella GIS incompleta")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "ALF 001" }));
    expect(await screen.findByRole("dialog")).toHaveTextContent("subject-resolved");
    fireEvent.click(screen.getByText("Close subject"));
    fireEvent.click(screen.getByText("Map parcel clear"));

    fireEvent.click(screen.getByText("Map delivery"));
    expect(await screen.findByText("Punto di attacco PDC-1")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Map white"));
    expect(await screen.findByText("Perdita")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Map dui"));
    expect(await screen.findByText("Azienda")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Map other"));

    fireEvent.click(screen.getByRole("button", { name: /Distretto 1/i }));
    await waitFor(() => expect(mocks.catastoGetDistrettoGeojson).toHaveBeenCalledWith("token", "d1"));
    const allButtons = screen.getAllByRole("button", { name: "Tutti" });
    fireEvent.click(allButtons[allButtons.length - 1]);
    fireEvent.change(screen.getByLabelText("Cerca distretto"), { target: { value: "sud" } });
    expect(screen.getByRole("button", { name: /Distretto 2/i })).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Aggiorna cache" })[0]);
    await waitFor(() => expect(mocks.storeGisTileRevision).toHaveBeenCalledWith("rev-1"));
    fireEvent.click(screen.getByText("Export geojson"));
    await waitFor(() => expect(mocks.catastoGisExport).toHaveBeenCalledWith("token", ["parcel-1"], "geojson"));

    fireEvent.click(screen.getByRole("button", { name: /Vista/ }));
    expect(screen.getByText("Vista estesa GIS")).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByText("Vista estesa GIS")).not.toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Apri Console GIS" }));
    expect(screen.getByRole("button", { name: "Chiudi strumenti GIS" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi strumenti GIS" }));
    expect(screen.getByRole("button", { name: "Apri Console GIS" })).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(screen.getByRole("button", { name: "Apri Console GIS" }));
    fireEvent.click(screen.getByText("Draw polygon"));
    expect(screen.getByRole("button", { name: "Apri Console GIS" })).toHaveAttribute("aria-expanded", "false");
  });

  test("imports, edits, persists and removes workspace layers", async () => {
    render(<CatastoGisPage />);
    await screen.findByRole("heading", { name: "GIS" });

    const file = { name: "selezione.xlsx", arrayBuffer: vi.fn().mockResolvedValue(new ArrayBuffer(8)) } as unknown as File;
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    expect((await screen.findAllByText("selezione.xlsx")).length).toBeGreaterThan(0);
    expect(screen.getByText("Bozza")).toBeInTheDocument();
    const nameInput = screen.getByPlaceholderText("Nome layer");
    fireEvent.change(nameInput, { target: { value: "Layer importato" } });
    const colorInput = document.querySelector('input[title="Colore layer"]') as HTMLInputElement;
    fireEvent.change(colorInput, { target: { value: "#123456" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Riempimento" })[0]);
    const sliders = screen.getAllByRole("slider");
    fireEvent.change(sliders[2], { target: { value: "75" } });
    fireEvent.click(screen.getByRole("button", { name: "Centra" }));
    fireEvent.click(screen.getByRole("button", { name: "Salva permanentemente" }));
    await waitFor(() => expect(mocks.catastoGisCreateSavedSelection).toHaveBeenCalled());

    expect(await screen.findByText("Salvato")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Nome layer"), { target: { value: "Layer aggiornato" } });
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna metadati salvati" }));
    await waitFor(() => expect(mocks.catastoGisUpdateSavedSelection).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: "Rimuovi dalla mappa" }));

    fireEvent.click(screen.getByRole("button", { name: "Aggiungi in mappa" }));
    await waitFor(() => expect(mocks.catastoGisGetSavedSelection).toHaveBeenCalledWith("token", "saved-1"));
    fireEvent.click(screen.getByRole("button", { name: "Porta in primo piano" }));
    fireEvent.click(screen.getAllByRole("button", { name: "Riempimento" }).at(-1)!);
    const archiveSlider = screen.getAllByRole("slider").at(-1)!;
    fireEvent.change(archiveSlider, { target: { value: "65" } });
    fireEvent.blur(document.querySelector('input[title="Modifica colore"]') as HTMLInputElement, { target: { value: "#ABCDEF" } });
    fireEvent.click(screen.getByRole("button", { name: "Rimuovi" }));
    fireEvent.click(screen.getByRole("button", { name: "Elimina" }));
    await waitFor(() => expect(mocks.catastoGisDeleteSavedSelection).toHaveBeenCalledWith("token", "saved-1"));
  });

  test("governs a missing session and empty selection without calling protected APIs", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);
    mocks.selectionResult = { particelle: [], n_particelle: 0, truncated: false };
    render(<CatastoGisPage />);
    await screen.findByRole("heading", { name: "GIS" });

    fireEvent.click(screen.getAllByRole("button", { name: "Aggiorna cache" })[0]);
    expect(await screen.findByText("Sessione non disponibile.")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Export csv"));
    expect(mocks.catastoGisExport).not.toHaveBeenCalled();

    const file = { name: "vuoto.xlsx", arrayBuffer: vi.fn() } as unknown as File;
    fireEvent.change(document.querySelector('input[type="file"]') as HTMLInputElement, { target: { files: [file] } });
    expect(await screen.findByText("Sessione non disponibile. Accedi di nuovo.")).toBeInTheDocument();
    expect(file.arrayBuffer).not.toHaveBeenCalled();

    fireEvent.click(screen.getByText("Map dui"));
    expect(mocks.catastoGisGetDui2026DomandaDetail).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText("Map parcel incomplete"));
    fireEvent.click(screen.getByRole("button", { name: "ALF 001" }));
    expect(await screen.findByText("Nessun soggetto GAIA collegato a questo identificativo fiscale.")).toBeInTheDocument();
  });

  test("surfaces degraded bootstrap and action failures", async () => {
    mocks.catastoGisListSavedSelections.mockRejectedValueOnce("archive down");
    mocks.catastoGisGetLatestAdeWfsRunStatus.mockRejectedValueOnce("ade down");
    mocks.catastoGisGetDui2026LatestLayer.mockRejectedValueOnce("dui down");
    mocks.catastoGisGetWhiteCompanyReportLayer.mockRejectedValueOnce("white down");
    render(<CatastoGisPage />);
    expect(await screen.findByText("Caricamento layer WhiteCompany fallito")).toBeInTheDocument();

    mocks.catastoGetDistrettoGeojson.mockRejectedValueOnce("focus down");
    fireEvent.click(screen.getByRole("button", { name: /Distretto 1/i }));
    expect(await screen.findByText("Impossibile centrare il distretto selezionato")).toBeInTheDocument();

    mocks.catastoRefreshDeliveryPointsGisCache.mockRejectedValueOnce("cache down");
    fireEvent.click(screen.getAllByRole("button", { name: "Aggiorna cache" })[0]);
    expect(await screen.findByText("Errore aggiornamento cache GIS.")).toBeInTheDocument();

    mocks.catastoGisExport.mockRejectedValueOnce("export down");
    fireEvent.click(screen.getByText("Export xlsx"));
    expect(await screen.findByText("Export fallito")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Export geojson"));
    await waitFor(() => expect(mocks.catastoGisExport).toHaveBeenCalledTimes(2));

    mocks.capacitasGetRptCertificatoLink.mockRejectedValueOnce("capacitas down");
    fireEvent.click(screen.getByText("Map parcel rich"));
    fireEvent.click(screen.getByRole("button", { name: /Apri intestatario su Capacitas/i }));
    expect(await screen.findByText("Errore generazione link Capacitas")).toBeInTheDocument();

    mocks.searchAnagraficaSubjects.mockRejectedValueOnce("subjects down");
    fireEvent.click(screen.getByText("Map parcel incomplete"));
    fireEvent.click(screen.getByRole("button", { name: "ALF 001" }));
    expect(await screen.findByText("Errore apertura dettaglio soggetto")).toBeInTheDocument();

    mocks.catastoGisGetDui2026DomandaDetail.mockRejectedValueOnce("detail down");
    fireEvent.click(screen.getByText("Map dui"));
    expect(await screen.findByText("Caricamento dettaglio DUI 2026 fallito")).toBeInTheDocument();
  });

  test("keeps layer controls synchronized across normal and expanded consoles", async () => {
    render(<CatastoGisPage />);
    await waitFor(() => expect(mocks.catastoListDistretti).toHaveBeenCalled());
    for (const name of ["Distretti", "Aree colorate", "Riempimento particelle", "Punti consegna", "Evidenzia sel."]) {
      fireEvent.click(screen.getByRole("button", { name, exact: true }));
    }
    fireEvent.change(screen.getByRole("slider", { name: "Opacità aree distretto" }), { target: { value: "0.2" } });
    fireEvent.change(screen.getByRole("slider", { name: "Opacità particelle" }), { target: { value: "0.8" } });
    expect(mocks.mapProps.mapLayers).toMatchObject({ showDistretti: false, showDistrettiFill: true, showParticelleFill: true, showDeliveryPoints: false, highlightSelected: false, distrettiOpacity: 0.2, particelleOpacity: 0.8 });
    fireEvent.click(screen.getByRole("button", { name: "Satellite", exact: true }));
    expect(mocks.mapProps.basemap).toBe("satellite");
    for (const name of ["A ruolo", "Ruolo inferito", "Tutte"]) fireEvent.click(screen.getByRole("button", { name, exact: true }));
    expect(mocks.mapProps.mapLayers).toMatchObject({ particelleQuickFilter: "all" });
    fireEvent.click(screen.getByRole("button", { name: "Vista estesa" }));
    expect(screen.getByRole("button", { name: "Aree colorate" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.keyDown(window, { key: "a" });
    expect(screen.getByText("Vista estesa GIS")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi", exact: true }));
  });

  test("renders incomplete, historical and inferred parcel records without inventing missing data", async () => {
    render(<CatastoGisPage />);
    const variants = [
      { ...incompleteParticella, nome_comune: null, cod_comune_capacitas: null, num_distretto: null, nome_distretto: null, superficie_grafica_mq: null, source_type: null, missing_reason: null, missing_fields: [], n_anomalie_aperte: null, ha_ruolo_inferito: false, ruolo_summary: null, titolare: null, suppressed: false },
      { ...richParticella, cfm: null, nome_comune: null, subalterno: null, superficie_mq: null, ha_ruolo: false, ha_ruolo_inferito: false, ruolo_summary: null, swapped_capacitas: { source_codice_catastale: "X", source_comune_nome: null, source_foglio: null, source_particella: null, source_subalterno: null }, titolare: { codice_fiscale: null, partita_iva: "PIVA", denominazione: "Impresa", cco: null } },
      { ...incompleteParticella, codice_catastale: "A001", foglio: "1", particella: "", ha_ruolo: true, titolare: { subject_display_name: " ", denominazione: " ", codice_fiscale: " ", partita_iva: null }, swapped_capacitas: {}, ruolo_summary: { ...incompleteParticella.ruolo_summary, anno_tributario_richiesto: null } },
      { ...richParticella, cfm: null, foglio: "", nome_comune: null, codice_catastale: null, titolare: { subject_display_name: "Nome", subject_id: "subject-1" }, ruolo_summary: { ...richParticella.ruolo_summary, items: [{ anno_tributario: 2025, codice_partita: "P", codice_cnc: "C", subalterno: null, coltura: null }] } },
    ];
    for (const parcel of variants) {
      await act(async () => { (mocks.mapProps.onParticellaClick as (value: unknown) => void)(parcel); });
      const close = screen.getByRole("button", { name: "Chiudi dettaglio particella GIS" });
      expect(close).toBeInTheDocument();
      fireEvent.mouseDown(close.parentElement!);
      fireEvent.click(close.parentElement!);
      fireEvent.click(close);
      expect(screen.queryByRole("button", { name: "Chiudi dettaglio particella GIS" })).not.toBeInTheDocument();
    }
  });

  test("supports sparse DUI and delivery-point source records and popup dismissal", async () => {
    render(<CatastoGisPage />);
    await waitFor(() => expect(mocks.catastoGisGetDui2026LatestLayer).toHaveBeenCalled());
    for (const properties of [{}, { domanda_irrigua: 42, intestatario: "Fonte GIS", in_ruolo_2025: true }, { domanda_irrigua: "  " }]) {
      mocks.catastoGisGetDui2026DomandaDetail.mockResolvedValueOnce({ ruolo_summary: { n_righe: 1, n_subalterni: 0, items: [{ codice_partita: "P", codice_cnc: "C", subalterno: null, coltura: null }] } });
      await act(async () => { await (mocks.mapProps.onOverlayFeatureClick as (value: unknown) => Promise<void>)({ layer_key: "dui-2026-live", properties }); });
      const close = screen.getByRole("button", { name: "Chiudi dettaglio domanda DUI 2026" });
      fireEvent.mouseDown(close.parentElement!);
      fireEvent.click(close.parentElement!);
      fireEvent.click(close);
      expect(screen.queryByRole("button", { name: "Chiudi dettaglio domanda DUI 2026" })).not.toBeInTheDocument();
    }
    await act(async () => { (mocks.mapProps.onOverlayFeatureClick as (value: unknown) => void)(null); });
    const point = { id: "pdc-2", punto_consegna_code: "PDC-2", has_meter: false, linked_meter_readings_count: 3, tipologia: "Punto", tipo: "T", cod_cont: "C", photo_ref: "Foto", source_payload_json: { source: "INAZ" } };
    await act(async () => { (mocks.mapProps.onDeliveryPointClick as (value: unknown) => void)(point); });
    expect(screen.getByText(/"source": "INAZ"/)).toBeInTheDocument();
    const close = screen.getByRole("button", { name: "Chiudi dettaglio punto di consegna" });
    fireEvent.mouseDown(close.parentElement!);
    fireEvent.click(close.parentElement!);
    fireEvent.click(close);
    expect(screen.queryByText("Punto di attacco PDC-2")).not.toBeInTheDocument();
  });

  test("loads the map adapter lazily and renders its loading placeholder", async () => {
    expect(await mocks.mapLoader!()).toHaveProperty("default");
    render(<>{mocks.mapLoading!()}</>);
    expect(screen.getByText("Caricamento GIS...")).toBeInTheDocument();
  });

  test("handles sparse WhiteCompany properties and closes without propagating clicks", async () => {
    render(<CatastoGisPage />);
    for (const properties of [{}, { id: 3, external_code: 42, title: " ", created_at: null }]) {
      await act(async () => { (mocks.mapProps.onOverlayFeatureClick as (value: unknown) => void)({ layer_key: "whitecompany-reports", properties }); });
      expect(screen.getByRole("heading", { name: "Segnalazione WhiteCompany" })).toBeInTheDocument();
      const close = screen.getByRole("button", { name: "Chiudi dettaglio segnalazione WhiteCompany" });
      fireEvent.click(close.parentElement!);
      fireEvent.mouseDown(close.parentElement!);
      fireEvent.click(close);
      expect(screen.queryByRole("heading", { name: "Segnalazione WhiteCompany" })).not.toBeInTheDocument();
    }
  });

  test("resolves PIVA owners, ambiguous and unmatched fiscal identifiers", async () => {
    render(<CatastoGisPage />);
    const parcel = { ...richParticella, titolare: { denominazione: "Impresa", partita_iva: "PIVA", codice_fiscale: null, source: "intestatario", titoli: "Proprietario" } };
    await act(async () => { (mocks.mapProps.onParticellaClick as (value: unknown) => void)(parcel); });
    for (const [items, expected] of [
      [[{ id: "resolved", partita_iva: "PIVA", display_name: null }], "Subject resolved"],
      [[{ id: "a", partita_iva: "PIVA" }, { id: "b", codice_fiscale: "PIVA" }], "Identificatore fiscale associato a più soggetti GAIA."],
      [[{ id: "a", codice_fiscale: "DIFFERENTE" }], "Nessun soggetto GAIA trovato"],
    ] as const) {
      mocks.searchAnagraficaSubjects.mockResolvedValueOnce({ items });
      fireEvent.click(screen.getByRole("button", { name: "PIVA" }));
      expect(await screen.findByText(new RegExp(expected))).toBeInTheDocument();
      const close = screen.queryByText("Close subject");
      if (close) fireEvent.click(close);
    }
    mocks.searchAnagraficaSubjects.mockRejectedValueOnce(new Error("Ricerca fallita"));
    fireEvent.click(screen.getByRole("button", { name: "PIVA" }));
    expect(await screen.findByText("Ricerca fallita")).toBeInTheDocument();
  });

  test("renders selected parcel summaries in expanded view and toggles live DUI", async () => {
    mocks.selectionResult = { particelle: [
      { id: "a", nome_comune: "Comune", foglio: "1", particella: "2", subalterno: "3", superficie_mq: 100, ha_anomalie: true },
      { id: "b", superficie_grafica_mq: 50 }, { id: "c" },
    ], n_particelle: 3 };
    render(<CatastoGisPage />);
    await waitFor(() => expect(mocks.catastoGisGetDui2026LatestLayer).toHaveBeenCalled());
    fireEvent.click(screen.getByText("Toggle DUI"));
    expect(mocks.mapProps.mapLayers).toMatchObject({ showDui2026: true });
    fireEvent.click(screen.getByRole("button", { name: "Vista estesa" }));
    fireEvent.click(screen.getByText("Draw polygon"));
    fireEvent.click(screen.getByText("Map draw"));
    expect(await screen.findByText("Particelle Selezionate (3)")).toBeInTheDocument();
    expect(screen.getByText("100 mq")).toBeInTheDocument();
    expect(screen.getByText("50 mq")).toBeInTheDocument();
    expect(screen.getByText("Area ND")).toBeInTheDocument();
  });

  test.each([new Error("Errore rete"), "offline"])("surfaces archive and import failures: %s", async (failure) => {
    render(<CatastoGisPage />);
    await waitFor(() => expect(mocks.catastoGisListSavedSelections).toHaveBeenCalled());
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [] } });
    const file = { name: "test.xlsx", arrayBuffer: vi.fn().mockRejectedValue(failure) } as unknown as File;
    fireEvent.change(input, { target: { files: [file] } });
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Import Excel fallito")).toBeInTheDocument();
    mocks.catastoGisGetSavedSelection.mockRejectedValueOnce(failure);
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi in mappa" }));
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Caricamento layer fallito")).toBeInTheDocument();
    mocks.catastoGisDeleteSavedSelection.mockRejectedValueOnce(failure);
    fireEvent.click(screen.getByRole("button", { name: "Elimina" }));
    await waitFor(() => expect(mocks.catastoGisDeleteSavedSelection).toHaveBeenCalled());
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Eliminazione layer fallita")).toBeInTheDocument();
    mocks.catastoGisUpdateSavedSelection.mockRejectedValueOnce(failure);
    fireEvent.blur(document.querySelector('input[title="Modifica colore"]') as HTMLInputElement, { target: { value: "#112233" } });
    await waitFor(() => expect(mocks.catastoGisUpdateSavedSelection).toHaveBeenCalled());
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Aggiornamento colore fallito")).toBeInTheDocument();
  });

  test("imports alternate Excel headings and reports unmatched, ambiguous and geometry-free rows", async () => {
    render(<CatastoGisPage />);
    mocks.sheetToJson.mockReturnValue([
      { COMUNE: "A", FOGLIO: "1", PARTICELLA: "2", SEZIONE: "B", SUB: "3" },
      { comune: "A", foglio: "1", particella: "2", sezione: "", sub: " " },
      { Comune: "A", Foglio: "1", Particella: "2", Sezione: "B", Sub: "4" },
      { subalterno: "5" }, {},
    ]);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = { name: "test.xlsx", arrayBuffer: vi.fn().mockResolvedValue(new ArrayBuffer(8)) } as unknown as File;
    for (const result of [
      { processed: 5, found: 0, not_found: 5, multiple: 0, invalid: 0, results: [], geojson: null },
      { processed: 5, found: 1, not_found: 4, multiple: 0, invalid: 0, results: [{ esito: "FOUND", particella_id: "a" }], geojson: { type: "FeatureCollection", features: [{ type: "Feature", geometry: null }] } },
      { processed: 5, found: 2, not_found: 1, multiple: 1, invalid: 1, results: [{ esito: "NOT_FOUND" }, { esito: "FOUND", particella_id: "a" }], geojson: featureCollection },
      { processed: 5, found: 4, not_found: 0, multiple: 1, invalid: 0, results: [], geojson: featureCollection },
      { processed: 5, found: 4, not_found: 1, multiple: 0, invalid: 0, results: [], geojson: featureCollection },
    ]) {
      mocks.catastoGisResolveRefs.mockResolvedValueOnce(result);
      fireEvent.change(input, { target: { files: [file] } });
      await waitFor(() => expect(screen.queryByText("Caricamento…")).not.toBeInTheDocument());
      if (!result.found) expect(screen.getByText("Nessuna particella trovata su 5 righe.")).toBeInTheDocument();
      else expect(screen.getAllByText(/Bozza/).length).toBeGreaterThan(0);
    }
    expect(mocks.catastoGisResolveRefs).toHaveBeenCalledWith("token", expect.arrayContaining([expect.objectContaining({ comune: "A", foglio: "1", particella: "2", sub: null })]), { includeGeometry: true });
    const checkboxes = screen.getAllByRole("checkbox", { name: "Visibile" });
    fireEvent.click(checkboxes[1]);
    expect(checkboxes[1]).not.toBeChecked();
    fireEvent.click(checkboxes[1]);
    expect(checkboxes[1]).toBeChecked();
    fireEvent.change(screen.getAllByPlaceholderText("Nome layer")[1], { target: { value: " " } });
    fireEvent.click(screen.getAllByRole("button", { name: "Salva permanentemente" }).find((button) => !(button as HTMLButtonElement).disabled)!);
    expect(await screen.findByText("Inserisci un nome per salvare il layer.")).toBeInTheDocument();
  });

  test("autoloads a saved selection once and keeps archive controls effective before and after loading", async () => {
    window.history.replaceState({}, "", "/catasto/gis?selection=saved-1");
    mocks.catastoGisGetSavedSelection.mockResolvedValue({ ...savedSummary, geojson: null, import_summary: {} });
    render(<CatastoGisPage />);
    expect(await screen.findByText("Layer caricato: Archivio.")).toBeInTheDocument();
    expect(mocks.catastoGisGetSavedSelection).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Rimuovi" }));
    fireEvent.click(screen.getByRole("button", { name: "Riempimento" }));
    await waitFor(() => expect(mocks.catastoGisGetSavedSelection).toHaveBeenCalledTimes(2));
    fireEvent.click(screen.getByRole("button", { name: "Rimuovi" }));
    fireEvent.change(screen.getAllByRole("slider").at(-1)!, { target: { value: "30" } });
    await waitFor(() => expect(mocks.catastoGisGetSavedSelection).toHaveBeenCalledTimes(3));
    fireEvent.blur(document.querySelector('input[title="Modifica colore"]') as HTMLInputElement, { target: { value: "#112233" } });
    await waitFor(() => expect(mocks.catastoGisUpdateSavedSelection).toHaveBeenCalled());
    expect(mocks.mapProps.overlayLayers).toEqual(expect.arrayContaining([expect.objectContaining({ color: "#112233", opacity: 0.3 })]));
    fireEvent.click(screen.getByRole("button", { name: "Elimina" }));
    await waitFor(() => expect(screen.queryByPlaceholderText("Nome layer")).not.toBeInTheDocument());
  });

  test.each([new Error("Servizio indisponibile"), "offline"])("preserves error feedback across bootstrap and metadata actions: %s", async (failure) => {
    mocks.catastoListDistretti.mockRejectedValueOnce(failure);
    mocks.catastoGisListSavedSelections.mockRejectedValueOnce(failure);
    mocks.catastoGisGetDui2026LatestLayer.mockRejectedValueOnce(failure);
    mocks.catastoGisGetWhiteCompanyReportLayer.mockRejectedValueOnce(failure);
    render(<CatastoGisPage />);
    await waitFor(() => expect(mocks.catastoGisGetWhiteCompanyReportLayer).toHaveBeenCalled());
    mocks.catastoRefreshDeliveryPointsGisCache.mockResolvedValueOnce({ tile_revision: "rev-2", martin_restarted: false, restart_error: "Martin fermo" });
    fireEvent.click(screen.getAllByRole("button", { name: "Aggiorna cache" })[0]);
    expect(await screen.findByText(/Cache aggiornata, Martin non riavviato/)).toBeInTheDocument();
    mocks.catastoRefreshDeliveryPointsGisCache.mockRejectedValueOnce(failure);
    fireEvent.click(screen.getAllByRole("button", { name: "Aggiorna cache" })[0]);
    await waitFor(() => expect(mocks.catastoRefreshDeliveryPointsGisCache).toHaveBeenCalledTimes(2));
    mocks.catastoGisExport.mockRejectedValueOnce(failure);
    fireEvent.click(screen.getByText("Export csv"));
    await waitFor(() => expect(mocks.catastoGisExport).toHaveBeenCalled());
    fireEvent.click(screen.getByText("Export geojson"));
    await waitFor(() => expect(mocks.catastoGisExport).toHaveBeenCalledTimes(2));
    const file = { name: "test.xlsx", arrayBuffer: vi.fn().mockResolvedValue(new ArrayBuffer(8)) } as unknown as File;
    fireEvent.change(document.querySelector('input[type="file"]')!, { target: { files: [file] } });
    await screen.findByText("Bozza");
    mocks.catastoGisCreateSavedSelection.mockRejectedValueOnce(failure);
    fireEvent.click(screen.getByRole("button", { name: "Salva permanentemente" }));
    expect((await screen.findAllByText(failure instanceof Error ? failure.message : "Salvataggio layer fallito")).length).toBeGreaterThan(0);
    mocks.catastoGisCreateSavedSelection.mockResolvedValueOnce({ ...savedSummary, geojson: null });
    fireEvent.click(screen.getByRole("button", { name: "Salva permanentemente" }));
    await screen.findByText("Salvato");
    fireEvent.change(screen.getByPlaceholderText("Nome layer"), { target: { value: "" } });
    mocks.catastoGisUpdateSavedSelection.mockRejectedValueOnce(failure);
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna metadati salvati" }));
    expect((await screen.findAllByText(failure instanceof Error ? failure.message : "Aggiornamento layer fallito")).length).toBeGreaterThan(0);
    expect(mocks.catastoGisUpdateSavedSelection).toHaveBeenCalledWith("token", "saved-1", expect.objectContaining({ name: undefined }));
    mocks.capacitasGetRptCertificatoLink.mockRejectedValueOnce(failure);
    fireEvent.click(screen.getByText("Map parcel rich"));
    fireEvent.click(screen.getByRole("button", { name: /Apri intestatario su Capacitas/i }));
    await waitFor(() => expect(mocks.capacitasGetRptCertificatoLink).toHaveBeenCalled());
    mocks.catastoGisGetDui2026DomandaDetail.mockRejectedValueOnce(failure);
    fireEvent.click(screen.getByText("Map dui"));
    await waitFor(() => expect(mocks.catastoGisGetDui2026DomandaDetail).toHaveBeenCalled());
  });

  test("clears district search, expands its list and toggles its parcel detail", async () => {
    mocks.catastoListDistretti.mockResolvedValue([{ id: "a", num_distretto: "A" }, { id: "b", num_distretto: "B" }]);
    render(<CatastoGisPage />);
    fireEvent.click(await screen.findByRole("button", { name: /Distretto A/ }));
    await waitFor(() => expect(mocks.catastoGetDistrettoGeojson).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: "Mostra riempimento particelle" }));
    expect(mocks.mapProps.mapLayers).toMatchObject({ showParticelleFill: true });
    fireEvent.click(screen.getByRole("button", { name: /Distretti irrigui/ }));
    fireEvent.click(screen.getByRole("button", { name: /Distretti irrigui/ }));
    fireEvent.change(screen.getByPlaceholderText("Cerca per numero o nome"), { target: { value: "B" } });
    fireEvent.click(screen.getByRole("button", { name: "Pulisci filtro distretti" }));
    expect(screen.getByPlaceholderText("Cerca per numero o nome")).toHaveValue("");
  });

  test("dismisses parcel help and delivery-point overlays through their backdrop", async () => {
    render(<CatastoGisPage />);
    fireEvent.click(screen.getByText("Map parcel rich"));
    fireEvent.click(screen.getByRole("button", { name: /Approfondisci come e stato determinato/ }));
    fireEvent.click(screen.getByRole("button", { name: "Chiudi", exact: true }));
    expect(screen.queryByText("Approfondimento ruolo")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Map delivery"));
    const close = screen.getByRole("button", { name: "Chiudi dettaglio punto di consegna" });
    fireEvent.click(close.closest(".absolute.inset-0")!);
    expect(screen.queryByRole("button", { name: "Chiudi dettaglio punto di consegna" })).not.toBeInTheDocument();
  });

  test.each([null, { type: "FeatureCollection", features: [] }, { type: "FeatureCollection", features: [
    { ...featureCollection.features[0], properties: { category: "geometrie_variate", geometry_source: "gaia", particella_id: "p1" } },
    { ...featureCollection.features[0], properties: { category: "nuove_in_ade" } },
    { ...featureCollection.features[0], properties: { category: "unknown" } },
    { ...featureCollection.features[0], properties: null },
  ] }])("handles completed AdE previews with absent or mixed geometries", async (geojson) => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mocks.catastoGisGetLatestAdeWfsRunStatus.mockResolvedValue({ ...adeRun, status: "queued" });
    mocks.catastoGisGetAdeWfsRunStatus.mockResolvedValue(adeRun);
    mocks.catastoGisGetAdeAlignmentReport.mockResolvedValue({ ...adeReport, geojson });
    const view = render(<CatastoGisPage />);
    await screen.findByText("In coda");
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi in mappa" }));
    await screen.findByText("Layer caricato: Archivio.");
    await act(async () => { await vi.advanceTimersByTimeAsync(2500); });
    expect(screen.getByText(/Run comprensorio AdE completato/)).toBeInTheDocument();
    const layers = mocks.mapProps.overlayLayers as Array<{ layer_key: string; geojson: { features: Array<{ properties: { __overlayColor: string } }> } }>;
    expect(layers.some((layer) => layer.layer_key.startsWith("ade-preview"))).toBe(Boolean(geojson?.features.length));
    if (geojson?.features.length) expect(layers.find((layer) => layer.layer_key.startsWith("ade-preview"))!.geojson.features[0].properties.__overlayColor).toBe("#1D4ED8");
    view.unmount();
    vi.useRealTimers();
  });

  test.each(["failed", "failed-empty", "processing", "error", "string-error"])("handles AdE polling state %s", async (status) => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mocks.catastoGisGetLatestAdeWfsRunStatus.mockResolvedValue({ ...adeRun, status: "queued" });
    if (status === "error") mocks.catastoGisGetAdeWfsRunStatus.mockRejectedValue(new Error("Polling error"));
    else if (status === "string-error") mocks.catastoGisGetAdeWfsRunStatus.mockRejectedValue("offline");
    else mocks.catastoGisGetAdeWfsRunStatus.mockResolvedValue({ ...adeRun, status: status === "failed-empty" ? "failed" : status, error: status === "failed" ? "Run fallito" : null });
    const view = render(<CatastoGisPage />);
    await screen.findByText("In coda");
    await act(async () => { await vi.advanceTimersByTimeAsync(2500); });
    expect(mocks.catastoGisGetAdeWfsRunStatus).toHaveBeenCalled();
    view.unmount();
    vi.useRealTimers();
  });

  test("polls an active AdE run to completion", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const queued = { ...adeRun, status: "queued", progress_phase: "queued", progress_percent: 0, completed_at: null };
    mocks.catastoGisGetLatestAdeWfsRunStatus.mockResolvedValueOnce(queued);
    mocks.catastoGisGetAdeWfsRunStatus.mockResolvedValueOnce(adeRun);
    render(<CatastoGisPage />);
    await screen.findByText("In coda");
    await vi.advanceTimersByTimeAsync(2500);
    await waitFor(() => expect(mocks.catastoGisGetAdeWfsRunStatus).toHaveBeenCalledWith("token", adeRun.run_id));
    expect(await screen.findByText(/Run comprensorio AdE completato/)).toBeInTheDocument();
    vi.useRealTimers();
  });

  test("keeps panel event boundaries fail-closed without a session or a loaded selection", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);
    mocks.selectionResult = null;
    render(<CatastoGisPage />);
    expect(screen.queryByText("Selection panel")).not.toBeInTheDocument();
    expect(mocks.mapProps.selectedIds).toEqual([]);
    await act(async () => {
      await mocks.whiteProps.onLoadLayer();
      mocks.districtProps.onSelectDistretto({ id: "d1", num_distretto: "1" } as never);
      mocks.archiveProps.onRemoveLoaded("missing");
    });
    expect(mocks.catastoGisGetWhiteCompanyReportLayer).not.toHaveBeenCalled();
    expect(mocks.catastoGetDistrettoGeojson).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText("Map parcel rich"));
    fireEvent.click(screen.getByRole("button", { name: /Apri intestatario su Capacitas/ }));
    expect(mocks.capacitasGetRptCertificatoLink).not.toHaveBeenCalled();
  });

  test("reports district request failures and incomplete owner identifiers", async () => {
    mocks.catastoGetDistrettoGeojson.mockRejectedValueOnce(new Error("Distretto non disponibile"));
    render(<CatastoGisPage />);
    fireEvent.click(await screen.findByRole("button", { name: /Distretto 1/ }));
    expect(await screen.findByText("Distretto non disponibile")).toBeInTheDocument();
    await act(async () => {
      (mocks.mapProps.onParticellaClick as (value: unknown) => void)({ ...richParticella, titolare: { cco: " ", codice_fiscale: " ", denominazione: " ", subject_display_name: " " } });
    });
    fireEvent.click(screen.getByRole("button", { name: /Apri intestatario su Capacitas/ }));
    expect(mocks.capacitasGetRptCertificatoLink).not.toHaveBeenCalled();
    const fiscalButton = document.querySelector('button.font-mono');
    expect(fiscalButton).not.toBeNull();
    fireEvent.click(fiscalButton!);
    expect(await screen.findByText("Nessun soggetto GAIA collegato a questo identificativo fiscale.")).toBeInTheDocument();
    expect(mocks.searchAnagraficaSubjects).not.toHaveBeenCalled();
  });

  test("renders missing role identifiers, campaign anomalies and unreconciled owners", async () => {
    render(<CatastoGisPage />);
    await act(async () => {
      (mocks.mapProps.onParticellaClick as (value: unknown) => void)({
        ...richParticella, titolare: null,
        anomalie_aperte: [{ id: "campaign", tipo: "chiave", severita: "warning", descrizione: null, anno_campagna: 2025 }],
        ruolo_summary: { ...richParticella.ruolo_summary, items: [{ anno_tributario: 2025, domanda_irrigua: "D-12", subalterno: null, codice_partita: null }] },
      });
    });
    expect(screen.getByText("Anno ruolo 2025")).toBeInTheDocument();
    expect(screen.getByText("Particella a ruolo, ma titolare non ancora riconciliato nel GIS.")).toBeInTheDocument();
    expect(screen.getByText("Domanda D-12")).toBeInTheDocument();
    expect(screen.getByText("Sub ND")).toBeInTheDocument();
    expect(screen.getByText("chiave")).toBeInTheDocument();
    const detail = await mocks.catastoGisGetDui2026DomandaDetail();
    mocks.catastoGisGetDui2026DomandaDetail.mockResolvedValueOnce({ ...detail, ruolo_summary: { ...detail.ruolo_summary, items: [{ ...detail.ruolo_summary.items[0], coltura: "Riso" }] } });
    fireEvent.click(screen.getByText("Map dui"));
    expect(await screen.findByText(/Riso/)).toBeInTheDocument();
  });
});
