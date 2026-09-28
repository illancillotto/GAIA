import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import * as XLSX from "xlsx";

import { AnagraficaBulkPanel } from "@/components/catasto/anagrafica/AnagraficaBulkPanel";

vi.mock("xlsx", async (importOriginal) => {
  const actual = await importOriginal<typeof import("xlsx")>();
  return { ...actual, read: vi.fn(actual.read) };
});

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  catastoCreateElaborazioneMassivaScopeExportJob: vi.fn(),
  catastoDeleteElaborazioniMassiveJobs: vi.fn(),
  catastoDownloadElaborazioneMassivaDistrettoExportJob: vi.fn(),
  catastoDownloadElaborazioneMassivaJobExport: vi.fn(),
  catastoGetElaborazioneMassivaDistrettoExportJob: vi.fn(),
  catastoGetElaborazioneMassivaJob: vi.fn(),
  catastoListElaborazioneMassivaDistrettoExportJobs: vi.fn(),
  catastoListDistretti: vi.fn(),
  catastoListComuniExport: vi.fn(),
  catastoDownloadComuneExport: vi.fn(),
  catastoListElaborazioniMassiveJobs: vi.fn(),
  catastoUploadElaborazioneMassivaJob: vi.fn(),
}));
const table = vi.hoisted(() => ({ columns: [] as unknown[] }));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.getStoredAccessToken }));
vi.mock("@/lib/api/catasto-distretto-export-jobs", () => ({
  catastoCreateElaborazioneMassivaScopeExportJob: mocks.catastoCreateElaborazioneMassivaScopeExportJob,
  catastoDownloadElaborazioneMassivaDistrettoExportJob: mocks.catastoDownloadElaborazioneMassivaDistrettoExportJob,
  catastoGetElaborazioneMassivaDistrettoExportJob: mocks.catastoGetElaborazioneMassivaDistrettoExportJob,
  catastoListElaborazioneMassivaDistrettoExportJobs: mocks.catastoListElaborazioneMassivaDistrettoExportJobs,
}));
vi.mock("@/lib/api/catasto", () => ({
  catastoDeleteElaborazioniMassiveJobs: mocks.catastoDeleteElaborazioniMassiveJobs,
  catastoDownloadElaborazioneMassivaJobExport: mocks.catastoDownloadElaborazioneMassivaJobExport,
  catastoGetElaborazioneMassivaJob: mocks.catastoGetElaborazioneMassivaJob,
  catastoListDistretti: mocks.catastoListDistretti,
  catastoListComuniExport: mocks.catastoListComuniExport,
  catastoDownloadComuneExport: mocks.catastoDownloadComuneExport,
  catastoListElaborazioniMassiveJobs: mocks.catastoListElaborazioniMassiveJobs,
  catastoUploadElaborazioneMassivaJob: mocks.catastoUploadElaborazioneMassivaJob,
}));
vi.mock("@/components/table/data-table", () => ({
  DataTable: ({ columns }: { columns: unknown[] }) => {
    table.columns = columns;
    return <div data-testid="bulk-results" />;
  },
}));

const kind = "CF_PIVA_PARTICELLE";

function bulkRow(overrides: Record<string, unknown> = {}) {
  return {
    row_index: 1,
    comune_input: null,
    sezione_input: null,
    foglio_input: null,
    particella_input: null,
    sub_input: null,
    codice_fiscale_input: "RSSMRA80A01H501U",
    partita_iva_input: null,
    esito: "FOUND",
    message: "Trovato",
    particella_id: null,
    match: null,
    matches: null,
    matches_count: 1,
    ...overrides,
  };
}

function bulkJob(overrides: Record<string, unknown> = {}) {
  return {
    id: "bulk-1",
    created_at: "2026-07-16T10:00:00Z",
    started_at: "2026-07-16T10:00:01Z",
    completed_at: "2026-07-16T10:00:02Z",
    source_filename: "input.csv",
    kind,
    status: "completed",
    skipped_rows: 0,
    total_rows: 1,
    processed_rows: 1,
    current_label: null,
    error_message: null,
    summary: { total: 1, found: 1, notFound: 0, multiple: 0, invalid: 0, error: 0 },
    results: [bulkRow()],
    ...overrides,
  };
}

function scopeJob(overrides: Record<string, unknown> = {}) {
  return {
    id: "scope-1", status: "completed", scope_kind: "distretti", scope_values: ["01"],
    num_distretto: "01", nome_distretto: "Nord", format: "csv", processed_rows: 1,
    current_label: null, error_message: null, output_filename: "scope.csv",
    ...overrides,
  };
}

function csvFile(contents: string): File {
  const file = new File([contents], "input.csv", { type: "text/csv" });
  Object.defineProperty(file, "text", { value: async () => contents });
  return file;
}

function spreadsheetFile(headers: string[]): File {
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet([headers]), "Sheet1");
  const buffer = XLSX.write(workbook, { type: "array", bookType: "xlsx" }) as ArrayBuffer;
  const file = new File([buffer], "input.xlsx");
  Object.defineProperty(file, "arrayBuffer", { value: async () => buffer });
  return file;
}

function selectFile(file: File): void {
  fireEvent.change(document.getElementById("catasto-bulk-file") as HTMLInputElement, {
    target: { files: [file] },
  });
}

function renderCell(index: number, row: ReturnType<typeof bulkRow>): string {
  const column = table.columns[index] as {
    cell: (context: { row: { original: ReturnType<typeof bulkRow> } }) => ReactNode;
  };
  const view = render(<>{column.cell({ row: { original: row } })}</>);
  const html = view.container.innerHTML;
  view.unmount();
  return html;
}

describe("AnagraficaBulkPanel bulk workflow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.catastoListElaborazioniMassiveJobs.mockResolvedValue({ items: [] });
    mocks.catastoListElaborazioneMassivaDistrettoExportJobs.mockResolvedValue({ items: [] });
    mocks.catastoListDistretti.mockResolvedValue([]);
    mocks.catastoListComuniExport.mockResolvedValue([]);
    mocks.catastoDeleteElaborazioniMassiveJobs.mockResolvedValue(undefined);
    mocks.catastoDownloadElaborazioneMassivaJobExport.mockResolvedValue(new Blob(["csv"]));
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:bulk");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("does not load protected lists without a token", () => {
    mocks.getStoredAccessToken.mockReturnValue(null);
    render(<AnagraficaBulkPanel />);
    expect(mocks.catastoListElaborazioniMassiveJobs).not.toHaveBeenCalled();
    expect(screen.getByText("Nessuna operazione salvata.")).toBeInTheDocument();
  });

  test("keeps available lists when unrelated startup requests fail", async () => {
    mocks.catastoListElaborazioniMassiveJobs.mockRejectedValue(new Error("history"));
    mocks.catastoListDistretti.mockRejectedValue(new Error("districts"));
    mocks.catastoListComuniExport.mockRejectedValue(new Error("comuni"));
    render(<AnagraficaBulkPanel />);
    expect(await screen.findByText("Errore caricamento distretti.")).toBeInTheDocument();
    expect(screen.getByText("Nessuna operazione salvata.")).toBeInTheDocument();
  });

  test("validates a tax-id CSV, runs a completed job and exports both formats", async () => {
    mocks.catastoUploadElaborazioneMassivaJob.mockResolvedValue(bulkJob());
    render(<AnagraficaBulkPanel />);

    selectFile(csvFile("codice_fiscale,partita_iva\nRSSMRA80A01H501U,"));
    expect(await screen.findByText(/pronto per upload backend/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Elabora righe file/i }));
    expect(await screen.findByText("Elaborazione completata", { selector: "p" })).toBeInTheDocument();
    expect(screen.getByTestId("bulk-results")).toBeInTheDocument();
    expect(mocks.catastoUploadElaborazioneMassivaJob).toHaveBeenCalledWith("token", expect.objectContaining({ name: "input.csv" }));

    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    fireEvent.click(screen.getByRole("button", { name: "Export CSV" }));
    await waitFor(() => expect(mocks.catastoDownloadElaborazioneMassivaJobExport).toHaveBeenCalledWith("token", "bulk-1", "csv"));
    fireEvent.click(screen.getByRole("button", { name: "Export Excel" }));
    await waitFor(() => expect(mocks.catastoDownloadElaborazioneMassivaJobExport).toHaveBeenCalledWith("token", "bulk-1", "xlsx"));
    expect(HTMLAnchorElement.prototype.click).toHaveBeenCalledTimes(2);
  });

  test("rejects invalid headers and allows resetting the selected file", async () => {
    render(<AnagraficaBulkPanel />);
    selectFile(csvFile("foglio,particella\n5,120"));
    expect(await screen.findByText(/Colonne minime mancanti/)).toBeInTheDocument();

    selectFile(csvFile("comune,foglio,particella\nA357,5,120"));
    expect(await screen.findByText(/pronto per upload backend/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Reset" }));
    expect(screen.getAllByText("Nessun file selezionato")).toHaveLength(2);
    expect(screen.getByRole("button", { name: /Elabora righe file/i })).toBeDisabled();
  });

  test("downloads the four unchanged CSV and Excel templates", async () => {
    render(<AnagraficaBulkPanel />);
    await act(async () => undefined);
    const csvButtons = screen.getAllByRole("button", { name: "Template CSV" });
    const excelButtons = screen.getAllByRole("button", { name: "Template Excel" });
    for (const button of [...csvButtons, ...excelButtons]) fireEvent.click(button);
    expect(HTMLAnchorElement.prototype.click).toHaveBeenCalledTimes(4);
  });

  test("deletes saved history only after confirmation", async () => {
    mocks.catastoListElaborazioniMassiveJobs.mockResolvedValue({ items: [bulkJob()] });
    render(<AnagraficaBulkPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Cancella storico" }));
    expect(mocks.catastoDeleteElaborazioniMassiveJobs).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Annulla" }));
    fireEvent.click(screen.getByRole("button", { name: "Cancella storico" }));
    const confirmation = screen.getByText("Cancellare lo storico?").parentElement;
    fireEvent.click(within(confirmation as HTMLElement).getByRole("button", { name: "Cancella storico" }));
    await waitFor(() => expect(mocks.catastoDeleteElaborazioniMassiveJobs).toHaveBeenCalledWith("token"));
    expect(screen.getByText("Nessuna operazione salvata.")).toBeInTheDocument();
  });

  test("renders each result status and the cadastral and tax detail columns", async () => {
    mocks.catastoListElaborazioniMassiveJobs.mockResolvedValue({ items: [bulkJob()] });
    mocks.catastoGetElaborazioneMassivaJob.mockResolvedValue(bulkJob({
      results: [bulkRow({
        match: {
          comune: "Arborea", cod_comune_capacitas: "A357", num_distretto: "01", superficie_mq: 10000,
          intestatari: [],
        },
        matches_count: 2,
      })],
    }));
    render(<AnagraficaBulkPanel />);
    fireEvent.click((await screen.findAllByRole("button", { name: "Ricarica risultati" }))[0]);
    expect(await screen.findByTestId("bulk-results")).toBeInTheDocument();

    const taxRow = bulkRow({
      match: { comune: "Arborea", num_distretto: "01", superficie_mq: 10000, intestatari: [] },
      matches_count: 2,
    });
    expect(renderCell(0, taxRow)).toContain("1");
    expect(renderCell(1, taxRow)).toContain("RSSMRA80A01H501U");
    expect(renderCell(3, taxRow)).toContain("Trovato");
    expect(renderCell(4, taxRow)).toContain("Particelle trovate: 2");
    expect(renderCell(4, bulkRow())).toContain("—");
    for (const esito of ["FOUND", "NOT_FOUND", "MULTIPLE_MATCHES", "INVALID_ROW", "ERROR"]) {
      expect(renderCell(2, bulkRow({ esito }))).toContain(esito);
    }

    mocks.catastoGetElaborazioneMassivaJob.mockResolvedValue(bulkJob({
      kind: "COMUNE_FOGLIO_PARTICELLA_INTESTATARI",
      results: [bulkRow({ comune_input: "Arborea" })],
    }));
    fireEvent.click(screen.getByRole("button", { name: "Ricarica risultati" }));
    await waitFor(() => expect(screen.getByText(/Particelle → Intestatari/)).toBeInTheDocument());
    const cadastralRow = bulkRow({
      comune_input: "Arborea", sezione_input: "A", foglio_input: "5", particella_input: "120", sub_input: "1",
      match: {
        comune: null, cod_comune_capacitas: "A357", num_distretto: null, superficie_mq: null,
        intestatari: [
          { cognome: "Rossi", nome: "Mario" },
          { denominazione: "Societa" },
          { ragione_sociale: "Impresa" },
          { cognome: "Verdi", nome: "Anna" },
        ],
      },
    });
    expect(renderCell(1, cadastralRow)).toContain("Sez.A Fg.5 Part.120 Sub.1");
    expect(renderCell(4, cadastralRow)).toContain("Rossi Mario · Societa · Impresa (+1)");
  });

  test("reloads and reexports a saved job, preserving the history status labels", async () => {
    mocks.catastoListElaborazioniMassiveJobs.mockResolvedValue({ items: [
      bulkJob({ id: "pending", status: "pending", skipped_rows: 2, current_label: "Attesa" }),
      bulkJob({ id: "processing", status: "processing" }),
      bulkJob({ id: "failed", status: "failed" }),
      bulkJob({ id: "completed", status: "completed" }),
    ] });
    mocks.catastoGetElaborazioneMassivaJob.mockResolvedValue(bulkJob({ id: "pending" }));
    render(<AnagraficaBulkPanel />);
    expect(await screen.findByText("IN CODA")).toBeInTheDocument();
    expect(screen.getByText("IN ELABORAZIONE")).toBeInTheDocument();
    expect(screen.getByText("FALLITO")).toBeInTheDocument();
    expect(screen.getByText("COMPLETATO")).toBeInTheDocument();
    expect(screen.getByText(/2 righe vuote saltate/)).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Ricarica risultati" })[0]);
    await waitFor(() => expect(mocks.catastoGetElaborazioneMassivaJob).toHaveBeenCalledWith("token", "pending"));
    fireEvent.click(screen.getAllByRole("button", { name: "Riesporta CSV" })[0]);
    await waitFor(() => expect(mocks.catastoDownloadElaborazioneMassivaJobExport).toHaveBeenCalledWith("token", "pending", "csv"));
    fireEvent.click(screen.getAllByRole("button", { name: "Riesporta Excel" })[0]);
    await waitFor(() => expect(mocks.catastoDownloadElaborazioneMassivaJobExport).toHaveBeenCalledWith("token", "pending", "xlsx"));
  });

  test("accepts a cadastral spreadsheet and reports empty or unreadable input", async () => {
    render(<AnagraficaBulkPanel />);
    selectFile(spreadsheetFile(["comune", "foglio", "particella"]));
    expect(await screen.findByText(/pronto per upload backend/)).toBeInTheDocument();

    selectFile(csvFile(""));
    expect(await screen.findByText(/Colonne minime mancanti/)).toBeInTheDocument();

    const broken = new File(["comune,foglio,particella"], "broken.csv");
    Object.defineProperty(broken, "text", { value: async () => { throw "parse failed"; } });
    selectFile(broken);
    expect(await screen.findByText("Errore parsing file")).toBeInTheDocument();
  });

  test("polls a pending bulk job and keeps the completed results", async () => {
    mocks.catastoUploadElaborazioneMassivaJob.mockResolvedValue(bulkJob({
      status: "pending", completed_at: null, processed_rows: 0, total_rows: 2, results: [], current_label: null,
    }));
    mocks.catastoGetElaborazioneMassivaJob.mockResolvedValue(bulkJob({
      status: "completed", processed_rows: 2, total_rows: 2,
      results: [bulkRow({ esito: "NOT_FOUND" }), bulkRow({ row_index: 2, esito: "ERROR" })],
      current_label: null,
    }));
    render(<AnagraficaBulkPanel />);
    selectFile(csvFile("codice_fiscale\nRSSMRA80A01H501U"));
    await screen.findByText(/pronto per upload backend/);
    fireEvent.click(await screen.findByRole("button", { name: /Elabora righe file/i }));
    await waitFor(() => expect(mocks.catastoGetElaborazioneMassivaJob).toHaveBeenCalledWith("token", "bulk-1"), { timeout: 3000 });
    expect(await screen.findByText("2 di 2 righe")).toBeInTheDocument();
    expect(screen.getByTestId("bulk-results")).toBeInTheDocument();
    expect(screen.getByText("NOT_FOUND: 1")).toBeInTheDocument();
  });

  test("shows failed and rejected bulk jobs without losing the progress dialog", async () => {
    mocks.catastoUploadElaborazioneMassivaJob
      .mockResolvedValueOnce(bulkJob({ status: "failed", error_message: null, results: [] }))
      .mockRejectedValueOnce("upload failed");
    render(<AnagraficaBulkPanel />);
    selectFile(csvFile("codice_fiscale\nRSSMRA80A01H501U"));
    await screen.findByText(/pronto per upload backend/);
    fireEvent.click(await screen.findByRole("button", { name: /Elabora righe file/i }));
    expect(await screen.findAllByText("Errore elaborazione massiva")).not.toHaveLength(0);
    expect(screen.getByText("Elaborazione interrotta")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    fireEvent.click(screen.getByRole("button", { name: /Elabora righe file/i }));
    await waitFor(() => expect(mocks.catastoUploadElaborazioneMassivaJob).toHaveBeenCalledTimes(2));
    expect(screen.getByText("Elaborazione interrotta")).toBeInTheDocument();
  });

  test("keeps the history on deletion failure and shows both error variants", async () => {
    mocks.catastoListElaborazioniMassiveJobs.mockResolvedValue({ items: [bulkJob()] });
    mocks.catastoDeleteElaborazioniMassiveJobs
      .mockRejectedValueOnce(new Error("delete failed"))
      .mockRejectedValueOnce("not an Error");
    render(<AnagraficaBulkPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Cancella storico" }));
    const confirmation = screen.getByText("Cancellare lo storico?").parentElement as HTMLElement;
    fireEvent.click(within(confirmation).getByRole("button", { name: "Cancella storico" }));
    expect(await screen.findByText("delete failed")).toBeInTheDocument();
    fireEvent.click(within(confirmation).getByRole("button", { name: "Cancella storico" }));
    expect(await screen.findByText("Errore cancellazione storico")).toBeInTheDocument();
    expect(screen.getByText("input.csv")).toBeInTheDocument();
  });

  test("rejects workbooks without sheets or headers", async () => {
    const read = vi.mocked(XLSX.read);
    read.mockReturnValueOnce({ SheetNames: [], Sheets: {} } as XLSX.WorkBook);
    render(<AnagraficaBulkPanel />);
    selectFile(csvFile("x"));
    expect(await screen.findByText("File vuoto o senza fogli leggibili.")).toBeInTheDocument();

    read.mockReturnValueOnce({ SheetNames: ["Sheet1"], Sheets: { Sheet1: XLSX.utils.aoa_to_sheet([]) } } as XLSX.WorkBook);
    selectFile(csvFile("y"));
    expect(await screen.findByText("File vuoto o senza intestazioni.")).toBeInTheDocument();
  });

  test("handles a failed resumed export poll and cancellation on unmount", async () => {
    const pending = {
      id: "scope-pending", status: "processing", scope_kind: "distretti", scope_values: ["01"],
      num_distretto: "01", nome_distretto: null, format: "csv", processed_rows: 0,
      current_label: null, error_message: null,
    };
    mocks.catastoListElaborazioneMassivaDistrettoExportJobs.mockResolvedValue({ items: [pending] });
    mocks.catastoGetElaborazioneMassivaDistrettoExportJob.mockRejectedValue(new Error("poll failed"));
    const view = render(<AnagraficaBulkPanel />);
    expect(await screen.findByRole("status")).toHaveTextContent("Export distretto in corso");
    expect(await screen.findByText("poll failed", {}, { timeout: 3000 })).toBeInTheDocument();
    view.unmount();

    mocks.catastoGetElaborazioneMassivaDistrettoExportJob.mockClear();
    const cancelled = render(<AnagraficaBulkPanel />);
    await screen.findByRole("status");
    cancelled.unmount();
    await new Promise((resolve) => window.setTimeout(resolve, 1600));
    expect(mocks.catastoGetElaborazioneMassivaDistrettoExportJob).not.toHaveBeenCalled();
  });

  test("keeps history and exports idle when the token disappears", async () => {
    mocks.catastoListElaborazioniMassiveJobs.mockResolvedValue({ items: [bulkJob()] });
    render(<AnagraficaBulkPanel />);
    await screen.findByRole("button", { name: "Cancella storico" });
    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: "Cancella storico" }));
    const confirmation = screen.getByText("Cancellare lo storico?").parentElement as HTMLElement;
    fireEvent.click(within(confirmation).getByRole("button", { name: "Cancella storico" }));
    fireEvent.click(screen.getByRole("button", { name: "Ricarica risultati" }));
    fireEvent.click(screen.getByRole("button", { name: "Riesporta CSV" }));
    fireEvent.click(screen.getByRole("button", { name: "Riesporta Excel" }));
    expect(mocks.catastoDeleteElaborazioniMassiveJobs).not.toHaveBeenCalled();
    expect(mocks.catastoGetElaborazioneMassivaJob).not.toHaveBeenCalled();
    expect(mocks.catastoDownloadElaborazioneMassivaJobExport).not.toHaveBeenCalled();
  });

  test("shows errors from reload and history exports without dropping the saved job", async () => {
    mocks.catastoListElaborazioniMassiveJobs.mockResolvedValue({ items: [bulkJob()] });
    mocks.catastoGetElaborazioneMassivaJob
      .mockRejectedValueOnce(new Error("reload failed"))
      .mockRejectedValueOnce("unknown reload");
    mocks.catastoDownloadElaborazioneMassivaJobExport
      .mockRejectedValueOnce(new Error("csv failed"))
      .mockRejectedValueOnce("unknown export");
    render(<AnagraficaBulkPanel />);
    const reload = await screen.findByRole("button", { name: "Ricarica risultati" });
    fireEvent.click(reload);
    expect(await screen.findByText("reload failed")).toBeInTheDocument();
    fireEvent.click(reload);
    expect(await screen.findByText("Errore caricamento job")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Riesporta CSV" }));
    expect(await screen.findByText("csv failed")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Riesporta Excel" }));
    expect(await screen.findByText("Errore export job")).toBeInTheDocument();
    expect(screen.getByText("input.csv")).toBeInTheDocument();
  });

  test("counts every result kind and preserves both operation labels", async () => {
    mocks.catastoUploadElaborazioneMassivaJob.mockResolvedValue(bulkJob({
      results: [
        bulkRow({ esito: "FOUND" }), bulkRow({ esito: "NOT_FOUND" }),
        bulkRow({ esito: "MULTIPLE_MATCHES" }), bulkRow({ esito: "INVALID_ROW" }),
        bulkRow({ esito: "ERROR" }),
      ],
      summary: { total: 5, found: 1, notFound: 1, multiple: 1, invalid: 1, error: 1 },
    }));
    mocks.catastoListElaborazioniMassiveJobs.mockResolvedValue({ items: [
      bulkJob({ id: "cadastral", kind: "COMUNE_FOGLIO_PARTICELLA_INTESTATARI" }),
      bulkJob({ id: "unknown", kind: "OTHER" }),
    ] });
    render(<AnagraficaBulkPanel />);
    expect(await screen.findByText(/Tipo non rilevato/)).toBeInTheDocument();
    expect(screen.getByText(/Particelle -> Intestatari/)).toBeInTheDocument();
    selectFile(csvFile("codice_fiscale\nRSSMRA80A01H501U"));
    await screen.findByText(/pronto per upload backend/);
    fireEvent.click(screen.getByRole("button", { name: /Elabora righe file/i }));
    expect(await screen.findByText("INVALID: 1")).toBeInTheDocument();
    expect(screen.getAllByText("MULTIPLE: 1")).not.toHaveLength(0);
  });

  test("handles absent file, invalid values and fallback result cells", async () => {
    mocks.catastoListElaborazioniMassiveJobs.mockResolvedValue({ items: [bulkJob()] });
    mocks.catastoGetElaborazioneMassivaJob.mockResolvedValue(bulkJob());
    render(<AnagraficaBulkPanel />);
    fireEvent.change(document.getElementById("catasto-bulk-file") as HTMLInputElement, { target: { files: [] } });
    fireEvent.click(await screen.findByRole("button", { name: "Ricarica risultati" }));
    await screen.findByTestId("bulk-results");
    expect(renderCell(1, bulkRow({ codice_fiscale_input: null, partita_iva_input: "123" }))).toContain("123");
    expect(renderCell(1, bulkRow({ codice_fiscale_input: null, partita_iva_input: null }))).toContain("—");
    expect(renderCell(4, bulkRow({ match: {
      comune: null, cod_comune_capacitas: null, num_distretto: null,
      superficie_mq: "not-a-number", intestatari: [],
    } }))).toContain("0,00 ha");
    expect(renderCell(4, bulkRow({ match: {
      comune: null, cod_comune_capacitas: null, num_distretto: null,
      superficie_mq: null, intestatari: [],
    } }))).toContain("—");

    mocks.catastoGetElaborazioneMassivaJob.mockResolvedValue(bulkJob({
      kind: "COMUNE_FOGLIO_PARTICELLA_INTESTATARI", results: [bulkRow()],
    }));
    fireEvent.click(screen.getByRole("button", { name: "Ricarica risultati" }));
    await waitFor(() => expect(screen.getByText(/Particelle → Intestatari/)).toBeInTheDocument());
    expect(renderCell(1, bulkRow({ comune_input: null, foglio_input: null, particella_input: null }))).toContain("Fg.— Part.—");
  });

  test("shows fallback labels for unknown results, missing filenames and empty progress", async () => {
    mocks.catastoListElaborazioniMassiveJobs.mockResolvedValue({ items: [bulkJob({ source_filename: null })] });
    mocks.catastoUploadElaborazioneMassivaJob.mockResolvedValue(bulkJob({
      results: [bulkRow({ esito: "OTHER" })], current_label: "", summary: {
        total: 1, found: 0, notFound: 0, multiple: 0, invalid: 0, error: 0,
      },
    }));
    render(<AnagraficaBulkPanel />);
    expect(await screen.findByText("Elaborazione senza file")).toBeInTheDocument();
    selectFile(csvFile("codice_fiscale\nRSSMRA80A01H501U"));
    await screen.findByText(/pronto per upload backend/);
    fireEvent.click(screen.getByRole("button", { name: /Elabora righe file/i }));
    expect(await screen.findByText("Riga corrente:")).toBeInTheDocument();
    expect(screen.getByText("Elaborazione completata.")).toBeInTheDocument();
  });

  test("does not start processing or exporting after the token expires", async () => {
    mocks.catastoListElaborazioniMassiveJobs.mockResolvedValue({ items: [bulkJob()] });
    mocks.catastoGetElaborazioneMassivaJob.mockResolvedValue(bulkJob());
    render(<AnagraficaBulkPanel />);
    selectFile(csvFile("codice_fiscale\nRSSMRA80A01H501U"));
    await screen.findByText(/pronto per upload backend/);
    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: /Elabora righe file/i }));
    expect(mocks.catastoUploadElaborazioneMassivaJob).not.toHaveBeenCalled();

    mocks.getStoredAccessToken.mockReturnValue("token");
    fireEvent.click(screen.getByRole("button", { name: "Ricarica risultati" }));
    await screen.findByTestId("bulk-results");
    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: "Export CSV" }));
    expect(mocks.catastoDownloadElaborazioneMassivaJobExport).not.toHaveBeenCalled();
  });

  test("exports the cadastral job and handles a token missing from the comune dialog", async () => {
    mocks.catastoListElaborazioniMassiveJobs.mockResolvedValue({ items: [bulkJob()] });
    mocks.catastoGetElaborazioneMassivaJob.mockResolvedValue(bulkJob({
      kind: "COMUNE_FOGLIO_PARTICELLA_INTESTATARI", results: [bulkRow()],
    }));
    mocks.catastoListComuniExport.mockResolvedValue([{ codice: "A357", nome: "Arborea" }]);
    render(<AnagraficaBulkPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Ricarica risultati" }));
    await screen.findByTestId("bulk-results");
    fireEvent.click(screen.getByRole("button", { name: "Export CSV" }));
    await waitFor(() => expect(mocks.catastoDownloadElaborazioneMassivaJobExport).toHaveBeenCalledWith("token", "bulk-1", "csv"));
    fireEvent.click(await screen.findByRole("checkbox", { name: /Arborea/ }));
    fireEvent.click(screen.getByRole("button", { name: /Export CSV comuni/ }));
    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: /Esporta con dato GAIA/ }));
    expect(mocks.catastoDownloadComuneExport).not.toHaveBeenCalled();
  });

  test("keeps polling a scope export that remains pending before completion", async () => {
    mocks.catastoListDistretti.mockResolvedValue([{ num_distretto: "01", nome_distretto: "Nord" }]);
    mocks.catastoListElaborazioneMassivaDistrettoExportJobs.mockResolvedValue({ items: [scopeJob({ id: "old" })] });
    mocks.catastoCreateElaborazioneMassivaScopeExportJob.mockResolvedValue(scopeJob({ status: "pending" }));
    mocks.catastoGetElaborazioneMassivaDistrettoExportJob
      .mockResolvedValueOnce(scopeJob({ status: "processing" }))
      .mockResolvedValue(scopeJob());
    mocks.catastoDownloadElaborazioneMassivaDistrettoExportJob.mockResolvedValue(new Blob(["csv"]));
    render(<AnagraficaBulkPanel />);
    fireEvent.click(await screen.findByRole("checkbox", { name: /01 · Nord/ }));
    fireEvent.click(screen.getByRole("button", { name: /Export CSV distretti/ }));
    await waitFor(() => expect(mocks.catastoGetElaborazioneMassivaDistrettoExportJob).toHaveBeenCalledTimes(2), { timeout: 4500 });
    await waitFor(() => expect(mocks.catastoDownloadElaborazioneMassivaDistrettoExportJob).toHaveBeenCalledWith("token", "scope-1"), { timeout: 4500 });
    expect(screen.getAllByText("Distretto 01 · Nord · CSV")).not.toHaveLength(0);
  });

  test("handles a resumed scope job that stays pending or is cancelled after request", async () => {
    mocks.catastoListElaborazioneMassivaDistrettoExportJobs.mockResolvedValue({ items: [scopeJob({ status: "pending" })] });
    mocks.catastoGetElaborazioneMassivaDistrettoExportJob.mockResolvedValueOnce(scopeJob({ status: "processing" }));
    const first = render(<AnagraficaBulkPanel />);
    await waitFor(() => expect(mocks.catastoGetElaborazioneMassivaDistrettoExportJob).toHaveBeenCalled(), { timeout: 3000 });
    first.unmount();

    let resolve!: (job: ReturnType<typeof scopeJob>) => void;
    mocks.catastoGetElaborazioneMassivaDistrettoExportJob.mockReset();
    mocks.catastoGetElaborazioneMassivaDistrettoExportJob.mockReturnValue(new Promise((res) => { resolve = res; }));
    const second = render(<AnagraficaBulkPanel />);
    await waitFor(() => expect(mocks.catastoGetElaborazioneMassivaDistrettoExportJob).toHaveBeenCalled(), { timeout: 3000 });
    second.unmount();
    await act(async () => resolve(scopeJob()));
  });

  test("renders short owner lists and normal tax matches without a count badge", async () => {
    mocks.catastoListElaborazioniMassiveJobs.mockResolvedValue({ items: [bulkJob()] });
    mocks.catastoGetElaborazioneMassivaJob.mockResolvedValue(bulkJob());
    render(<AnagraficaBulkPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Ricarica risultati" }));
    await screen.findByTestId("bulk-results");
    expect(renderCell(4, bulkRow({ match: {
      comune: "Arborea", num_distretto: "01", superficie_mq: 10000, intestatari: [],
    }, matches_count: 1 }))).not.toContain("Particelle trovate");
    mocks.catastoGetElaborazioneMassivaJob.mockResolvedValue(bulkJob({
      kind: "COMUNE_FOGLIO_PARTICELLA_INTESTATARI", results: [bulkRow()],
    }));
    fireEvent.click(screen.getByRole("button", { name: "Ricarica risultati" }));
    await waitFor(() => expect(screen.getByText(/Particelle → Intestatari/)).toBeInTheDocument());
    expect(renderCell(4, bulkRow({ match: {
      comune: "Arborea", num_distretto: "01", superficie_mq: 10000,
      intestatari: [{ cognome: "Rossi", nome: "Mario" }],
    } }))).not.toContain("(+");
  });

  test("keeps cadastral filenames and fallback comune codes in downloads", async () => {
    mocks.catastoListElaborazioniMassiveJobs.mockResolvedValue({ items: [bulkJob({
      kind: "COMUNE_FOGLIO_PARTICELLA_INTESTATARI",
    })] });
    mocks.catastoListComuniExport.mockResolvedValue([{ codice: "A357", nome: undefined }]);
    mocks.catastoDownloadElaborazioneMassivaJobExport.mockResolvedValue(new Blob(["csv"]));
    mocks.catastoDownloadComuneExport.mockResolvedValue(new Blob(["csv"]));
    render(<AnagraficaBulkPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Riesporta CSV" }));
    await waitFor(() => expect(mocks.catastoDownloadElaborazioneMassivaJobExport).toHaveBeenCalledWith("token", "bulk-1", "csv"));
    fireEvent.click(screen.getByRole("button", { name: "Riesporta Excel" }));
    await waitFor(() => expect(mocks.catastoDownloadElaborazioneMassivaJobExport).toHaveBeenCalledWith("token", "bulk-1", "xlsx"));
    fireEvent.click(await screen.findByRole("checkbox", { name: /A357/ }));
    fireEvent.click(screen.getByRole("button", { name: /Export CSV comuni/ }));
    fireEvent.click(screen.getByRole("button", { name: /Esporta con dato GAIA/ }));
    await waitFor(() => expect(mocks.catastoDownloadComuneExport).toHaveBeenCalledWith("token", "A357", "csv", "gaia"));
  });

  test("handles non-Error polling failures and ignores rejection after unmount", async () => {
    mocks.catastoListElaborazioneMassivaDistrettoExportJobs.mockResolvedValue({ items: [scopeJob({ status: "pending" })] });
    mocks.catastoGetElaborazioneMassivaDistrettoExportJob.mockRejectedValueOnce("not an Error");
    const first = render(<AnagraficaBulkPanel />);
    expect(await screen.findByText("Errore aggiornamento export distretto", {}, { timeout: 3000 })).toBeInTheDocument();
    first.unmount();

    let reject!: (reason: unknown) => void;
    mocks.catastoGetElaborazioneMassivaDistrettoExportJob.mockReset();
    mocks.catastoGetElaborazioneMassivaDistrettoExportJob.mockReturnValue(new Promise((_, no) => { reject = no; }));
    const second = render(<AnagraficaBulkPanel />);
    await waitFor(() => expect(mocks.catastoGetElaborazioneMassivaDistrettoExportJob).toHaveBeenCalled(), { timeout: 3000 });
    second.unmount();
    await act(async () => reject(new Error("ignored after unmount")));
  });

  test("continues bulk polling while the server still reports processing", async () => {
    mocks.catastoUploadElaborazioneMassivaJob.mockResolvedValue(bulkJob({ status: "pending", results: [] }));
    mocks.catastoGetElaborazioneMassivaJob
      .mockResolvedValueOnce(bulkJob({ status: "processing", results: [], current_label: null }))
      .mockResolvedValue(bulkJob());
    render(<AnagraficaBulkPanel />);
    selectFile(csvFile("codice_fiscale\nRSSMRA80A01H501U"));
    await screen.findByText(/pronto per upload backend/);
    fireEvent.click(screen.getByRole("button", { name: /Elabora righe file/i }));
    await waitFor(() => expect(mocks.catastoGetElaborazioneMassivaJob).toHaveBeenCalledTimes(2), { timeout: 4500 });
    expect(await screen.findByTestId("bulk-results")).toBeInTheDocument();
  });

  test("uses the default match count and both history export error branches", async () => {
    mocks.catastoListElaborazioniMassiveJobs.mockResolvedValue({ items: [bulkJob()] });
    mocks.catastoGetElaborazioneMassivaJob.mockResolvedValue(bulkJob());
    mocks.catastoDownloadElaborazioneMassivaJobExport
      .mockRejectedValueOnce("csv rejected")
      .mockRejectedValueOnce(new Error("xlsx rejected"));
    render(<AnagraficaBulkPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Ricarica risultati" }));
    await screen.findByTestId("bulk-results");
    expect(renderCell(4, bulkRow({ match: {
      comune: "Arborea", num_distretto: "01", superficie_mq: 10000, intestatari: [],
    }, matches_count: null }))).not.toContain("Particelle trovate");
    fireEvent.click(screen.getByRole("button", { name: "Riesporta CSV" }));
    expect(await screen.findByText("Errore export job")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Riesporta Excel" }));
    expect(await screen.findByText("xlsx rejected")).toBeInTheDocument();
  });
});
