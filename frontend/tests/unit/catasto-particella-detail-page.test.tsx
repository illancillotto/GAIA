import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import type { CatAnomalia, CatParticellaConsorzio, CatParticellaDetail, CatParticellaHistory, CatUtenzaIrrigua } from "@/types/catasto";

const mocks = vi.hoisted(() => ({
  routeId: "parcel-1",
  embedded: true,
  back: vi.fn(),
  getStoredAccessToken: vi.fn(),
  catastoGetParticella: vi.fn(),
  catastoGetParticellaConsorzio: vi.fn(),
  catastoGetParticellaHistory: vi.fn(),
  catastoGetParticellaUtenze: vi.fn(),
  catastoGetParticellaAnomalie: vi.fn(),
  catastoSyncParticellaCapacitas: vi.fn(),
  catastoUpdateAnomalia: vi.fn(),
  capacitasGetRptCertificatoLink: vi.fn(),
  searchAnagraficaSubjects: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: mocks.routeId }),
  useRouter: () => ({ back: mocks.back }),
  useSearchParams: () => ({ get: () => mocks.embedded ? "1" : null }),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.getStoredAccessToken }));
vi.mock("@/lib/api", () => ({ searchAnagraficaSubjects: mocks.searchAnagraficaSubjects }));
vi.mock("@/lib/api/catasto", () => ({
  capacitasGetRptCertificatoLink: mocks.capacitasGetRptCertificatoLink,
  catastoGetParticella: mocks.catastoGetParticella,
  catastoGetParticellaAnomalie: mocks.catastoGetParticellaAnomalie,
  catastoGetParticellaConsorzio: mocks.catastoGetParticellaConsorzio,
  catastoGetParticellaHistory: mocks.catastoGetParticellaHistory,
  catastoGetParticellaUtenze: mocks.catastoGetParticellaUtenze,
  catastoSyncParticellaCapacitas: mocks.catastoSyncParticellaCapacitas,
  catastoUpdateAnomalia: mocks.catastoUpdateAnomalia,
}));
vi.mock("@/lib/catasto-anomalie", () => ({ describeCatastoAnomalia: (anomalia: { id: string }) => `Motivo ${anomalia.id}` }));

vi.mock("@/components/catasto/catasto-page", () => ({
  CatastoPage: ({ children, title }: { children: ReactNode; title: string }) => <main><h1>{title}</h1>{children}</main>,
}));
vi.mock("@/components/ui/alert-banner", () => ({
  AlertBanner: ({ children, title }: { children: ReactNode; title: string }) => <div role="alert"><strong>{title}</strong>{children}</div>,
}));
vi.mock("@/components/ui/metric-card", () => ({
  MetricCard: ({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) => <div data-testid={`metric-${label}`}>{label}:{value}{sub ? `:${sub}` : ""}</div>,
}));
vi.mock("@/components/catasto/AnomaliaStatusBadge", () => ({ AnomaliaStatusBadge: ({ severita }: { severita: string }) => <span>Severità {severita}</span> }));
vi.mock("@/components/catasto/AnomaliaStatusPill", () => ({ AnomaliaStatusPill: ({ status }: { status: string }) => <span>Stato {status}</span> }));
vi.mock("@/components/catasto/catasto-anomalia-explainer", () => ({ CatastoAnomaliaExplainer: ({ anomalia }: { anomalia: { id: string } }) => <span>Explainer {anomalia.id}</span> }));
vi.mock("@/components/utenze/utenze-subject-quick-view-dialog", () => ({
  UtenzeSubjectQuickViewDialog: ({ subjectId, subjectLabel, onClose }: { subjectId: string; subjectLabel: string | null; onClose: () => void }) => <div role="dialog">Soggetto {subjectId} {subjectLabel}<button type="button" onClick={onClose}>Chiudi soggetto</button></div>,
}));
vi.mock("@/components/table/data-table", () => ({
  DataTable: ({ data, columns, emptyTitle }: { data: unknown[]; columns: Array<{ cell?: unknown }>; emptyTitle?: string }) => (
    <div data-testid={`table-${emptyTitle ?? "history"}`}>
      {data.length === 0 ? emptyTitle : data.map((original, rowIndex) => (
        <div key={rowIndex}>
          {columns.map((column, columnIndex) => typeof column.cell === "function" ? <div key={columnIndex}>{(column.cell as (context: unknown) => ReactNode)({ row: { original } })}</div> : null)}
        </div>
      ))}
    </div>
  ),
}));

import CatastoParticellaDetailPage from "@/app/catasto/particelle/[id]/page";

const currentYear = 2026;
const item = {
  id: "parcel-1",
  foglio: "14",
  particella: "82",
  subalterno: "3",
  nome_comune: "Marrubiu",
  cod_comune_capacitas: 123,
  codice_catastale: "E972",
  num_distretto: "01",
  fuori_distretto: true,
  capacitas_last_sync_at: "2026-01-02T10:00:00Z",
  capacitas_last_sync_status: "ok",
  capacitas_last_sync_error: "Avviso sync",
  superficie_mq: "10000",
  superficie_grafica_mq: "9000",
  indice_irriguo_finale: "1.2",
  indice_irriguo_gruppo_coltura: "Seminativi",
  indice_irriguo_moltiplicatore: "1.1",
  indice_irriguo_comune_arborea: true,
  indice_irriguo_coltura: "Mais",
  indice_irriguo_sup_irrigata_ha: "2.5",
  indice_irriguo_importo_stimato: "100",
  indice_irriguo_euro_mc: "0.2",
  indice_irriguo_anno_riferimento: 2026,
  valid_from: "2026-01-01",
  source_type: "capacitas",
  is_current: true,
  swapped_capacitas: {
    source_codice_catastale: "A001",
    source_comune_nome: "Terralba",
    source_foglio: "9",
    source_particella: "10",
    source_subalterno: "2",
    anno_tributario_latest: 2025,
    n_righe_ruolo: 4,
  },
} as CatParticellaDetail;

const linkedUtenza = {
  id: "utenza-linked",
  anno_campagna: currentYear,
  cco: "123",
  cod_frazione: "4",
  codice_fiscale: "AAA111",
  subject_id: "subject-linked",
  subject_display_name: "Mario Rossi",
  denominazione: "Rossi",
  importo_0648: "10",
  importo_0985: "20",
} as CatUtenzaIrrigua;
const lookupUtenza = { ...linkedUtenza, id: "utenza-lookup", cco: "456", subject_id: null, subject_display_name: null, codice_fiscale: " BBB 222 " } as CatUtenzaIrrigua;
const subjectOnlyUtenza = { ...linkedUtenza, id: "utenza-subject-only", cco: null, subject_id: "subject-only", subject_display_name: null, denominazione: null, codice_fiscale: null } as CatUtenzaIrrigua;
const emptyUtenza = { ...linkedUtenza, id: "utenza-empty", cco: null, cod_frazione: null, subject_id: null, subject_display_name: null, denominazione: null, codice_fiscale: null, importo_0648: null, importo_0985: null } as CatUtenzaIrrigua;

const openAnomalia = { id: "anomalia-open", anno_campagna: currentYear, status: "aperta", severita: "error", tipo: "mismatch", descrizione: "Anomalia aperta" } as CatAnomalia;
const closedAnomalia = { id: "anomalia-closed", anno_campagna: null, status: "aperta", severita: "warning", tipo: "closed", descrizione: null } as CatAnomalia;
const history = [
  { history_id: "history-1", valid_from: "2025-01-01", valid_to: "2025-12-31", num_distretto: "01", superficie_mq: "10000", superficie_grafica_mq: "9000", change_reason: "update" },
  { history_id: "history-2", valid_from: "2024-01-01", valid_to: "2024-12-31", num_distretto: null, superficie_mq: null, superficie_grafica_mq: null, change_reason: null },
] as CatParticellaHistory[];

const currentOccupancy = { id: "occupancy-current", utenza_id: linkedUtenza.id, relationship_type: "utilizzatore", cco: "123", source_type: "capacitas", valid_from: "2026-01-01", valid_to: null, is_current: true, com: "001", pvc: "002", fra: "3", ccs: "4", updated_at: "2026-01-01" };
const historicOccupancy = { ...currentOccupancy, id: "occupancy-old", is_current: false, cco: null, valid_from: null, valid_to: "2025-12-31" };
const person = { cognome: "Rossi", nome: "Mario", codice_fiscale: "AAA111", indirizzo: "Via Roma", comune_residenza: "Marrubiu" };
const owner = { id: "owner-1", denominazione: "Mario Rossi", deceduto: true, codice_fiscale: "AAA111", titoli: "Proprietà", data_nascita: "1980-01-01", luogo_nascita: "Oristano", residenza: "Via Roma", comune_residenza: "Marrubiu", person, person_snapshots: [{ id: "snapshot" }] };
const ownerWithoutPerson = { ...owner, id: "owner-2", denominazione: null, deceduto: false, codice_fiscale: null, titoli: null, data_nascita: null, luogo_nascita: null, residenza: null, comune_residenza: null, person: null, person_snapshots: [] };
const ownerWithComune = { ...owner, id: "owner-3", person: { ...person, indirizzo: null }, person_snapshots: [] };
const ownerWithoutResidence = { ...owner, id: "owner-4", person: { ...person, indirizzo: null, comune_residenza: null }, person_snapshots: [] };
const unit = { id: "unit-1", foglio: "14", particella: "82", subalterno: "3", comune_label: "Marrubiu", cod_comune_capacitas: 123, source_comune_resolved_label: "Terralba", source_comune_label: null, source_cod_comune_capacitas: 321, comune_resolution_mode: "source_match", source_codice_catastale: "A001", source_last_seen: "2026-01-01", source_first_seen: "2025-01-01", is_active: true, occupancies: [currentOccupancy, historicOccupancy], intestatari_proprietari: [owner, ownerWithoutPerson, ownerWithComune, ownerWithoutResidence] };
const emptyUnit = { ...unit, id: "unit-empty", foglio: null, particella: null, subalterno: null, comune_label: null, cod_comune_capacitas: null, source_comune_resolved_label: null, source_comune_label: null, source_cod_comune_capacitas: null, comune_resolution_mode: null, source_codice_catastale: null, source_last_seen: null, source_first_seen: null, is_active: false, occupancies: [], intestatari_proprietari: [] };
const consorzio = { particella_id: item.id, units: [unit, emptyUnit] } as CatParticellaConsorzio;

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((promiseResolve) => { resolve = promiseResolve; });
  return { promise, resolve };
}

describe("CatastoParticellaDetailPage", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date("2026-06-01T12:00:00Z"));
    mocks.routeId = "parcel-1";
    mocks.embedded = true;
    mocks.back.mockReset();
    mocks.getStoredAccessToken.mockReset().mockReturnValue("token");
    mocks.catastoGetParticella.mockReset().mockResolvedValue(item);
    mocks.catastoGetParticellaConsorzio.mockReset().mockResolvedValue(consorzio);
    mocks.catastoGetParticellaHistory.mockReset().mockResolvedValue(history);
    mocks.catastoGetParticellaUtenze.mockReset().mockResolvedValue([linkedUtenza, lookupUtenza, subjectOnlyUtenza, emptyUtenza]);
    mocks.catastoGetParticellaAnomalie.mockReset().mockResolvedValue([openAnomalia, closedAnomalia]);
    mocks.catastoSyncParticellaCapacitas.mockReset().mockResolvedValue({ particella: item, message: "Sync completata" });
    mocks.catastoUpdateAnomalia.mockReset().mockResolvedValue(openAnomalia);
    mocks.capacitasGetRptCertificatoLink.mockReset().mockResolvedValue({ url: "https://capacitas.test/report" });
    mocks.searchAnagraficaSubjects.mockReset().mockResolvedValue({ items: [] });
    vi.spyOn(window, "open").mockImplementation(() => null);
  });

  test("preserves the full detail workflow and user actions", async () => {
    render(<CatastoParticellaDetailPage />);

    expect(await screen.findByRole("heading", { name: "Fg.14 Part.82 Sub.3" })).toBeInTheDocument();
    expect(screen.getByText("Comune Capacitas/Ruolo diverso dal comune GAIA")).toBeInTheDocument();
    expect(screen.getAllByText("Anagrafica GAIA corrente")).toHaveLength(3);
    expect(screen.getByText("Nessun intestatario strutturato ancora disponibile per questa unità.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Indietro" }));
    expect(mocks.back).toHaveBeenCalledOnce();

    fireEvent.click(screen.getByRole("button", { name: "Sincronizza con Capacitas" }));
    expect(await screen.findByText("Sync completata")).toBeInTheDocument();
    expect(mocks.catastoSyncParticellaCapacitas).toHaveBeenCalledWith("token", "parcel-1");

    const certificate = deferred<{ url: string }>();
    mocks.capacitasGetRptCertificatoLink.mockReturnValueOnce(certificate.promise);
    fireEvent.click(screen.getAllByRole("button", { name: "Visualizza su Capacitas" })[0]);
    expect((await screen.findAllByRole("button", { name: "Apertura…" }))[0]).toBeDisabled();
    certificate.resolve({ url: "https://capacitas.test/deferred" });
    await waitFor(() => expect(window.open).toHaveBeenCalledWith("https://capacitas.test/deferred", "_blank", "noopener,noreferrer"));

    await screen.findAllByRole("button", { name: "Visualizza su Capacitas" });
    const linkedSubjectButton = screen.getAllByText("AAA111").map((element) => element.closest("button")).find(Boolean);
    fireEvent.click(linkedSubjectButton!);
    expect(await screen.findByRole("dialog")).toHaveTextContent("subject-linked Mario Rossi");
    fireEvent.click(screen.getByRole("button", { name: "Chiudi soggetto" }));

    fireEvent.click(screen.getByRole("button", { name: /—Apri dettaglio soggetto/ }));
    expect(await screen.findByRole("dialog")).toHaveTextContent("subject-only");
    fireEvent.click(screen.getByRole("button", { name: "Chiudi soggetto" }));

    mocks.searchAnagraficaSubjects.mockResolvedValueOnce({ items: [{ id: "subject-resolved", codice_fiscale: "BBB222", partita_iva: null }] });
    fireEvent.click(screen.getByRole("button", { name: /BBB 222/ }));
    expect(await screen.findByRole("dialog")).toHaveTextContent("subject-resolved");
    fireEvent.click(screen.getByRole("button", { name: "Chiudi soggetto" }));

    const subjectLookup = deferred<{ items: Array<{ id: string; codice_fiscale: string }> }>();
    mocks.searchAnagraficaSubjects.mockReturnValueOnce(subjectLookup.promise);
    fireEvent.click(screen.getByRole("button", { name: /BBB 222/ }));
    expect(await screen.findByRole("button", { name: /Apertura…/ })).toBeDisabled();
    subjectLookup.resolve({ items: [] });
    await screen.findByText(/Nessun soggetto GAIA trovato/);

    fireEvent.click(screen.getAllByRole("button", { name: "Chiudi" })[0]);
    await waitFor(() => expect(mocks.catastoUpdateAnomalia).toHaveBeenCalledWith("token", "anomalia-open", { status: "chiusa" }));
    fireEvent.click(screen.getAllByRole("button", { name: "Ignora" })[0]);
    fireEvent.click(screen.getAllByRole("button", { name: "Riapri" })[0]);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "2025" } });
    await waitFor(() => expect(mocks.catastoGetParticellaUtenze).toHaveBeenCalledWith("token", "parcel-1", { anno: 2025 }));
  });

  test("selects the latest populated year when the current year is empty", async () => {
    mocks.catastoGetParticellaUtenze.mockImplementation((_token, _id, params) => Promise.resolve(params ? (params.anno === 2024 ? [linkedUtenza] : []) : [{ ...linkedUtenza, anno_campagna: 2024 }]));
    mocks.catastoGetParticellaAnomalie.mockImplementation((_token, _id, params) => Promise.resolve(params ? [] : [{ ...openAnomalia, anno_campagna: 2023 }]));

    render(<CatastoParticellaDetailPage />);

    await waitFor(() => expect(screen.getByRole("combobox")).toHaveValue("2024"));
    expect(mocks.catastoGetParticellaUtenze).toHaveBeenCalledWith("token", "parcel-1");
  });

  test("keeps the current year when no fallback data exists", async () => {
    mocks.catastoGetParticellaUtenze.mockResolvedValue([]);
    mocks.catastoGetParticellaAnomalie.mockResolvedValue([]);
    mocks.catastoGetParticellaConsorzio.mockResolvedValue({ particella_id: "parcel-1", units: [] });
    mocks.catastoGetParticella.mockResolvedValue({
      ...item,
      subalterno: null,
      nome_comune: null,
      num_distretto: null,
      fuori_distretto: false,
      capacitas_last_sync_at: null,
      capacitas_last_sync_status: null,
      capacitas_last_sync_error: null,
      superficie_mq: null,
      superficie_grafica_mq: null,
      indice_irriguo_finale: null,
      indice_irriguo_gruppo_coltura: null,
      indice_irriguo_comune_arborea: false,
      indice_irriguo_coltura: null,
      indice_irriguo_sup_irrigata_ha: null,
      indice_irriguo_importo_stimato: null,
      indice_irriguo_euro_mc: null,
      indice_irriguo_anno_riferimento: null,
      is_current: false,
      swapped_capacitas: null,
    });
    mocks.embedded = false;

    render(<CatastoParticellaDetailPage />);

    await waitFor(() => expect(screen.getByRole("combobox")).toHaveValue(String(currentYear)));
    expect(screen.queryByRole("button", { name: "Indietro" })).not.toBeInTheDocument();
    expect(screen.getByText("Nessun dato consortile ancora consolidato per questa particella.")).toBeInTheDocument();
    expect(screen.queryByText("Perche questa particella ha anomalie ruolo")).not.toBeInTheDocument();
  });

  test.each([
    ["E972", "A001", "E972", "A001"],
    [null, null, "Comune ND", "Comune ND"],
  ])("renders swapped municipality fallbacks for %p and %p", async (gaiaCode, sourceCode, gaiaLabel, sourceLabel) => {
    mocks.catastoGetParticella.mockResolvedValue({
      ...item,
      nome_comune: null,
      codice_catastale: gaiaCode,
      swapped_capacitas: {
        ...item.swapped_capacitas!,
        source_comune_nome: null,
        source_codice_catastale: sourceCode,
        source_foglio: null,
        source_particella: null,
        source_subalterno: null,
        anno_tributario_latest: null,
      },
    });

    render(<CatastoParticellaDetailPage />);

    await screen.findByRole("heading", { name: "Fg.14 Part.82 Sub.3" });
    expect(screen.getAllByText(gaiaLabel).length).toBeGreaterThan(0);
    expect(screen.getAllByText(sourceLabel).length).toBeGreaterThan(0);
    expect(screen.getByText(/Rif. sorgente —\/— · 4 righe ruolo collegate/)).toBeInTheDocument();
  });

  test.each([
    [new Error("Load failed"), "Load failed"],
    ["failed", "Errore caricamento particella"],
  ])("reports load failure %p", async (failure, message) => {
    mocks.catastoGetParticella.mockRejectedValue(failure);
    render(<CatastoParticellaDetailPage />);
    expect((await screen.findAllByRole("alert")).some((alert) => alert.textContent?.includes(message))).toBe(true);
    expect(screen.getByText("Non risultano dati per l’ID richiesto.")).toBeInTheDocument();
  });

  test("preserves action error messages and subject disambiguation", async () => {
    render(<CatastoParticellaDetailPage />);
    await screen.findByRole("heading", { name: "Fg.14 Part.82 Sub.3" });

    mocks.catastoSyncParticellaCapacitas.mockRejectedValueOnce(new Error("Sync failed")).mockRejectedValueOnce("failed");
    fireEvent.click(screen.getByRole("button", { name: "Sincronizza con Capacitas" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Sync failed");
    fireEvent.click(screen.getByRole("button", { name: "Sincronizza con Capacitas" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Errore sync particella Capacitas");

    mocks.capacitasGetRptCertificatoLink.mockRejectedValueOnce(new Error("Link failed")).mockRejectedValueOnce("failed");
    fireEvent.click(screen.getAllByRole("button", { name: "Visualizza su Capacitas" })[0]);
    expect(await screen.findByText("Link failed")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Visualizza su Capacitas" })[0]);
    expect(await screen.findByText("Errore generazione link Capacitas")).toBeInTheDocument();

    const lookupButton = screen.getByRole("button", { name: /BBB 222/ });
    mocks.searchAnagraficaSubjects.mockResolvedValueOnce({ items: [{ id: "one", codice_fiscale: "BBB222" }, { id: "two", partita_iva: "BBB222" }] });
    fireEvent.click(lookupButton);
    expect(await screen.findByText(/piu soggetti GAIA/)).toBeInTheDocument();
    mocks.searchAnagraficaSubjects.mockResolvedValueOnce({ items: [] });
    fireEvent.click(lookupButton);
    expect(await screen.findByText(/Nessun soggetto GAIA trovato/)).toBeInTheDocument();
    mocks.searchAnagraficaSubjects.mockRejectedValueOnce(new Error("Lookup failed"));
    fireEvent.click(lookupButton);
    expect(await screen.findByText("Lookup failed")).toBeInTheDocument();
    mocks.searchAnagraficaSubjects.mockRejectedValueOnce("failed");
    fireEvent.click(lookupButton);
    expect(await screen.findByText("Errore apertura dettaglio soggetto")).toBeInTheDocument();

  });

  test("does not start protected actions without an access token", async () => {
    render(<CatastoParticellaDetailPage />);
    await screen.findByRole("heading", { name: "Fg.14 Part.82 Sub.3" });
    mocks.getStoredAccessToken.mockReturnValue(null);

    fireEvent.click(screen.getByRole("button", { name: "Sincronizza con Capacitas" }));
    fireEvent.click(screen.getAllByRole("button", { name: "Visualizza su Capacitas" })[0]);
    fireEvent.click(screen.getAllByRole("button", { name: "Chiudi" })[0]);
    fireEvent.click(screen.getByRole("button", { name: /BBB 222/ }));

    expect(mocks.catastoSyncParticellaCapacitas).not.toHaveBeenCalled();
    expect(mocks.capacitasGetRptCertificatoLink).not.toHaveBeenCalled();
    expect(mocks.catastoUpdateAnomalia).not.toHaveBeenCalled();
    expect(await screen.findByText("Nessun soggetto GAIA collegato a questa utenza.")).toBeInTheDocument();
  });

  test("keeps the loading state when the session token is absent", () => {
    mocks.getStoredAccessToken.mockReturnValue(null);
    render(<CatastoParticellaDetailPage />);
    expect(screen.getAllByText("Caricamento…").length).toBeGreaterThan(0);
    expect(mocks.catastoGetParticella).not.toHaveBeenCalled();
  });
});
