import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { AnagraficaBulkPanel } from "@/components/catasto/anagrafica/AnagraficaBulkPanel";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  catastoCreateElaborazioneMassivaDistrettoExportJob: vi.fn(),
  catastoDeleteElaborazioniMassiveJobs: vi.fn(),
  catastoDownloadElaborazioneMassivaDistrettoExportJob: vi.fn(),
  catastoDownloadElaborazioneMassivaJobExport: vi.fn(),
  catastoGetElaborazioneMassivaDistrettoExportJob: vi.fn(),
  catastoGetElaborazioneMassivaJob: vi.fn(),
  catastoListElaborazioneMassivaDistrettoExportJobs: vi.fn(),
  catastoListDistretti: vi.fn(),
  catastoListElaborazioniMassiveJobs: vi.fn(),
  catastoUploadElaborazioneMassivaJob: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api/catasto-distretto-export-jobs", () => ({
  catastoCreateElaborazioneMassivaDistrettoExportJob: mocks.catastoCreateElaborazioneMassivaDistrettoExportJob,
  catastoDownloadElaborazioneMassivaDistrettoExportJob: mocks.catastoDownloadElaborazioneMassivaDistrettoExportJob,
  catastoGetElaborazioneMassivaDistrettoExportJob: mocks.catastoGetElaborazioneMassivaDistrettoExportJob,
  catastoListElaborazioneMassivaDistrettoExportJobs: mocks.catastoListElaborazioneMassivaDistrettoExportJobs,
}));

vi.mock("@/lib/api/catasto", () => ({
  catastoDeleteElaborazioniMassiveJobs: mocks.catastoDeleteElaborazioniMassiveJobs,
  catastoDownloadElaborazioneMassivaJobExport: mocks.catastoDownloadElaborazioneMassivaJobExport,
  catastoGetElaborazioneMassivaJob: mocks.catastoGetElaborazioneMassivaJob,
  catastoListDistretti: mocks.catastoListDistretti,
  catastoListElaborazioniMassiveJobs: mocks.catastoListElaborazioniMassiveJobs,
  catastoUploadElaborazioneMassivaJob: mocks.catastoUploadElaborazioneMassivaJob,
}));

vi.mock("@/components/table/data-table", () => ({
  DataTable: () => <div data-testid="data-table" />,
}));

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

describe("AnagraficaBulkPanel distretto export spinner", () => {
  beforeEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.catastoListElaborazioniMassiveJobs.mockResolvedValue({ items: [] });
    mocks.catastoListElaborazioneMassivaDistrettoExportJobs.mockResolvedValue({ items: [] });
    mocks.catastoListDistretti.mockResolvedValue([
      {
        id: "distretto-1",
        num_distretto: "01",
        nome_distretto: "Sinis Nord Est",
        decreto_istitutivo: null,
        data_decreto: null,
        attivo: true,
        note: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    ]);
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:export");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  test("shows a spinner while district CSV export is being prepared", async () => {
    const createRequest = deferred<{
      id: string;
      created_at: string;
      started_at: string | null;
      completed_at: string | null;
      num_distretto: string;
      nome_distretto: string | null;
      format: "csv";
      status: "completed";
      total_rows: number;
      processed_rows: number;
      current_label: string | null;
      error_message: string | null;
      output_filename: string | null;
      download_url: string | null;
    }>();
    mocks.catastoCreateElaborazioneMassivaDistrettoExportJob.mockReturnValue(createRequest.promise);
    mocks.catastoDownloadElaborazioneMassivaDistrettoExportJob.mockResolvedValue(new Blob(["csv"], { type: "text/csv" }));

    render(<AnagraficaBulkPanel />);

    fireEvent.change(await screen.findByLabelText("Distretto"), { target: { value: "01" } });
    fireEvent.click(screen.getByRole("button", { name: /Export CSV distretto/i }));

    expect(await screen.findByRole("status")).toHaveTextContent("Export CSV in corso");
    expect(screen.getByRole("button", { name: /Export CSV in corso/i })).toBeDisabled();
    expect(screen.getByText(/Sto preparando il file sul backend/i)).toBeInTheDocument();
    expect(mocks.catastoCreateElaborazioneMassivaDistrettoExportJob).toHaveBeenCalledWith("token", "01", "csv");

    createRequest.resolve({
      id: "export-1",
      created_at: "2026-07-16T10:00:00Z",
      started_at: "2026-07-16T10:00:01Z",
      completed_at: "2026-07-16T10:00:02Z",
      num_distretto: "01",
      nome_distretto: "Sinis Nord Est",
      format: "csv",
      status: "completed",
      total_rows: 12,
      processed_rows: 12,
      current_label: "Export completato.",
      error_message: null,
      output_filename: "distretto-01.csv",
      download_url: "/download",
    });

    await waitFor(() => {
      expect(screen.queryByRole("status")).not.toBeInTheDocument();
    });
    expect(mocks.catastoDownloadElaborazioneMassivaDistrettoExportJob).toHaveBeenCalledWith("token", "export-1");
  });

  test("keeps the district dropdown usable when export history fails to load", async () => {
    mocks.catastoListElaborazioneMassivaDistrettoExportJobs.mockRejectedValue(new Error("Not found"));

    render(<AnagraficaBulkPanel />);

    const select = await screen.findByLabelText("Distretto");
    expect(select).not.toBeDisabled();
    expect(screen.getByRole("option", { name: /01 · Sinis Nord Est/i })).toBeInTheDocument();

    fireEvent.change(select, { target: { value: "01" } });
    expect(select).toHaveValue("01");
  });

  test("resumes polling an active district export after refresh", async () => {
    const pendingJob = {
      id: "export-2",
      created_at: "2026-07-16T10:00:00Z",
      started_at: "2026-07-16T10:00:01Z",
      completed_at: null,
      num_distretto: "01",
      nome_distretto: "Sinis Nord Est",
      format: "xlsx",
      status: "processing",
      total_rows: 0,
      processed_rows: 0,
      current_label: "Generazione file export...",
      error_message: null,
      output_filename: null,
      download_url: null,
    };
    mocks.catastoListElaborazioneMassivaDistrettoExportJobs.mockResolvedValue({ items: [pendingJob] });
    mocks.catastoGetElaborazioneMassivaDistrettoExportJob.mockResolvedValue({
      ...pendingJob,
      completed_at: "2026-07-16T10:00:02Z",
      status: "completed",
      total_rows: 18,
      processed_rows: 18,
      current_label: "Export completato.",
      output_filename: "distretto-01.xlsx",
      download_url: "/download",
    });

    render(<AnagraficaBulkPanel />);

    expect(await screen.findByRole("status")).toHaveTextContent("Export distretto in corso");
    expect(screen.getByText(/Quando sarà pronto resterà disponibile/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(mocks.catastoGetElaborazioneMassivaDistrettoExportJob).toHaveBeenCalledWith("token", "export-2");
    }, { timeout: 2500 });
    expect(await screen.findByText(/18 righe · pronto per il download/i)).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(mocks.catastoDownloadElaborazioneMassivaDistrettoExportJob).not.toHaveBeenCalled();
  });
});
