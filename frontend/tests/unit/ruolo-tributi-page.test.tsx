import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import RuoloTributiPage, { RuoloTributiFallback } from "@/app/ruolo/tributi/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  listTributiAvvisi: vi.fn(),
  getTributiAvviso: vi.fn(),
  createTributiPayment: vi.fn(),
  updateTributiAvvisoStatus: vi.fn(),
  addTributiNote: vi.fn(),
  push: vi.fn(),
  replace: vi.fn(),
  searchParams: new URLSearchParams(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/ruolo-api", () => ({
  listTributiAvvisi: mocks.listTributiAvvisi,
  getTributiAvviso: mocks.getTributiAvviso,
  createTributiPayment: mocks.createTributiPayment,
  updateTributiAvvisoStatus: mocks.updateTributiAvvisoStatus,
  addTributiNote: mocks.addTributiNote,
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
  useRouter: () => ({ push: mocks.push, replace: mocks.replace }),
  useSearchParams: () => mocks.searchParams,
}));

const listItem = {
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
};

const detail = {
  ...listItem,
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

describe("Ruolo tributi page", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.searchParams = new URLSearchParams();
    mocks.push.mockReset();
    mocks.replace.mockReset();
    mocks.listTributiAvvisi.mockReset();
    mocks.getTributiAvviso.mockReset();
    mocks.createTributiPayment.mockReset();
    mocks.updateTributiAvvisoStatus.mockReset();
    mocks.addTributiNote.mockReset();
    mocks.listTributiAvvisi.mockResolvedValue({ items: [listItem], total: 1, page: 1, page_size: 25 });
    mocks.getTributiAvviso.mockResolvedValue(detail);
    mocks.createTributiPayment.mockResolvedValue({});
    mocks.updateTributiAvvisoStatus.mockResolvedValue({});
    mocks.addTributiNote.mockResolvedValue({});
  });

  test("renders tributi list, KPI and applies filters", async () => {
    render(<RuoloTributiPage />);

    expect(await screen.findByText("Tributi Ruolo")).toBeInTheDocument();
    expect(await screen.findByText("ROSSI MARIO")).toBeInTheDocument();
    expect(screen.getAllByText("Parziale").length).toBeGreaterThan(0);
    expect(screen.getAllByText("60,00 €").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByPlaceholderText("Rossi, CNC, utenza, comune..."), {
      target: { value: "Oristano" },
    });
    fireEvent.change(screen.getByPlaceholderText("Anno"), { target: { value: "2024" } });
    fireEvent.change(screen.getByPlaceholderText("Comune"), { target: { value: "Mogoro" } });
    fireEvent.click(screen.getByRole("button", { name: "Applica" }));

    expect(mocks.replace).toHaveBeenCalledWith(expect.stringContaining("/ruolo/tributi?"));
    expect(mocks.replace).toHaveBeenCalledWith(expect.stringContaining("q=Oristano"));
    expect(mocks.replace).toHaveBeenCalledWith(expect.stringContaining("anno=2024"));
    expect(mocks.replace).toHaveBeenCalledWith(expect.stringContaining("comune=Mogoro"));
  });

  test("loads detail and submits payment, status and note", async () => {
    render(<RuoloTributiPage />);

    fireEvent.click(await screen.findByText("ROSSI MARIO"));
    expect(await screen.findByText("Registra pagamento")).toBeInTheDocument();
    expect(screen.getByText("Utente contattato")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Importo"), { target: { value: "60" } });
    fireEvent.change(screen.getByPlaceholderText("Riferimento pagamento"), { target: { value: "PAY-002" } });
    fireEvent.change(screen.getByPlaceholderText("Metodo, es. bonifico"), { target: { value: "bonifico" } });
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

    const workflowSelect = screen.getAllByRole("combobox").at(-1);
    expect(workflowSelect).toBeDefined();
    fireEvent.change(workflowSelect!, { target: { value: "contestato" } });
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna stato" }));

    await waitFor(() => {
      expect(mocks.updateTributiAvvisoStatus).toHaveBeenCalledWith(
        "token",
        "avviso-1",
        expect.objectContaining({ workflow_status: "contestato" }),
      );
    });

    fireEvent.change(screen.getByPlaceholderText("Es. utente contattato, pratica contestata..."), {
      target: { value: "Promesso pagamento" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Salva nota" }));

    await waitFor(() => {
      expect(mocks.addTributiNote).toHaveBeenCalledWith("token", "avviso-1", {
        body: "Promesso pagamento",
        visibility: "internal",
      });
    });
  });

  test("renders empty and loading/error states", async () => {
    mocks.listTributiAvvisi.mockReturnValue(new Promise(() => undefined));
    const { unmount } = render(<RuoloTributiPage />);
    expect(await screen.findByText("Caricamento tributi...")).toBeInTheDocument();
    unmount();

    mocks.listTributiAvvisi.mockRejectedValueOnce(new Error("Accesso negato"));
    const errorRender = render(<RuoloTributiPage />);
    expect(await screen.findByText("Accesso negato")).toBeInTheDocument();
    errorRender.unmount();

    mocks.listTributiAvvisi.mockRejectedValueOnce("boom");
    const fallbackErrorRender = render(<RuoloTributiPage />);
    expect(await screen.findByText("Errore caricamento tributi")).toBeInTheDocument();
    fallbackErrorRender.unmount();

    mocks.listTributiAvvisi.mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 25 });
    render(<RuoloTributiPage />);
    expect(await screen.findByText("Nessuna posizione trovata")).toBeInTheDocument();
  });

  test("supports reset, pagination and status filters", async () => {
    mocks.searchParams = new URLSearchParams("page=2&open_only=false&unlinked=true");
    mocks.listTributiAvvisi.mockResolvedValueOnce({
      items: [
        { ...listItem, id: "paid", payment_status: "paid", workflow_status: null, saldo_amount: 0, paid_amount: 100, is_linked: true },
        { ...listItem, id: "over", payment_status: "overpaid", saldo_amount: -5, paid_amount: 105 },
        { ...listItem, id: "review", payment_status: "to_review", importo_totale_euro: null, saldo_amount: null },
        {
          ...listItem,
          id: "unpaid",
          display_name: null,
          nominativo_raw: null,
          codice_fiscale_raw: null,
          codice_utenza: null,
          payment_status: "unpaid",
          paid_amount: 0,
          saldo_amount: 100,
        },
      ],
      total: 50,
      page: 2,
      page_size: 25,
    });

    render(<RuoloTributiPage />);

    expect(await screen.findByText("Pagato")).toBeInTheDocument();
    expect(screen.getAllByText("Eccedenza").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Da verificare").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Non pagato").length).toBeGreaterThan(0);
    expect(screen.getByText("Avviso senza nominativo")).toBeInTheDocument();
    expect(screen.getByText(/CF\/P.IVA - · Utenza -/)).toBeInTheDocument();

    const comboboxes = screen.getAllByRole("combobox");
    fireEvent.change(comboboxes[0], { target: { value: "paid" } });
    fireEvent.change(comboboxes[1], { target: { value: "moroso" } });
    fireEvent.click(screen.getByLabelText("Solo scoperti"));
    fireEvent.click(screen.getByLabelText("Solo scoperti"));
    fireEvent.click(screen.getByLabelText("Non collegati"));
    fireEvent.click(screen.getByLabelText("Non collegati"));
    fireEvent.click(screen.getByRole("button", { name: "Applica" }));

    expect(mocks.replace).toHaveBeenCalledWith(expect.stringContaining("payment_status=paid"));
    expect(mocks.replace).toHaveBeenCalledWith(expect.stringContaining("workflow_status=moroso"));
    expect(mocks.replace).toHaveBeenCalledWith(expect.stringContaining("open_only=false"));
    expect(mocks.replace).toHaveBeenCalledWith(expect.stringContaining("unlinked=true"));

    fireEvent.click(screen.getByRole("button", { name: "Precedente" }));
    expect(mocks.push).toHaveBeenCalledWith(expect.stringContaining("page=1"));

    fireEvent.click(screen.getByRole("button", { name: "Reset" }));
    expect(mocks.push).toHaveBeenCalledWith("/ruolo/tributi?page=1");
  });

  test("loads API filters from URL search params", async () => {
    mocks.searchParams = new URLSearchParams(
      "q=Rossi&anno=2024&comune=Mogoro&payment_status=partial&workflow_status=moroso",
    );
    render(<RuoloTributiPage />);
    await screen.findByText("ROSSI MARIO");

    expect(mocks.listTributiAvvisi).toHaveBeenCalledWith(
      "token",
      expect.objectContaining({
        q: "Rossi",
        anno: 2024,
        comune: "Mogoro",
        payment_status: "partial",
        workflow_status: "moroso",
      }),
    );
  });

  test("supports next pagination and fallback rendering", async () => {
    mocks.listTributiAvvisi.mockResolvedValueOnce({ items: [listItem], total: 50, page: 1, page_size: 25 });
    render(<RuoloTributiPage />);
    expect(await screen.findByText("ROSSI MARIO")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Successiva" }));
    expect(mocks.push).toHaveBeenCalledWith(expect.stringContaining("page=2"));

    render(<RuoloTributiFallback />);
    expect(screen.getByText("Caricamento sezione tributi...")).toBeInTheDocument();
  });

  test("handles detail errors and validates empty forms", async () => {
    mocks.getTributiAvviso.mockRejectedValueOnce(new Error("Dettaglio non disponibile"));
    const { unmount } = render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByText("ROSSI MARIO"));
    expect(await screen.findByText("Dettaglio non disponibile")).toBeInTheDocument();
    unmount();

    mocks.getTributiAvviso.mockRejectedValueOnce("boom");
    const fallbackDetailRender = render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByText("ROSSI MARIO"));
    expect(await screen.findByText("Errore dettaglio tributi")).toBeInTheDocument();
    fallbackDetailRender.unmount();

    mocks.getTributiAvviso.mockResolvedValueOnce({
      ...detail,
      display_name: null,
      nominativo_raw: null,
      workflow_status: null,
      capacitas_url: null,
      capacitas_avviso_code: null,
      payments: [],
      notes: [],
    });
    render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByText("ROSSI MARIO"));

    expect(await screen.findByText("Avviso selezionato")).toBeInTheDocument();
    expect(screen.getByText("Nessun pagamento registrato.")).toBeInTheDocument();
    expect(screen.getByText("Nessuna nota.")).toBeInTheDocument();

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
        expect.objectContaining({
          workflow_status: null,
          capacitas_url: null,
          capacitas_avviso_code: null,
        }),
      );
    });
  });
});
