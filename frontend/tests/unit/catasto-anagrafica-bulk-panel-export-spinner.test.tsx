import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

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
    mocks.catastoListComuniExport.mockResolvedValue([
      { codice: "A357", nome: "Arborea" },
      { codice: "G113", nome: "Oristano" },
    ]);
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
    mocks.catastoCreateElaborazioneMassivaScopeExportJob.mockReturnValue(createRequest.promise);
    mocks.catastoDownloadElaborazioneMassivaDistrettoExportJob.mockResolvedValue(new Blob(["csv"], { type: "text/csv" }));

    render(<AnagraficaBulkPanel />);

    fireEvent.click(await screen.findByRole("checkbox", { name: /01 · Sinis Nord Est/i }));
    fireEvent.click(screen.getByRole("button", { name: /Export CSV distretti/i }));

    expect(await screen.findByRole("status")).toHaveTextContent("Export CSV in corso");
    expect(screen.getByRole("button", { name: /Export CSV in corso/i })).toBeDisabled();
    expect(screen.getByText(/Sto preparando il file sul backend/i)).toBeInTheDocument();
    expect(mocks.catastoCreateElaborazioneMassivaScopeExportJob).toHaveBeenCalledWith("token", "distretti", ["01"], "csv");

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

  test("keeps the district checklist usable when export history fails to load", async () => {
    mocks.catastoListElaborazioneMassivaDistrettoExportJobs.mockRejectedValue(new Error("Not found"));

    render(<AnagraficaBulkPanel />);

    const checkbox = await screen.findByRole("checkbox", { name: /01 · Sinis Nord Est/i });
    expect(checkbox).not.toBeDisabled();

    fireEvent.click(checkbox);
    expect(checkbox).toBeChecked();
  });

  test("exports several comuni in a single job", async () => {
    mocks.catastoCreateElaborazioneMassivaScopeExportJob.mockResolvedValue({
      id: "export-3",
      created_at: "2026-07-16T10:00:00Z",
      started_at: null,
      completed_at: "2026-07-16T10:00:02Z",
      num_distretto: "A357, G113",
      nome_distretto: "Arborea, Oristano",
      scope_kind: "comuni",
      scope_values: ["A357", "G113"],
      format: "xlsx",
      status: "completed",
      total_rows: 5,
      processed_rows: 5,
      current_label: "Export completato.",
      error_message: null,
      output_filename: "comuni.xlsx",
      download_url: "/download",
    });
    mocks.catastoDownloadElaborazioneMassivaDistrettoExportJob.mockResolvedValue(new Blob(["x"]));

    render(<AnagraficaBulkPanel />);

    fireEvent.click(await screen.findByRole("checkbox", { name: /Arborea/i }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Oristano/i }));
    fireEvent.click(screen.getByRole("button", { name: /Export Excel comuni/i }));

    await waitFor(() => {
      expect(mocks.catastoCreateElaborazioneMassivaScopeExportJob).toHaveBeenCalledWith(
        "token",
        "comuni",
        ["A357", "G113"],
        "xlsx",
      );
    });
    await waitFor(() => {
      expect(mocks.catastoDownloadElaborazioneMassivaDistrettoExportJob).toHaveBeenCalledWith("token", "export-3");
    });
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

function exportJob(overrides: Record<string, unknown> = {}) {
  return {
    id: "export-x",
    created_at: "2026-07-16T10:00:00Z",
    started_at: "2026-07-16T10:00:01Z",
    completed_at: "2026-07-16T10:00:02Z",
    num_distretto: "01",
    nome_distretto: null,
    scope_kind: "distretti",
    scope_values: ["01"],
    format: "csv",
    status: "completed",
    total_rows: 3,
    processed_rows: 3,
    current_label: "Export completato.",
    error_message: null,
    output_filename: "file.csv",
    download_url: "/download",
    ...overrides,
  };
}

describe("AnagraficaBulkPanel multi-scope export", () => {
  beforeEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.catastoListElaborazioniMassiveJobs.mockResolvedValue({ items: [] });
    mocks.catastoListElaborazioneMassivaDistrettoExportJobs.mockResolvedValue({ items: [] });
    mocks.catastoListComuniExport.mockResolvedValue([
      { codice: "A357", nome: "Arborea" },
      { codice: "G113", nome: "Oristano" },
    ]);
    mocks.catastoListDistretti.mockResolvedValue([
      { id: "d1", num_distretto: "01", nome_distretto: "Sinis Nord Est" },
      { id: "d2", num_distretto: "02", nome_distretto: null },
    ]);
    mocks.catastoDownloadComuneExport.mockResolvedValue(new Blob(["x"]));
    mocks.catastoDownloadElaborazioneMassivaDistrettoExportJob.mockResolvedValue(new Blob(["x"]));
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:export");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("polls a pending multi-district job until completion and downloads it", async () => {
    mocks.catastoCreateElaborazioneMassivaScopeExportJob.mockResolvedValue(
      exportJob({ id: "export-p", status: "pending", num_distretto: "01, 02", scope_values: ["01", "02"] }),
    );
    mocks.catastoGetElaborazioneMassivaDistrettoExportJob.mockResolvedValue(
      exportJob({ id: "export-p", num_distretto: "01, 02", scope_values: ["01", "02"], output_filename: null, format: "xlsx" }),
    );

    render(<AnagraficaBulkPanel />);

    fireEvent.click(await screen.findByRole("checkbox", { name: /01 · Sinis Nord Est/i }));
    fireEvent.click(screen.getByRole("checkbox", { name: /^02$/ }));
    fireEvent.click(screen.getByRole("button", { name: /Export Excel distretti/i }));

    await waitFor(
      () => expect(mocks.catastoDownloadElaborazioneMassivaDistrettoExportJob).toHaveBeenCalledWith("token", "export-p"),
      { timeout: 3500 },
    );
    expect(mocks.catastoCreateElaborazioneMassivaScopeExportJob).toHaveBeenCalledWith(
      "token",
      "distretti",
      ["01", "02"],
      "xlsx",
    );
    expect(await screen.findByText("2 distretti (01, 02) · XLSX")).toBeInTheDocument();
  });

  test("shows the backend error when an export job fails", async () => {
    mocks.catastoCreateElaborazioneMassivaScopeExportJob.mockResolvedValue(
      exportJob({ status: "failed", error_message: "Nessuna particella", scope_kind: "comuni", scope_values: ["A357", "G113"] }),
    );

    render(<AnagraficaBulkPanel />);

    fireEvent.click(await screen.findByRole("checkbox", { name: /Arborea/i }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Oristano/i }));
    fireEvent.click(screen.getByRole("button", { name: /Export CSV comuni/i }));

    expect(await screen.findAllByText("Nessuna particella")).toHaveLength(2);
    expect(mocks.catastoDownloadElaborazioneMassivaDistrettoExportJob).not.toHaveBeenCalled();
  });

  test("uses fallback messages when the job has no error message or the request is not an Error", async () => {
    mocks.catastoCreateElaborazioneMassivaScopeExportJob
      .mockResolvedValueOnce(exportJob({ status: "failed", error_message: null }))
      .mockRejectedValueOnce("boom");

    render(<AnagraficaBulkPanel />);

    fireEvent.click(await screen.findByRole("checkbox", { name: /01 · Sinis Nord Est/i }));
    fireEvent.click(screen.getByRole("button", { name: /Export CSV distretti/i }));
    expect(await screen.findAllByText("Export fallito")).not.toHaveLength(0);

    fireEvent.click(await screen.findByRole("button", { name: /Export CSV distretti/i }));
    expect(await screen.findByText("Errore export")).toBeInTheDocument();
  });

  test("single comune opens the source dialog and exports GAIA or live data", async () => {
    render(<AnagraficaBulkPanel />);

    fireEvent.click(await screen.findByRole("checkbox", { name: /Arborea/i }));
    fireEvent.click(screen.getByRole("button", { name: /Export CSV comuni/i }));
    fireEvent.click(await screen.findByRole("button", { name: /Esporta con dato GAIA/i }));

    await waitFor(() =>
      expect(mocks.catastoDownloadComuneExport).toHaveBeenCalledWith("token", "A357", "csv", "gaia"),
    );
    expect(mocks.catastoCreateElaborazioneMassivaScopeExportJob).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: /Export Excel comuni/i }));
    fireEvent.click(await screen.findByRole("button", { name: /Esporta live/i }));
    await waitFor(() =>
      expect(mocks.catastoDownloadComuneExport).toHaveBeenLastCalledWith("token", "A357", "xlsx", "live"),
    );

    fireEvent.click(screen.getByRole("button", { name: /Export CSV comuni/i }));
    fireEvent.click(await screen.findByRole("button", { name: "Annulla" }));
    expect(screen.queryByText("Scegli la fonte dei dati")).not.toBeInTheDocument();
  });

  test("shows an error when the single comune export fails", async () => {
    mocks.catastoDownloadComuneExport.mockRejectedValueOnce(new Error("Comune KO")).mockRejectedValueOnce("x");

    render(<AnagraficaBulkPanel />);

    fireEvent.click(await screen.findByRole("checkbox", { name: /Arborea/i }));
    fireEvent.click(screen.getByRole("button", { name: /Export CSV comuni/i }));
    fireEvent.click(await screen.findByRole("button", { name: /Esporta con dato GAIA/i }));
    expect(await screen.findByText("Comune KO")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Esporta con dato GAIA/i }));
    expect(await screen.findByText("Errore export comune")).toBeInTheDocument();
  });

  test("describes every kind of export job in the history and allows re-download", async () => {
    mocks.catastoListElaborazioneMassivaDistrettoExportJobs.mockResolvedValue({
      items: [
        exportJob({ id: "j1", scope_kind: "comuni", scope_values: ["A357", "G113"], num_distretto: "A357, G113" }),
        exportJob({ id: "j2", scope_kind: "comuni", scope_values: ["A357"], nome_distretto: "Arborea", num_distretto: "A357", output_filename: null }),
        exportJob({ id: "j3", scope_kind: "comuni", scope_values: null, nome_distretto: null, num_distretto: "A357" }),
        exportJob({ id: "j4", scope_kind: undefined, scope_values: undefined, num_distretto: "01", nome_distretto: "Sinis" }),
        exportJob({ id: "j5", status: "failed", error_message: null, scope_values: ["01"] }),
        exportJob({ id: "j6", status: "pending", current_label: null, completed_at: null }),
        exportJob({ id: "j7", scope_kind: undefined, output_filename: null }),
      ],
    });

    render(<AnagraficaBulkPanel />);

    expect(await screen.findByText("2 comuni · CSV")).toBeInTheDocument();
    expect(screen.getByText("Comune Arborea · CSV")).toBeInTheDocument();
    expect(screen.getByText("Comune A357 · CSV")).toBeInTheDocument();
    expect(screen.getByText("Distretto 01 · Sinis · CSV")).toBeInTheDocument();
    expect(screen.getAllByText("Distretto 01 · CSV")).toHaveLength(3);

    const downloads = screen.getAllByRole("button", { name: "Scarica" });
    fireEvent.click(downloads[0]);
    await waitFor(() =>
      expect(mocks.catastoDownloadElaborazioneMassivaDistrettoExportJob).toHaveBeenCalledWith("token", "j1"),
    );
    fireEvent.click(downloads[1]);
    await waitFor(() =>
      expect(mocks.catastoDownloadElaborazioneMassivaDistrettoExportJob).toHaveBeenCalledWith("token", "j2"),
    );

    fireEvent.click(downloads[4]);
    await waitFor(() =>
      expect(mocks.catastoDownloadElaborazioneMassivaDistrettoExportJob).toHaveBeenCalledWith("token", "j7"),
    );

    mocks.catastoDownloadElaborazioneMassivaDistrettoExportJob.mockRejectedValueOnce(new Error("Download KO"));
    fireEvent.click(downloads[2]);
    expect(await screen.findByText("Download KO")).toBeInTheDocument();

    mocks.catastoDownloadElaborazioneMassivaDistrettoExportJob.mockRejectedValueOnce("x");
    fireEvent.click(screen.getAllByRole("button", { name: "Scarica" })[0]);
    expect(await screen.findByText("Errore download export")).toBeInTheDocument();
    expect(screen.getByText("Export in coda")).toBeInTheDocument();

    mocks.catastoDownloadElaborazioneMassivaDistrettoExportJob.mockClear();
    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(screen.getAllByRole("button", { name: "Scarica" })[0]);
    expect(mocks.catastoDownloadElaborazioneMassivaDistrettoExportJob).not.toHaveBeenCalled();
  });

  test("does nothing when the session token is missing at export time", async () => {
    render(<AnagraficaBulkPanel />);

    fireEvent.click(await screen.findByRole("checkbox", { name: /01 · Sinis Nord Est/i }));
    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: /Export CSV distretti/i }));

    expect(mocks.catastoCreateElaborazioneMassivaScopeExportJob).not.toHaveBeenCalled();
  });

  test("resumes a running comuni job and labels it accordingly", async () => {
    mocks.catastoListElaborazioneMassivaDistrettoExportJobs.mockResolvedValue({
      items: [exportJob({ id: "run", status: "processing", scope_kind: "comuni", scope_values: ["A357", "G113"], completed_at: null })],
    });
    mocks.catastoGetElaborazioneMassivaDistrettoExportJob.mockImplementation(() => new Promise(() => undefined));

    render(<AnagraficaBulkPanel />);

    expect(await screen.findByRole("status")).toHaveTextContent("Export comuni in corso");
  });
});
