import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { AnagraficaBulkPanel } from "@/components/catasto/anagrafica/AnagraficaBulkPanel";

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
  DataTable: () => <div data-testid="bulk-results" />,
}));

function bulkRow(esito: string, index: number) {
  return {
    row_index: index,
    comune_input: null,
    sezione_input: null,
    foglio_input: null,
    particella_input: null,
    sub_input: null,
    codice_fiscale_input: "RSSMRA80A01H501U",
    partita_iva_input: null,
    esito,
    message: null,
    particella_id: null,
    match: null,
    matches: null,
    matches_count: 1,
  };
}

function bulkJob(esiti: string[]) {
  return {
    id: "bulk-r129",
    created_at: "2026-07-16T10:00:00Z",
    started_at: "2026-07-16T10:00:01Z",
    completed_at: "2026-07-16T10:00:02Z",
    source_filename: "input.csv",
    kind: "CF_PIVA_PARTICELLE",
    status: "completed",
    skipped_rows: 0,
    total_rows: esiti.length,
    processed_rows: esiti.length,
    current_label: null,
    error_message: null,
    // Deliberately inconsistent with the rows: the "Riepilogo" counters must be
    // derived client-side from the results, never copied from the job summary.
    summary: { total: 99, found: 99, notFound: 99, multiple: 99, invalid: 99, error: 99 },
    results: esiti.map((esito, index) => bulkRow(esito, index + 1)),
  };
}

function csvFile(contents: string): File {
  const file = new File([contents], "input.csv", { type: "text/csv" });
  Object.defineProperty(file, "text", { value: async () => contents });
  return file;
}

async function runJobAndReadSummary(esiti: string[]): Promise<string[]> {
  mocks.catastoUploadElaborazioneMassivaJob.mockResolvedValue(bulkJob(esiti));
  render(<AnagraficaBulkPanel />);
  fireEvent.change(document.getElementById("catasto-bulk-file") as HTMLInputElement, {
    target: { files: [csvFile("codice_fiscale\nRSSMRA80A01H501U")] },
  });
  await screen.findByText(/pronto per upload backend/);
  fireEvent.click(screen.getByRole("button", { name: /Elabora righe file/i }));
  await screen.findByTestId("bulk-results");
  return readSummaryChips();
}

function readSummaryChips(): string[] {
  const card = screen.getByText("Riepilogo").closest("article") as HTMLElement;
  const chips = within(card).getAllByText(/^(Totale|FOUND|NOT_FOUND|MULTIPLE|INVALID|ERROR): /);
  return chips.map((chip) => chip.textContent ?? "");
}

describe("AnagraficaBulkPanel summary counters (R129 characterization)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.catastoListElaborazioniMassiveJobs.mockResolvedValue({ items: [] });
    mocks.catastoListElaborazioneMassivaDistrettoExportJobs.mockResolvedValue({ items: [] });
    mocks.catastoListDistretti.mockResolvedValue([]);
    mocks.catastoListComuniExport.mockResolvedValue([]);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("shows zero counters in fixed order before any elaboration", () => {
    render(<AnagraficaBulkPanel />);
    expect(readSummaryChips()).toEqual([
      "Totale: 0",
      "FOUND: 0",
      "NOT_FOUND: 0",
      "MULTIPLE: 0",
      "INVALID: 0",
      "ERROR: 0",
    ]);
  });

  test("counts repeated outcomes per kind and keeps the total equal to all rows", async () => {
    const chips = await runJobAndReadSummary([
      "FOUND", "NOT_FOUND", "FOUND", "ERROR", "MULTIPLE_MATCHES",
      "FOUND", "INVALID_ROW", "NOT_FOUND", "ERROR", "ERROR",
    ]);
    expect(chips).toEqual([
      "Totale: 10",
      "FOUND: 3",
      "NOT_FOUND: 2",
      "MULTIPLE: 1",
      "INVALID: 1",
      "ERROR: 3",
    ]);
  });

  test("ignores unknown, lowercase and prototype-like outcomes but still counts them in the total", async () => {
    const chips = await runJobAndReadSummary([
      "OTHER", "found", "toString", "constructor", "__proto__", "hasOwnProperty", "", "MULTIPLE_MATCHES",
    ]);
    expect(chips).toEqual([
      "Totale: 8",
      "FOUND: 0",
      "NOT_FOUND: 0",
      "MULTIPLE: 1",
      "INVALID: 0",
      "ERROR: 0",
    ]);
  });
});
