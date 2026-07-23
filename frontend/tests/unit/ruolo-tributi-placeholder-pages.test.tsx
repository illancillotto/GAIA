import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import RuoloTributiImportPagamentiPage from "@/app/ruolo/tributi/import-pagamenti/page";
import RuoloTributiSollecitiPage from "@/app/ruolo/tributi/solleciti/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  importTributiPayments: vi.fn(),
  listTributiPaymentImportJobs: vi.fn(),
  listTributiPaymentImportUnmatched: vi.fn(),
}));

function buildPaymentImportJob(overrides: Record<string, unknown> = {}) {
  return {
    id: "job-1",
    filename: "pagamenti.csv",
    source: "capacitas_excel",
    status: "completed",
    started_at: "2026-07-22T08:00:00Z",
    finished_at: "2026-07-22T08:00:02Z",
    records_total: 2,
    records_imported: 1,
    records_matched: 1,
    records_unmatched: 1,
    records_errors: 0,
    error_detail: null,
    mapping_json: null,
    triggered_by: 1,
    created_at: "2026-07-22T08:00:00Z",
    ...overrides,
  };
}

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/ruolo-api", () => ({
  importTributiPayments: mocks.importTributiPayments,
  listTributiPaymentImportJobs: mocks.listTributiPaymentImportJobs,
  listTributiPaymentImportUnmatched: mocks.listTributiPaymentImportUnmatched,
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({
    children,
    title,
  }: {
    children: React.ReactNode;
    title: string;
  }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

describe("Ruolo tributi placeholder pages", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.importTributiPayments.mockReset();
    mocks.listTributiPaymentImportJobs.mockReset();
    mocks.listTributiPaymentImportUnmatched.mockReset();
    mocks.listTributiPaymentImportJobs.mockResolvedValue({
      items: [buildPaymentImportJob()],
      total: 1,
      page: 1,
      page_size: 12,
    });
    mocks.listTributiPaymentImportUnmatched.mockResolvedValue({
      job_id: "job-1",
      items: [{ row_number: 3, reason: "Avviso non trovato", raw: { Avviso: "NOPE" } }],
      total: 1,
    });
    mocks.importTributiPayments.mockResolvedValue(buildPaymentImportJob({
      id: "job-2",
      filename: "nuovi.csv",
      started_at: "2026-07-22T09:00:00Z",
      finished_at: "2026-07-22T09:00:02Z",
      records_total: 1,
      records_imported: 1,
      records_matched: 1,
      records_unmatched: 0,
      created_at: "2026-07-22T09:00:00Z",
    }));
  });

  test("renders and submits payment import workflow", async () => {
    render(<RuoloTributiImportPagamentiPage />);

    expect(screen.getByRole("heading", { name: "Import Pagamenti Tributi" })).toBeInTheDocument();
    expect((await screen.findAllByText("pagamenti.csv")).length).toBeGreaterThan(0);
    expect(await screen.findByText("Avviso non trovato")).toBeInTheDocument();
    expect(screen.getByText("Import pagamenti con matching controllato")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Torna ai tributi" })).toHaveAttribute("href", "/ruolo/tributi");

    const file = new File(["Avviso;Importo\nCNC-1;10,00"], "nuovi.csv", { type: "text/csv" });
    fireEvent.change(screen.getByLabelText("File pagamenti CapaciTas"), { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "Avvia import pagamenti" }));

    await waitFor(() => {
      expect(mocks.importTributiPayments).toHaveBeenCalledWith(
        "token",
        file,
        expect.objectContaining({ amount: "Importo pagato" }),
      );
    });
    expect((await screen.findAllByText("nuovi.csv")).length).toBeGreaterThan(0);
  });

  test("handles empty history, API errors, invalid mapping and alternate job states", async () => {
    mocks.getStoredAccessToken.mockReturnValueOnce(null);
    mocks.listTributiPaymentImportJobs.mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 12 });
    const noTokenRender = render(<RuoloTributiImportPagamentiPage />);
    expect(await screen.findByText("Nessun import pagamenti")).toBeInTheDocument();
    noTokenRender.unmount();

    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.listTributiPaymentImportJobs.mockReset();
    mocks.listTributiPaymentImportUnmatched.mockReset();
    mocks.listTributiPaymentImportJobs.mockRejectedValueOnce("boom");
    const loadErrorRender = render(<RuoloTributiImportPagamentiPage />);
    expect(await screen.findByText("Errore caricamento job import pagamenti")).toBeInTheDocument();
    loadErrorRender.unmount();

    mocks.listTributiPaymentImportJobs.mockResolvedValueOnce({
      items: [
        buildPaymentImportJob({
          id: "failed-job",
          filename: null,
          status: "failed",
          created_at: null,
          records_total: null,
          records_imported: null,
          records_unmatched: null,
          records_errors: null,
          error_detail: "Mapping importo pagamento mancante",
        }),
        buildPaymentImportJob({
          id: "running-job",
          filename: "running.csv",
          status: "running",
          records_errors: 2,
        }),
      ],
      total: 2,
      page: 1,
      page_size: 12,
    });
    mocks.listTributiPaymentImportUnmatched.mockResolvedValue({ job_id: "running-job", items: [], total: 0 });
    mocks.listTributiPaymentImportUnmatched.mockRejectedValueOnce(new Error("Report non disponibile"));
    mocks.importTributiPayments.mockRejectedValueOnce("boom");

    render(<RuoloTributiImportPagamentiPage />);
    expect(await screen.findByText("Fallito")).toBeInTheDocument();
    expect(screen.getByText("Mapping importo pagamento mancante")).toBeInTheDocument();
    expect(screen.getByText("Import pagamenti")).toBeInTheDocument();

    fireEvent.click(await screen.findByText("running.csv"));
    expect(await screen.findByText("In corso")).toBeInTheDocument();

    const file = new File(["Avviso;Importo\nCNC-1;10,00"], "errore.csv", { type: "text/csv" });
    fireEvent.change(screen.getByLabelText("File pagamenti CapaciTas"), { target: { files: [file] } });
    fireEvent.change(screen.getByDisplayValue(/"codice_cnc"/), { target: { value: "{" } });
    fireEvent.click(screen.getByRole("button", { name: "Avvia import pagamenti" }));
    expect(await screen.findByText("Mapping colonne non valido")).toBeInTheDocument();

    fireEvent.change(screen.getByDisplayValue("{"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Avvia import pagamenti" }));
    expect(await screen.findByText("Errore import pagamenti CapaciTas")).toBeInTheDocument();
    expect(mocks.importTributiPayments).toHaveBeenCalledWith("token", file, undefined);
  });

  test("covers defensive payment import UI branches", async () => {
    let resolveJobs: (value: { items: ReturnType<typeof buildPaymentImportJob>[]; total: number; page: number; page_size: number }) => void = () => {};
    const pendingJobs = new Promise<{ items: ReturnType<typeof buildPaymentImportJob>[]; total: number; page: number; page_size: number }>((resolve) => {
      resolveJobs = resolve;
    });
    mocks.listTributiPaymentImportJobs.mockReset();
    mocks.listTributiPaymentImportJobs.mockReturnValueOnce(pendingJobs);
    const pendingRender = render(<RuoloTributiImportPagamentiPage />);
    pendingRender.unmount();
    await act(async () => {
      resolveJobs({ items: [buildPaymentImportJob()], total: 1, page: 1, page_size: 12 });
      await pendingJobs;
    });

    let rejectJobs: (reason: Error) => void = () => {};
    const rejectedJobs = new Promise<{ items: ReturnType<typeof buildPaymentImportJob>[]; total: number; page: number; page_size: number }>((_resolve, reject) => {
      rejectJobs = reject;
    });
    mocks.listTributiPaymentImportJobs.mockReturnValueOnce(rejectedJobs);
    const rejectedRender = render(<RuoloTributiImportPagamentiPage />);
    rejectedRender.unmount();
    await act(async () => {
      rejectJobs(new Error("Caricamento cancellato"));
      await rejectedJobs.catch(() => undefined);
    });

    mocks.listTributiPaymentImportJobs.mockRejectedValueOnce(new Error("Errore dettagliato caricamento"));
    const errorRender = render(<RuoloTributiImportPagamentiPage />);
    expect(await screen.findByText("Errore dettagliato caricamento")).toBeInTheDocument();
    errorRender.unmount();

    mocks.listTributiPaymentImportJobs.mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 12 });
    const emptyRender = render(<RuoloTributiImportPagamentiPage />);
    expect(await screen.findByText("Nessun import pagamenti")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("File pagamenti CapaciTas"), { target: {} });
    fireEvent.submit(emptyRender.container.querySelector("form") as HTMLFormElement);
    expect(mocks.importTributiPayments).not.toHaveBeenCalledWith("token", expect.any(File), expect.anything());
    emptyRender.unmount();

    let resolveUnmatched: (value: { job_id: string; items: never[]; total: number }) => void = () => {};
    const pendingUnmatched = new Promise<{ job_id: string; items: never[]; total: number }>((resolve) => {
      resolveUnmatched = resolve;
    });
    mocks.listTributiPaymentImportJobs.mockResolvedValueOnce({
      items: [buildPaymentImportJob({ id: "cancel-unmatched" })],
      total: 1,
      page: 1,
      page_size: 12,
    });
    mocks.listTributiPaymentImportUnmatched.mockReturnValueOnce(pendingUnmatched);
    const unmatchedResolveRender = render(<RuoloTributiImportPagamentiPage />);
    await waitFor(() => expect(mocks.listTributiPaymentImportUnmatched).toHaveBeenCalledWith("token", "cancel-unmatched"));
    unmatchedResolveRender.unmount();
    await act(async () => {
      resolveUnmatched({ job_id: "cancel-unmatched", items: [], total: 0 });
      await pendingUnmatched;
    });

    let rejectUnmatched: (reason: Error) => void = () => {};
    const rejectedUnmatched = new Promise<{ job_id: string; items: never[]; total: number }>((_resolve, reject) => {
      rejectUnmatched = reject;
    });
    mocks.listTributiPaymentImportJobs.mockResolvedValueOnce({
      items: [buildPaymentImportJob({ id: "cancel-unmatched-error" })],
      total: 1,
      page: 1,
      page_size: 12,
    });
    mocks.listTributiPaymentImportUnmatched.mockReturnValueOnce(rejectedUnmatched);
    const unmatchedRejectRender = render(<RuoloTributiImportPagamentiPage />);
    await waitFor(() => expect(mocks.listTributiPaymentImportUnmatched).toHaveBeenCalledWith("token", "cancel-unmatched-error"));
    unmatchedRejectRender.unmount();
    await act(async () => {
      rejectUnmatched(new Error("Report cancellato"));
      await rejectedUnmatched.catch(() => undefined);
    });

    mocks.listTributiPaymentImportJobs.mockResolvedValueOnce({
      items: [buildPaymentImportJob({ status: "queued" })],
      total: 1,
      page: 1,
      page_size: 12,
    });
    mocks.listTributiPaymentImportUnmatched.mockResolvedValueOnce({ job_id: "job-1", items: [], total: 0 });
    render(<RuoloTributiImportPagamentiPage />);
    expect(await screen.findByText("queued")).toBeInTheDocument();
  });

  test("renders reminders placeholder", () => {
    render(<RuoloTributiSollecitiPage />);

    expect(screen.getByRole("heading", { name: "Solleciti Tributi" })).toBeInTheDocument();
    expect(screen.getByText("Generazione solleciti da implementare")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Torna ai tributi" })).toHaveAttribute("href", "/ruolo/tributi");
  });
});
