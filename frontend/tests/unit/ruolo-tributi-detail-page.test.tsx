import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import RuoloTributiDetailPage, { RuoloTributiDetailFallback } from "@/app/ruolo/tributi/[avvisoId]/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getTributiAvviso: vi.fn(),
  createTributiPayment: vi.fn(),
  updateTributiAvvisoStatus: vi.fn(),
  addTributiNote: vi.fn(),
  listTributiReminders: vi.fn(),
  createTributiReminder: vi.fn(),
  downloadTributiReminderDocument: vi.fn(),
  createObjectURL: vi.fn(),
  revokeObjectURL: vi.fn(),
  anchorClick: vi.fn(),
  avvisoId: "avviso-1",
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/ruolo-api", () => ({
  getTributiAvviso: mocks.getTributiAvviso,
  createTributiPayment: mocks.createTributiPayment,
  updateTributiAvvisoStatus: mocks.updateTributiAvvisoStatus,
  addTributiNote: mocks.addTributiNote,
  listTributiReminders: mocks.listTributiReminders,
  createTributiReminder: mocks.createTributiReminder,
  downloadTributiReminderDocument: mocks.downloadTributiReminderDocument,
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({
    children,
    title,
    topbarActions,
  }: {
    children: React.ReactNode;
    title: string;
    topbarActions?: React.ReactNode;
  }) => (
    <div>
      <h1>{title}</h1>
      {topbarActions}
      {children}
    </div>
  ),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ avvisoId: mocks.avvisoId }),
}));

const detail = {
  id: "avviso-1",
  codice_cnc: "CNC-001",
  anno_tributario: 2024,
  subject_id: null,
  codice_fiscale_raw: "RSSMRA80A01H501Z",
  nominativo_raw: "ROSSI MARIO",
  codice_utenza: "UT-001",
  importo_totale_euro: 100,
  paid_amount: 40,
  saldo_amount: 60,
  payment_status: "partial",
  workflow_status: "moroso",
  last_payment_at: "2026-07-17T00:00:00Z",
  capacitas_url: "https://incass3.servizicapacitas.com/pages/dettaglioAvviso.aspx?avviso=1",
  capacitas_avviso_code: "020210002922120",
  display_name: "ROSSI MARIO",
  is_linked: false,
  notes_count: 1,
  domicilio_raw: "VIA TEST 1",
  residenza_raw: "ORISTANO",
  importo_totale_0648: 80,
  importo_totale_0985: 20,
  importo_totale_0668: 0,
  payments: [
    {
      id: "pay-1",
      avviso_id: "avviso-1",
      import_job_id: null,
      codice_cnc_raw: "CNC-001",
      codice_utenza_raw: "UT-001",
      anno_tributario: 2024,
      paid_at: "2026-07-17T00:00:00Z",
      amount: 40,
      payment_reference: "PAY-001",
      payment_method: "bonifico",
      source: "manual",
      status: "valid",
      raw_payload_json: null,
      created_by: 1,
      created_at: "2026-07-17T00:00:00Z",
      updated_at: "2026-07-17T00:00:00Z",
    },
    {
      id: "pay-2",
      avviso_id: "avviso-1",
      import_job_id: null,
      codice_cnc_raw: "CNC-001",
      codice_utenza_raw: "UT-001",
      anno_tributario: 2024,
      paid_at: null,
      amount: 5,
      payment_reference: null,
      payment_method: null,
      source: "manual",
      status: "duplicate",
      raw_payload_json: null,
      created_by: 1,
      created_at: "2026-07-17T00:00:00Z",
      updated_at: "2026-07-17T00:00:00Z",
    },
  ],
  notes: [
    {
      id: "note-1",
      avviso_id: "avviso-1",
      body: "Utente contattato",
      visibility: "internal",
      created_by: 1,
      created_at: "2026-07-17T00:00:00Z",
      updated_at: "2026-07-17T00:00:00Z",
    },
  ],
};

const reminder = {
  id: "reminder-1",
  avviso_id: "avviso-1",
  template_id: null,
  status: "generated",
  generated_document_path: "/tmp/sollecito.docx",
  generated_at: "2026-07-18T00:00:00Z",
  generated_by: 1,
  payload_json: null,
  notes: "Sollecito telefonico",
  created_at: "2026-07-18T00:00:00Z",
  download_url: "/ruolo/tributi/reminders/reminder-1/download",
};

describe("Ruolo tributi detail page", () => {
  beforeEach(() => {
    mocks.avvisoId = "avviso-1";
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getTributiAvviso.mockReset();
    mocks.createTributiPayment.mockReset();
    mocks.updateTributiAvvisoStatus.mockReset();
    mocks.addTributiNote.mockReset();
    mocks.listTributiReminders.mockReset();
    mocks.createTributiReminder.mockReset();
    mocks.downloadTributiReminderDocument.mockReset();
    mocks.createObjectURL.mockReset();
    mocks.revokeObjectURL.mockReset();
    mocks.anchorClick.mockReset();
    mocks.getTributiAvviso.mockResolvedValue(detail);
    mocks.createTributiPayment.mockResolvedValue({});
    mocks.updateTributiAvvisoStatus.mockResolvedValue({});
    mocks.addTributiNote.mockResolvedValue({});
    mocks.listTributiReminders.mockResolvedValue([reminder]);
    mocks.createTributiReminder.mockResolvedValue(reminder);
    mocks.downloadTributiReminderDocument.mockResolvedValue(new Blob(["docx"]));
    mocks.createObjectURL.mockReturnValue("blob:sollecito");
    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      value: mocks.createObjectURL,
    });
    Object.defineProperty(window.URL, "revokeObjectURL", {
      configurable: true,
      value: mocks.revokeObjectURL,
    });
    HTMLAnchorElement.prototype.click = mocks.anchorClick;
  });

  test("renders detail and submits payment, status, note and reminder", async () => {
    render(<RuoloTributiDetailPage />);

    expect(await screen.findByText("ROSSI MARIO")).toBeInTheDocument();
    expect(screen.getByText(/CNC CNC-001/)).toBeInTheDocument();
    expect(screen.getByText("Parziale")).toBeInTheDocument();
    expect(screen.getByText("Utente contattato")).toBeInTheDocument();
    expect(screen.getByText("Sollecito telefonico")).toBeInTheDocument();
    expect(mocks.listTributiReminders).toHaveBeenCalledWith("token", "avviso-1");

    fireEvent.change(screen.getByPlaceholderText("Importo"), { target: { value: "60" } });
    fireEvent.change(screen.getByPlaceholderText("Riferimento pagamento"), { target: { value: "PAY-002" } });
    fireEvent.change(screen.getByPlaceholderText("Metodo"), { target: { value: "bonifico" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva pagamento" }));

    await waitFor(() => {
      expect(mocks.createTributiPayment).toHaveBeenCalledWith(
        "token",
        "avviso-1",
        expect.objectContaining({ amount: 60, payment_reference: "PAY-002", payment_method: "bonifico" }),
      );
    });

    fireEvent.change(screen.getByPlaceholderText("Importo"), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva pagamento" }));

    await waitFor(() => {
      expect(mocks.createTributiPayment).toHaveBeenCalledWith(
        "token",
        "avviso-1",
        expect.objectContaining({ amount: 1, payment_reference: null, payment_method: null }),
      );
    });

    const workflowSelect = screen.getByRole("combobox");
    fireEvent.change(workflowSelect, { target: { value: "contestato" } });
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna stato" }));

    await waitFor(() => {
      expect(mocks.updateTributiAvvisoStatus).toHaveBeenCalledWith(
        "token",
        "avviso-1",
        expect.objectContaining({ workflow_status: "contestato" }),
      );
    });

    fireEvent.change(screen.getByPlaceholderText("Nota operativa"), { target: { value: "Promesso pagamento" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva nota" }));

    await waitFor(() => {
      expect(mocks.addTributiNote).toHaveBeenCalledWith("token", "avviso-1", {
        body: "Promesso pagamento",
        visibility: "internal",
      });
    });

    fireEvent.change(screen.getByPlaceholderText("Note per sollecito"), { target: { value: "Inviare PEC" } });
    fireEvent.click(screen.getByRole("button", { name: "Genera sollecito .docx" }));

    await waitFor(() => {
      expect(mocks.createTributiReminder).toHaveBeenCalledWith("token", "avviso-1", { notes: "Inviare PEC" });
    });

    fireEvent.click(screen.getByRole("button", { name: "Genera sollecito .docx" }));

    await waitFor(() => {
      expect(mocks.createTributiReminder).toHaveBeenCalledWith("token", "avviso-1", { notes: null });
    });

    fireEvent.click(screen.getByRole("button", { name: "Scarica .docx" }));

    await waitFor(() => {
      expect(mocks.downloadTributiReminderDocument).toHaveBeenCalledWith(
        "token",
        "/ruolo/tributi/reminders/reminder-1/download",
      );
    });
    expect(mocks.createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    expect(mocks.anchorClick).toHaveBeenCalled();
    expect(mocks.revokeObjectURL).toHaveBeenCalledWith("blob:sollecito");
  });

  test("renders reminder fallback metadata without download action", async () => {
    mocks.listTributiReminders.mockResolvedValueOnce([
      {
        ...reminder,
        id: "reminder-no-document",
        generated_at: null,
        notes: null,
        download_url: null,
      },
    ]);

    render(<RuoloTributiDetailPage />);

    expect(await screen.findByText("Documento predisposto da GAIA")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Scarica .docx" })).not.toBeInTheDocument();
  });

  test("renders empty histories, fallback labels and validates forms", async () => {
    mocks.getTributiAvviso.mockResolvedValueOnce({
      ...detail,
      display_name: null,
      nominativo_raw: null,
      codice_utenza: null,
      codice_fiscale_raw: null,
      domicilio_raw: null,
      residenza_raw: null,
      payment_status: "paid",
      workflow_status: null,
      saldo_amount: null,
      importo_totale_euro: null,
      capacitas_url: null,
      capacitas_avviso_code: null,
      payments: [],
      notes: [],
    });
    mocks.listTributiReminders.mockResolvedValueOnce([]);
    render(<RuoloTributiDetailPage />);

    expect(await screen.findByText("Avviso senza nominativo")).toBeInTheDocument();
    expect(screen.getByText("Nessun pagamento registrato.")).toBeInTheDocument();
    expect(screen.getByText("Nessuna nota registrata.")).toBeInTheDocument();
    expect(screen.getByText("Nessun sollecito generato.")).toBeInTheDocument();
    expect(screen.getAllByText("Pagato").length).toBeGreaterThan(0);
    expect(screen.getAllByText("-").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Salva pagamento" }));
    expect(await screen.findByText("Inserisci un importo pagamento valido.")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Importo"), { target: { value: "abc" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva pagamento" }));
    expect(await screen.findByText("Inserisci un importo pagamento valido.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Salva nota" }));
    expect(await screen.findByText("Scrivi una nota prima di salvarla.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Aggiorna stato" }));
    await waitFor(() => {
      expect(mocks.updateTributiAvvisoStatus).toHaveBeenCalledWith(
        "token",
        "avviso-1",
        expect.objectContaining({ workflow_status: null, capacitas_url: null, capacitas_avviso_code: null }),
      );
    });
  });

  test("renders loading, fetch errors and suspense fallback", async () => {
    mocks.getTributiAvviso.mockReturnValueOnce(new Promise(() => undefined));
    const loadingRender = render(<RuoloTributiDetailPage />);
    expect(await screen.findByText("Caricamento dettaglio tributo...")).toBeInTheDocument();
    loadingRender.unmount();

    mocks.getTributiAvviso.mockRejectedValueOnce(new Error("Avviso non trovato"));
    const errorRender = render(<RuoloTributiDetailPage />);
    expect(await screen.findByText("Dettaglio non disponibile")).toBeInTheDocument();
    expect(screen.getByText("Avviso non trovato")).toBeInTheDocument();
    errorRender.unmount();

    mocks.getTributiAvviso.mockRejectedValueOnce("boom");
    const fallbackErrorRender = render(<RuoloTributiDetailPage />);
    expect(await screen.findByText("Errore dettaglio tributi")).toBeInTheDocument();
    fallbackErrorRender.unmount();

    mocks.getTributiAvviso.mockResolvedValueOnce(null);
    render(<RuoloTributiDetailPage />);
    expect(await screen.findByText("L'avviso richiesto non e stato trovato o non e accessibile.")).toBeInTheDocument();

    render(<RuoloTributiDetailFallback />);
    expect(screen.getAllByText("Caricamento dettaglio tributo...").length).toBeGreaterThan(0);
  });
});
