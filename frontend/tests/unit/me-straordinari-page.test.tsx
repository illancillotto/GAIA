import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import MeStraordinariPage from "@/app/me/straordinari/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  previewMeStraordinariRequest: vi.fn(),
  downloadMeStraordinariRequest: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  previewMeStraordinariRequest: mocks.previewMeStraordinariRequest,
  downloadMeStraordinariRequest: mocks.downloadMeStraordinariRequest,
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <main>
      <h1>{title}</h1>
      {children}
    </main>
  ),
}));

describe("MeStraordinariPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.previewMeStraordinariRequest.mockResolvedValue({
      collaborator: { id: "collab-1", name: "AMADU SALVATORE", employee_code: "1854" },
      period_start: "2026-07-01",
      period_end: "2026-07-31",
      items: [
        {
          record_id: "record-1",
          work_date: "2026-07-10",
          motivation: "Intervento impianto",
          start_time: "14:30",
          end_time: "16:00",
          duration_minutes: 90,
          duration_label: "01:30",
        },
      ],
    });
    mocks.downloadMeStraordinariRequest.mockResolvedValue(new Blob(["xlsx"], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }));
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:test");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
  });

  test("loads preview, edits motivation and downloads the Excel module", async () => {
    render(<MeStraordinariPage />);

    await waitFor(() => expect(mocks.previewMeStraordinariRequest).toHaveBeenCalledWith("token"));
    expect(screen.getByText("Richiesta straordinari")).toBeInTheDocument();
    expect(screen.getByText("AMADU SALVATORE · matricola 1854")).toBeInTheDocument();
    expect(screen.getAllByText("01:30")).toHaveLength(2);

    fireEvent.change(screen.getByDisplayValue("Intervento impianto"), { target: { value: "Servizio urgente" } });
    fireEvent.click(screen.getByRole("button", { name: "Scarica Excel" }));

    await waitFor(() =>
      expect(mocks.downloadMeStraordinariRequest).toHaveBeenCalledWith("token", "xlsx", {
        items: [{ record_id: "record-1", motivation: "Servizio urgente" }],
      }),
    );
    expect(URL.createObjectURL).toHaveBeenCalled();
    expect(screen.getByText(/Excel generato/)).toBeInTheDocument();
  });

  test("shows an empty state when there are no overtime candidates", async () => {
    mocks.previewMeStraordinariRequest.mockResolvedValueOnce({
      collaborator: { id: "collab-1", name: "AMADU SALVATORE", employee_code: "1854" },
      period_start: "2026-07-01",
      period_end: "2026-07-31",
      items: [],
    });

    render(<MeStraordinariPage />);

    expect(await screen.findByText("Nessuno straordinario nel mese precedente")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Scarica Excel" })).toBeDisabled();
  });

  test("downloads the PDF module and shows the fallback time label for missing punches", async () => {
    mocks.previewMeStraordinariRequest.mockResolvedValueOnce({
      collaborator: { id: "collab-1", name: "AMADU SALVATORE", employee_code: "1854" },
      period_start: "2026-07-01",
      period_end: "2026-07-31",
      items: [
        {
          record_id: "record-1",
          work_date: "2026-07-10",
          motivation: "",
          start_time: null,
          end_time: null,
          duration_minutes: 60,
          duration_label: "01:00",
        },
      ],
    });
    mocks.downloadMeStraordinariRequest.mockResolvedValueOnce(new Blob(["pdf"], { type: "application/pdf" }));

    render(<MeStraordinariPage />);

    expect(await screen.findByText("Orario da verificare")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Scarica PDF" }));

    await waitFor(() =>
      expect(mocks.downloadMeStraordinariRequest).toHaveBeenCalledWith("token", "pdf", {
        items: [{ record_id: "record-1", motivation: "" }],
      }),
    );
    expect(screen.getByText(/PDF generato/)).toBeInTheDocument();
  });

  test("updates totals and disables downloads when the operator excludes every row", async () => {
    render(<MeStraordinariPage />);

    const checkbox = await screen.findByRole("checkbox", { name: "Includi ven 10/07/2026" });
    fireEvent.click(checkbox);
    fireEvent.click(screen.getByRole("button", { name: "Solo pausa detratta" }));

    expect(screen.getByText("00:00")).toBeInTheDocument();
    expect(screen.getByText("Nessuna riga per questo filtro")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Scarica Excel" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Scarica PDF" })).toBeDisabled();
  });

  test("shows authentication and backend errors", async () => {
    mocks.getStoredAccessToken.mockReturnValueOnce(null);

    const { unmount } = render(<MeStraordinariPage />);
    expect(await screen.findByText("Sessione non disponibile. Effettua il login.")).toBeInTheDocument();
    expect(mocks.previewMeStraordinariRequest).not.toHaveBeenCalled();

    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.previewMeStraordinariRequest.mockRejectedValueOnce(new Error("Preview non disponibile"));
    unmount();
    const secondRender = render(<MeStraordinariPage />);

    expect(await screen.findByText("Preview non disponibile")).toBeInTheDocument();

    mocks.previewMeStraordinariRequest.mockRejectedValueOnce("errore non standard");
    secondRender.unmount();
    render(<MeStraordinariPage />);

    expect(await screen.findByText("Errore caricamento richiesta straordinari")).toBeInTheDocument();
  });

  test("shows download errors", async () => {
    mocks.downloadMeStraordinariRequest.mockRejectedValueOnce(new Error("LibreOffice non trovato"));

    render(<MeStraordinariPage />);

    await screen.findByDisplayValue("Intervento impianto");
    fireEvent.click(screen.getByRole("button", { name: "Scarica PDF" }));

    expect(await screen.findByText("LibreOffice non trovato")).toBeInTheDocument();
  });

  test("shows fallback text for non-standard download errors", async () => {
    mocks.downloadMeStraordinariRequest.mockRejectedValueOnce("errore non standard");

    render(<MeStraordinariPage />);

    await screen.findByDisplayValue("Intervento impianto");
    fireEvent.click(screen.getByRole("button", { name: "Scarica Excel" }));

    expect(await screen.findByText("Errore generazione modulo straordinari")).toBeInTheDocument();
  });

  test("stops download when the session disappears after preview load", async () => {
    render(<MeStraordinariPage />);

    await screen.findByDisplayValue("Intervento impianto");
    mocks.getStoredAccessToken.mockReturnValueOnce(null);
    fireEvent.click(screen.getByRole("button", { name: "Scarica Excel" }));

    expect(await screen.findByText("Sessione non disponibile. Effettua il login.")).toBeInTheDocument();
    expect(mocks.downloadMeStraordinariRequest).not.toHaveBeenCalled();
  });

  test("updates only the edited row when multiple candidates are available", async () => {
    mocks.previewMeStraordinariRequest.mockResolvedValueOnce({
      collaborator: { id: "collab-1", name: "AMADU SALVATORE", employee_code: "1854" },
      period_start: "2026-07-01",
      period_end: "2026-07-31",
      items: [
        {
          record_id: "record-1",
          work_date: "2026-07-10",
          motivation: "Prima motivazione",
          start_time: "14:30",
          end_time: "16:00",
          duration_minutes: 90,
          duration_label: "01:30",
        },
        {
          record_id: "record-2",
          work_date: "2026-07-11",
          motivation: "Seconda motivazione",
          start_time: "15:00",
          end_time: "15:30",
          duration_minutes: 30,
          duration_label: "00:30",
        },
      ],
    });

    render(<MeStraordinariPage />);

    fireEvent.click(await screen.findByRole("checkbox", { name: "Includi ven 10/07/2026" }));
    fireEvent.change(screen.getByDisplayValue("Seconda motivazione"), { target: { value: "Seconda aggiornata" } });
    fireEvent.click(screen.getByRole("button", { name: "Scarica Excel" }));

    await waitFor(() =>
      expect(mocks.downloadMeStraordinariRequest).toHaveBeenCalledWith("token", "xlsx", {
        items: [{ record_id: "record-2", motivation: "Seconda aggiornata" }],
      }),
    );
  });

  test("filters rows with missing lunch break adjustments", async () => {
    mocks.previewMeStraordinariRequest.mockResolvedValueOnce({
      collaborator: { id: "collab-1", name: "AMADU SALVATORE", employee_code: "1854" },
      period_start: "2026-07-01",
      period_end: "2026-07-31",
      items: [
        {
          record_id: "record-1",
          work_date: "2026-07-10",
          motivation: "Giornata continua",
          start_time: "15:00",
          end_time: "16:00",
          duration_minutes: 60,
          duration_label: "01:00",
          original_duration_minutes: 90,
          pause_deduction_minutes: 30,
          duration_adjustment_reason: "Detratta pausa pranzo non rilevata nelle timbrature (00:30)",
        },
        {
          record_id: "record-2",
          work_date: "2026-07-11",
          motivation: "Intervento programmato",
          start_time: "14:30",
          end_time: "15:30",
          duration_minutes: 60,
          duration_label: "01:00",
          original_duration_minutes: 60,
          pause_deduction_minutes: 0,
          lunch_break_minutes: null,
          duration_adjustment_reason: null,
        },
      ],
    });

    render(<MeStraordinariPage />);

    expect(await screen.findByText(/Pausa detratta: 1/)).toBeInTheDocument();
    expect(screen.getByText(/Allineate alla fascia post-pausa: 0/)).toBeInTheDocument();
    expect(screen.getByText("Da 01:30, pausa -00:30")).toBeInTheDocument();
    expect(screen.getByText("Detratta pausa pranzo non rilevata nelle timbrature (00:30)")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Solo pausa detratta" }));
    expect(screen.getByDisplayValue("Giornata continua")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("Intervento programmato")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Senza rettifica" }));
    expect(screen.queryByDisplayValue("Giornata continua")).not.toBeInTheDocument();
    expect(screen.getByDisplayValue("Intervento programmato")).toBeInTheDocument();
  });

  test("shows post-lunch band alignment when lunch break is valid", async () => {
    mocks.previewMeStraordinariRequest.mockResolvedValueOnce({
      collaborator: { id: "collab-1", name: "AMADU SALVATORE", employee_code: "1854" },
      period_start: "2026-07-01",
      period_end: "2026-07-31",
      items: [
        {
          record_id: "record-1",
          work_date: "2026-07-25",
          motivation: "Rientro serale",
          start_time: "14:20",
          end_time: "19:30",
          duration_minutes: 310,
          duration_label: "05:10",
          original_duration_minutes: 320,
          pause_deduction_minutes: 0,
          lunch_break_minutes: 30,
          duration_adjustment_reason: "Durata ricondotta alla fascia dopo pausa pranzo (05:10)",
        },
      ],
    });

    render(<MeStraordinariPage />);

    expect(await screen.findByText("Da 05:20 a 05:10")).toBeInTheDocument();
    expect(screen.getByText("Pausa rilevata: 00:30")).toBeInTheDocument();
    expect(screen.getByText("Durata ricondotta alla fascia dopo pausa pranzo (05:10)")).toBeInTheDocument();
    expect(screen.getAllByText("05:10")).toHaveLength(2);

    fireEvent.click(screen.getByRole("button", { name: "Senza rettifica" }));
    expect(screen.getByText("Nessuna riga per questo filtro")).toBeInTheDocument();
  });
});
