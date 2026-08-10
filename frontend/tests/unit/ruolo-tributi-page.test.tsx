import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { RuoloTributiFallback } from "@/app/ruolo/tributi/fallback";
import RuoloTributiPage from "@/app/ruolo/tributi/page";
import type { CurrentUser } from "@/types/api";
import type { RuoloTributiAvvisoListItemResponse } from "@/types/ruolo";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn(),
  listTributiAvvisi: vi.fn(),
  getTributiSummary: vi.fn(),
  getTributiAvviso: vi.fn(),
  listTributiReminderCandidates: vi.fn(),
  createTributiReminderBatch: vi.fn(),
  downloadTributiReminderDocument: vi.fn(),
  createTributiPayment: vi.fn(),
  updateTributiAvvisoStatus: vi.fn(),
  addTributiNote: vi.fn(),
  listTributiYearManagers: vi.fn(),
  createTributiYearManager: vi.fn(),
  updateTributiYearManager: vi.fn(),
  deleteTributiYearManager: vi.fn(),
  listTributiCalculationPolicies: vi.fn(),
  fetchTributiEuribor6mRate: vi.fn(),
  createTributiCalculationPolicy: vi.fn(),
  updateTributiCalculationPolicy: vi.fn(),
  deleteTributiCalculationPolicy: vi.fn(),
  listTributiRegisteredMails: vi.fn(),
  createCapacitasInCassSyncJob: vi.fn(),
  push: vi.fn(),
  replace: vi.fn(),
  searchParams: new URLSearchParams(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/ruolo-api", () => ({
  listTributiAvvisi: mocks.listTributiAvvisi,
  getTributiSummary: mocks.getTributiSummary,
  getTributiAvviso: mocks.getTributiAvviso,
  listTributiReminderCandidates: mocks.listTributiReminderCandidates,
  createTributiReminderBatch: mocks.createTributiReminderBatch,
  downloadTributiReminderDocument: mocks.downloadTributiReminderDocument,
  createTributiPayment: mocks.createTributiPayment,
  updateTributiAvvisoStatus: mocks.updateTributiAvvisoStatus,
  addTributiNote: mocks.addTributiNote,
  listTributiYearManagers: mocks.listTributiYearManagers,
  createTributiYearManager: mocks.createTributiYearManager,
  updateTributiYearManager: mocks.updateTributiYearManager,
  deleteTributiYearManager: mocks.deleteTributiYearManager,
  listTributiCalculationPolicies: mocks.listTributiCalculationPolicies,
  fetchTributiEuribor6mRate: mocks.fetchTributiEuribor6mRate,
  createTributiCalculationPolicy: mocks.createTributiCalculationPolicy,
  updateTributiCalculationPolicy: mocks.updateTributiCalculationPolicy,
  deleteTributiCalculationPolicy: mocks.deleteTributiCalculationPolicy,
  listTributiRegisteredMails: mocks.listTributiRegisteredMails,
}));

vi.mock("@/lib/api", () => ({
  createCapacitasInCassSyncJob: mocks.createCapacitasInCassSyncJob,
  getCurrentUser: mocks.getCurrentUser,
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

const listItem: RuoloTributiAvvisoListItemResponse = {
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
  annuality_manager_key: "gaia",
  annuality_manager_label: "Consorzio/GAIA",
  calculation_policy_id: "policy-2024",
  calculation_policy_name: "Regola ruolo 2024",
  calculation_policy: "internal_gaia",
  reminder_enabled: true,
};

function buildCurrentUser(overrides: Partial<CurrentUser> = {}): CurrentUser {
  return {
    id: 1,
    username: "admin",
    email: "admin@example.test",
    role: "admin",
    is_active: true,
    module_accessi: true,
    module_rete: true,
    module_inventario: true,
    module_gis: true,
    module_catasto: true,
    module_utenze: true,
    module_operazioni: true,
    module_riordino: true,
    module_ruolo: true,
    module_presenze: true,
    enabled_modules: ["ruolo"],
    ...overrides,
  };
}

const detail = {
  ...listItem,
  interest_start_date: "2026-07-01",
  interest_start_source: "pec_accepted_at",
  domicilio_raw: "VIA TEST 1",
  residenza_raw: "ORISTANO",
  importo_totale_0648: 80,
  importo_totale_0985: 20,
  importo_totale_0668: 0,
  incass_notice: {
    detail_url: "https://incass3.servizicapacitas.com/pages/dettaglioAvviso.aspx?avviso=1",
    source_notice_id: "020210002922120",
    stato_label: "Rateizzato e pagato in parte",
    importo_carico: "100,00",
    importo_riscosso: "-40,00",
    importo_residuo: "63,00",
    importo_rateizzato: "103,00",
    rateization_fee_amount: 3,
  },
  mailing_delivery: {
    source_notice_id: "020210002922120",
    pec_recipient: "rossi.mario@pec.example.it",
    delivery_status: "Accettazione, Consegna",
    delivered_at: "17/12/2021 20:01:58",
    accepted_at: "17/12/2021 20:01:57",
    receipt_groups: ["ACCETTAZIONE", "CONSEGNA"],
    receipt_documents_count: 2,
  },
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

const tributiSummary = {
  to_send_count: 1,
  sent_count: 1,
  pec_count: 1,
  raccomandata_count: 0,
  total_count: 2,
  total_amount: 180,
  pec_amount: 100,
  raccomandata_amount: 0,
  raccomandata_source_available: false,
};

const reminderCandidate2024 = {
  codice_fiscale: "RSSMRA80A01H501Z",
  display_name: "ROSSI MARIO",
  comune: "URAS",
  years: [2024],
  avvisi_count: 1,
  due_amount: 100,
  paid_amount: 40,
  saldo_amount: 60,
  subject_id: "subject-1",
  nas_folder_path: "/nas/R/RSSMRA80A01H501Z",
  has_nas_folder: true,
  annuality_managers: ["Consorzio/GAIA"],
  avvisi: [
    {
      id: "avviso-1",
      codice_cnc: "CNC-001",
      anno_tributario: 2024,
      importo_totale_euro: 100,
      paid_amount: 40,
      saldo_amount: 60,
      payment_status: "partial",
      capacitas_url: null,
      annuality_manager_key: "gaia",
      annuality_manager_label: "Consorzio/GAIA",
      calculation_policy: "internal_gaia",
    },
  ],
};

const reminderCandidate2025 = {
  ...reminderCandidate2024,
  years: [2025],
  avvisi_count: 1,
  due_amount: 150,
  paid_amount: 0,
  saldo_amount: 150,
  avvisi: [
    {
      id: "avviso-2",
      codice_cnc: "CNC-002",
      anno_tributario: 2025,
      importo_totale_euro: 150,
      paid_amount: 0,
      saldo_amount: 150,
      payment_status: "unpaid",
      capacitas_url: null,
      annuality_manager_key: "gaia",
      annuality_manager_label: "Consorzio/GAIA",
      calculation_policy: "internal_gaia",
    },
  ],
};

const yearManagers = [
  {
    id: "manager-ade",
    manager_key: "agenzia_entrate",
    manager_label: "Agenzia delle Entrate",
    year_from: null,
    year_to: 2017,
    calculation_policy: "external_ade",
    is_active: true,
    notes: "Annualita fino al 2017.",
    updated_by: null,
    created_at: "2026-07-22T00:00:00Z",
    updated_at: "2026-07-22T00:00:00Z",
  },
  {
    id: "manager-gaia",
    manager_key: "gaia",
    manager_label: "Consorzio/GAIA",
    year_from: 2022,
    year_to: null,
    calculation_policy: "internal_gaia",
    is_active: true,
    notes: "Annualita dal 2022.",
    updated_by: null,
    created_at: "2026-07-22T00:00:00Z",
    updated_at: "2026-07-22T00:00:00Z",
  },
  {
    id: "manager-step",
    manager_key: "step",
    manager_label: "STEP - Agenzia recupero crediti",
    year_from: 2018,
    year_to: 2021,
    calculation_policy: "external_recovery",
    is_active: true,
    notes: null,
    updated_by: null,
    created_at: "2026-07-22T00:00:00Z",
    updated_at: "2026-07-22T00:00:00Z",
  },
  {
    id: "manager-single",
    manager_key: "single",
    manager_label: "Annualita singola",
    year_from: 2022,
    year_to: 2022,
    calculation_policy: "internal_gaia",
    is_active: false,
    notes: null,
    updated_by: null,
    created_at: "2026-07-22T00:00:00Z",
    updated_at: "2026-07-22T00:00:00Z",
  },
  {
    id: "manager-all",
    manager_key: "all",
    manager_label: "Tutte le annualita",
    year_from: null,
    year_to: null,
    calculation_policy: "external",
    is_active: false,
    notes: null,
    updated_by: null,
    created_at: "2026-07-22T00:00:00Z",
    updated_at: "2026-07-22T00:00:00Z",
  },
];

const calculationPolicies = [
  {
    id: "policy-gaia-2024",
    name: "Maggiorazioni ruoli GAIA",
    year_from: 2024,
    year_to: 2025,
    bonario_due_date: "2025-05-26",
    surcharge_rate_percent: 3,
    surcharge_from: "2025-05-27",
    euribor_6m_rate_percent: 1.25,
    euribor_source_url: "https://data-api.ecb.europa.eu/service/data/FM/M.U2.EUR.RT.MM.EURIBOR6MD_.HSTA?format=csvdata&startPeriod=2024-01&endPeriod=2024-12",
    euribor_reference_period: "2024",
    euribor_fetched_at: "2026-08-06T13:00:00Z",
    interest_rate_percent: 5,
    effective_interest_rate_percent: 6.25,
    interest_from: "2025-05-27",
    interest_start_mode: "notification_date" as const,
    is_active: true,
    notes: "Interessi da invio PEC/ricezione raccomandata.",
    updated_by: null,
    created_at: "2026-07-22T00:00:00Z",
    updated_at: "2026-07-22T00:00:00Z",
  },
];

const reminderBatch = {
  id: "batch-1",
  title: "Solleciti tributi",
  status: "generated",
  template_path: "/tmp/template.docx",
  filters_json: {},
  items_total: 1,
  items_generated: 1,
  items_failed: 0,
  generated_by: 1,
  generated_at: "2026-07-22T00:00:00Z",
  notes: "Batch generato da wizard tributi GAIA.",
  created_at: "2026-07-22T00:00:00Z",
  updated_at: "2026-07-22T00:00:00Z",
  items: [
    {
      id: "item-1",
      batch_id: "batch-1",
      subject_id: "subject-1",
      codice_fiscale: "RSSMRA80A01H501Z",
      display_name: "ROSSI MARIO",
      comune_key: "URAS",
      years_json: [2024, 2025],
      avviso_ids_json: ["avviso-1", "avviso-2"],
      due_amount: 250,
      paid_amount: 40,
      saldo_amount: 210,
      nas_folder_path: "/nas/R/RSSMRA80A01H501Z",
      generated_document_path: "/nas/R/RSSMRA80A01H501Z/solleciti/RSSMRA80A01H501Z_avviso_sollecito_2024-2025.pdf",
      status: "generated",
      error_detail: null,
      payload_json: { notice_number: "12026242500001" },
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z",
      download_url: "/ruolo/tributi/solleciti/items/item-1/download",
    },
  ],
};

describe("Ruolo tributi page", () => {
  beforeEach(() => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 1024,
    });
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getCurrentUser.mockReset();
    mocks.getCurrentUser.mockResolvedValue(buildCurrentUser());
    mocks.searchParams = new URLSearchParams();
    mocks.push.mockReset();
    mocks.replace.mockReset();
    mocks.listTributiAvvisi.mockReset();
    mocks.getTributiSummary.mockReset();
    mocks.getTributiAvviso.mockReset();
    mocks.listTributiReminderCandidates.mockReset();
    mocks.createTributiReminderBatch.mockReset();
    mocks.downloadTributiReminderDocument.mockReset();
    mocks.createTributiPayment.mockReset();
    mocks.updateTributiAvvisoStatus.mockReset();
    mocks.addTributiNote.mockReset();
    mocks.listTributiYearManagers.mockReset();
    mocks.createTributiYearManager.mockReset();
    mocks.updateTributiYearManager.mockReset();
    mocks.deleteTributiYearManager.mockReset();
    mocks.listTributiCalculationPolicies.mockReset();
    mocks.fetchTributiEuribor6mRate.mockReset();
    mocks.createTributiCalculationPolicy.mockReset();
    mocks.updateTributiCalculationPolicy.mockReset();
    mocks.deleteTributiCalculationPolicy.mockReset();
    mocks.listTributiRegisteredMails.mockReset();
    mocks.createCapacitasInCassSyncJob.mockReset();
    mocks.listTributiAvvisi.mockResolvedValue({ items: [listItem], total: 1, page: 1, page_size: 25 });
    mocks.getTributiSummary.mockResolvedValue(tributiSummary);
    mocks.getTributiAvviso.mockResolvedValue(detail);
    mocks.listTributiReminderCandidates.mockImplementation((_token: string, params?: { anno_from?: number }) => {
      if (params?.anno_from === 2025) {
        return Promise.resolve({ items: [reminderCandidate2025], total: 1, page: 1, page_size: 80 });
      }
      return Promise.resolve({ items: [reminderCandidate2024], total: 1, page: 1, page_size: 80 });
    });
    mocks.createTributiReminderBatch.mockResolvedValue(reminderBatch);
    mocks.downloadTributiReminderDocument.mockResolvedValue(new Blob(["pdf"], { type: "application/pdf" }));
    mocks.createTributiPayment.mockResolvedValue({});
    mocks.updateTributiAvvisoStatus.mockResolvedValue({});
    mocks.addTributiNote.mockResolvedValue({});
    mocks.listTributiYearManagers.mockResolvedValue({ items: yearManagers });
    mocks.createTributiYearManager.mockResolvedValue(yearManagers[1]);
    mocks.updateTributiYearManager.mockResolvedValue(yearManagers[1]);
    mocks.deleteTributiYearManager.mockResolvedValue(undefined);
    mocks.listTributiCalculationPolicies.mockResolvedValue({ items: calculationPolicies });
    mocks.fetchTributiEuribor6mRate.mockResolvedValue({
      year: 2025,
      rate_percent: 3.25,
      reference_period: "2025",
      source_url: "https://data-api.ecb.europa.eu/service/data/FM/M.U2.EUR.RT.MM.EURIBOR6MD_.HSTA?format=csvdata&startPeriod=2025-01&endPeriod=2025-12",
      verification_url: "https://data.ecb.europa.eu/data/datasets/FM/FM.M.U2.EUR.RT.MM.EURIBOR6MD_.HSTA",
      fetched_at: "2026-08-06T14:00:00Z",
      observations_count: 12,
    });
    mocks.createTributiCalculationPolicy.mockResolvedValue(calculationPolicies[0]);
    mocks.updateTributiCalculationPolicy.mockResolvedValue(calculationPolicies[0]);
    mocks.deleteTributiCalculationPolicy.mockResolvedValue(undefined);
    mocks.listTributiRegisteredMails.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 25 });
    mocks.createCapacitasInCassSyncJob.mockResolvedValue({ id: 88 });
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:sollecito-preview"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
  });

  test("renders tributi list, KPI and auto-applies complete filters", async () => {
    render(<RuoloTributiPage />);

    expect(await screen.findByText("Tributi Ruolo")).toBeInTheDocument();
    expect(await screen.findByText("ROSSI MARIO")).toBeInTheDocument();
    expect(screen.getAllByText(/CNC 020210002922120/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Parziale").length).toBeGreaterThan(0);
    expect(screen.getAllByText("60,00 €").length).toBeGreaterThan(0);
    expect(screen.getByText("Da inviare")).toBeInTheDocument();
    expect(screen.getByText("Avvisi inviati")).toBeInTheDocument();
    expect(screen.getByText("Via PEC")).toBeInTheDocument();
    expect(screen.getByText("Via raccomandata")).toBeInTheDocument();
    expect(screen.getByText("Totale avvisi")).toBeInTheDocument();
    expect(screen.getByText("Totale via PEC")).toBeInTheDocument();
    expect(screen.getByText("Totale via raccomandata")).toBeInTheDocument();
    expect(screen.getByText("180,00 €")).toBeInTheDocument();
    expect(screen.getAllByText("100,00 €").length).toBeGreaterThan(0);
    expect(screen.getAllByText("0,00 €").length).toBeGreaterThan(0);
    expect(screen.getByText("In attesa del file Excel raccomandate")).toBeInTheDocument();
    expect(await screen.findByText("Gestori annualita tributo")).toBeInTheDocument();
    const adeFilter = screen.getByRole("button", { name: "Fino al 2017 · Agenzia delle Entrate" });
    const stepFilter = screen.getByRole("button", { name: "2018-2021 · STEP - Agenzia recupero crediti" });
    const gaiaFilter = screen.getByRole("button", { name: "Dal 2022 · Consorzio/GAIA" });
    expect(adeFilter).toHaveClass("bg-red-50");
    expect(stepFilter).toHaveClass("bg-orange-50");
    expect(gaiaFilter).toHaveClass("bg-yellow-400");
    expect(gaiaFilter).toHaveAttribute("aria-pressed", "true");
    await waitFor(() => {
      expect(mocks.listTributiAvvisi).toHaveBeenCalledWith("token", expect.objectContaining({ manager_key: "gaia" }));
      expect(mocks.getTributiSummary).toHaveBeenCalledWith("token", expect.objectContaining({ manager_key: "gaia", open_only: true }));
    });

    fireEvent.change(screen.getByPlaceholderText("Rossi, CNC, utenza, comune..."), {
      target: { value: "Ro" },
    });
    await new Promise((resolve) => setTimeout(resolve, 420));
    expect(mocks.replace).not.toHaveBeenCalledWith(expect.stringContaining("q=Ro"));

    fireEvent.change(screen.getByPlaceholderText("Rossi, CNC, utenza, comune..."), {
      target: { value: "Oristano" },
    });
    fireEvent.change(screen.getByPlaceholderText("Anno completo"), { target: { value: "202" } });
    await new Promise((resolve) => setTimeout(resolve, 420));
    expect(mocks.replace).not.toHaveBeenCalledWith(expect.stringContaining("anno=202"));

    fireEvent.change(screen.getByPlaceholderText("Anno completo"), { target: { value: "20ab24" } });
    fireEvent.change(screen.getByPlaceholderText("Comune"), { target: { value: "Mogoro" } });

    await waitFor(() => {
      expect(mocks.replace).toHaveBeenCalledWith(expect.stringContaining("/ruolo/tributi?"));
      expect(mocks.replace).toHaveBeenCalledWith(expect.stringContaining("q=Oristano"));
      expect(mocks.replace).toHaveBeenCalledWith(expect.stringContaining("anno=2024"));
      expect(mocks.replace).toHaveBeenCalledWith(expect.stringContaining("comune=Mogoro"));
    });

    fireEvent.click(stepFilter);
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith(expect.stringContaining("manager_key=step")));
    expect(stepFilter).toHaveClass("bg-orange-600");
    expect(gaiaFilter).toHaveClass("bg-yellow-50");
    fireEvent.click(adeFilter);
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith(expect.stringContaining("manager_key=agenzia_entrate")));
    expect(adeFilter).toHaveClass("bg-red-700");
  });

  test("renders tributi list without registered mails console", async () => {
    render(<RuoloTributiPage />);

    const tributiSectionLabel = await screen.findByText("Elenco tributi");

    expect(tributiSectionLabel).toBeInTheDocument();
    expect(screen.queryByText("Raccomandate Poste Online")).not.toBeInTheDocument();
  });

  test("manages annuality managers configuration", async () => {
    render(<RuoloTributiPage />);

    expect(await screen.findByText("Gestori annualita tributo")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Gestisci regole" }));
    expect((await screen.findAllByText("Agenzia delle Entrate")).length).toBeGreaterThan(0);
    expect(screen.getByText("2018-2021")).toBeInTheDocument();
    expect(screen.getByText("2022")).toBeInTheDocument();
    expect(screen.getAllByText("Tutte le annualita").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi" }));
    expect((await screen.findAllByText("Inserisci chiave e descrizione gestore.")).length).toBeGreaterThan(0);

    fireEvent.click(screen.getAllByRole("button", { name: "Modifica" })[0]);
    expect(screen.getByDisplayValue("2017")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Annulla" }));

    fireEvent.click(screen.getAllByRole("button", { name: "Modifica" })[2]);
    expect(screen.getByDisplayValue("STEP - Agenzia recupero crediti")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Annulla" }));

    fireEvent.click(screen.getAllByRole("button", { name: "Modifica" })[1]);
    fireEvent.change(screen.getByPlaceholderText("Anno a, vuoto = aperto"), { target: { value: "2025" } });
    fireEvent.change(screen.getByPlaceholderText("Note operative"), { target: { value: "Note aggiornate" } });
    fireEvent.click(screen.getByLabelText("Regola attiva"));
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna" }));

    await waitFor(() => {
      expect(mocks.updateTributiYearManager).toHaveBeenCalledWith(
        "token",
        "manager-gaia",
        expect.objectContaining({ manager_key: "gaia", year_from: 2022, year_to: 2025, is_active: false, notes: "Note aggiornate" }),
      );
    });

    fireEvent.change(screen.getByPlaceholderText("Descrizione, es. STEP"), { target: { value: "Nuovo Gestore" } });
    fireEvent.change(screen.getByPlaceholderText("Chiave, es. step"), { target: { value: "Nuovo Gestore!" } });
    fireEvent.change(screen.getByPlaceholderText("Anno da, vuoto = -inf"), { target: { value: "2026" } });
    fireEvent.change(screen.getByPlaceholderText("Policy calcolo"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi" }));

    await waitFor(() => {
      expect(mocks.createTributiYearManager).toHaveBeenCalledWith(
        "token",
        expect.objectContaining({
          manager_key: "nuovo_gestore",
          manager_label: "Nuovo Gestore",
          year_from: 2026,
          year_to: null,
          calculation_policy: "external",
        }),
      );
    });

    fireEvent.click(screen.getAllByRole("button", { name: "Modifica" })[0]);
    fireEvent.click(screen.getAllByRole("button", { name: "Elimina" })[0]);
    await waitFor(() => expect(mocks.deleteTributiYearManager).toHaveBeenCalledWith("token", "manager-ade"));
    fireEvent.click(screen.getAllByRole("button", { name: "Elimina" })[1]);
    await waitFor(() => expect(mocks.deleteTributiYearManager).toHaveBeenCalledWith("token", "manager-gaia"));
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    expect(screen.queryByText("Configura competenza e policy calcolo")).not.toBeInTheDocument();
  });

  test("handles annuality manager loading and mutation errors", async () => {
    mocks.listTributiYearManagers.mockRejectedValueOnce(new Error("Gestori non disponibili"));
    const loadingErrorRender = render(<RuoloTributiPage />);
    expect(await screen.findByText("Gestori non disponibili")).toBeInTheDocument();
    loadingErrorRender.unmount();

    mocks.listTributiYearManagers.mockRejectedValueOnce("boom");
    const fallbackLoadingErrorRender = render(<RuoloTributiPage />);
    expect(await screen.findByText("Errore caricamento gestori annualita")).toBeInTheDocument();
    fallbackLoadingErrorRender.unmount();

    mocks.createTributiYearManager.mockRejectedValueOnce("boom");
    render(<RuoloTributiPage />);
    expect(await screen.findByText("Gestori annualita tributo")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Gestisci regole" }));
    fireEvent.change(screen.getByPlaceholderText("Descrizione, es. STEP"), { target: { value: "Errore" } });
    fireEvent.change(screen.getByPlaceholderText("Chiave, es. step"), { target: { value: "errore" } });
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi" }));
    expect((await screen.findAllByText("Errore salvataggio gestore annualita")).length).toBeGreaterThan(0);

    mocks.deleteTributiYearManager.mockRejectedValueOnce("boom");
    fireEvent.click(screen.getAllByRole("button", { name: "Elimina" })[0]);
    expect((await screen.findAllByText("Errore eliminazione gestore annualita")).length).toBeGreaterThan(0);

    mocks.createTributiYearManager.mockRejectedValueOnce(new Error("Salvataggio bloccato"));
    fireEvent.change(screen.getByPlaceholderText("Descrizione, es. STEP"), { target: { value: "Errore 2" } });
    fireEvent.change(screen.getByPlaceholderText("Chiave, es. step"), { target: { value: "errore_2" } });
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi" }));
    expect((await screen.findAllByText("Salvataggio bloccato")).length).toBeGreaterThan(0);

    mocks.deleteTributiYearManager.mockRejectedValueOnce(new Error("Eliminazione bloccata"));
    fireEvent.click(screen.getAllByRole("button", { name: "Elimina" })[0]);
    expect((await screen.findAllByText("Eliminazione bloccata")).length).toBeGreaterThan(0);
  });

  test("manages calculation policies configuration", async () => {
    render(<RuoloTributiPage />);

    expect(await screen.findByText("Regole ruolo")).toBeInTheDocument();
    expect(await screen.findByText("Maggiorazioni ruoli GAIA")).toBeInTheDocument();
    expect(screen.getAllByText("Annualita 2024").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Annualita 2025").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Gestisci regole calcolo" }));

    const dialog = screen.getByText("Scadenza bonaria, maggiorazioni e interessi").closest("div")?.parentElement?.parentElement;
    expect(dialog).not.toBeNull();
    const modal = within(dialog as HTMLElement);
    expect(await modal.findByText("Maggiorazioni ruoli GAIA")).toBeInTheDocument();
    const policyCard = modal.getByText("Maggiorazioni ruoli GAIA").closest("article");
    expect(policyCard).not.toBeNull();
    expect(policyCard).toHaveTextContent("Annualita 2024");
    expect(policyCard).toHaveTextContent("Annualita 2025");
    expect(policyCard).toHaveTextContent("Scadenza bonaria 26/05/25");
    expect(policyCard).toHaveTextContent("Maggiorazione dal 27/05/25");
    expect(policyCard).toHaveTextContent("Fallback/minimo interessi 27/05/25");
    expect(policyCard).toHaveTextContent("interessi effettivi 6,25%");
    expect(policyCard).toHaveTextContent("Fonte Euribor BCE 2024");

    fireEvent.click(modal.getByRole("button", { name: "Modifica" }));
    fireEvent.change(modal.getByPlaceholderText("Nome, es. Ruoli morosi 2024"), { target: { value: "Policy aggiornata" } });
    fireEvent.change(modal.getByPlaceholderText("Anno da"), { target: { value: "2025" } });
    fireEvent.change(modal.getByPlaceholderText("Anno a"), { target: { value: "2026" } });
    fireEvent.click(modal.getByRole("button", { name: "Recupera da BCE" }));
    await waitFor(() => expect(mocks.fetchTributiEuribor6mRate).toHaveBeenCalledWith("token", 2025));
    expect(await modal.findByText("verifica il dato BCE")).toBeInTheDocument();
    fireEvent.change(modal.getByPlaceholderText("es. 3"), { target: { value: "4,5" } });
    expect(await modal.findByText("Date per annualita")).toBeInTheDocument();
    fireEvent.change(modal.getByLabelText("Scadenza pagamento bonario 2025"), { target: { value: "2026-07-31" } });
    fireEvent.change(modal.getByLabelText("Scadenza pagamento bonario 2026"), { target: { value: "2027-07-31" } });
    fireEvent.change(modal.getByLabelText("% tasso da delibera"), { target: { value: "abc" } });
    fireEvent.change(modal.getByLabelText("Fallback/minimo interessi 2025"), { target: { value: "2026-08-10" } });
    fireEvent.change(modal.getByLabelText("Fallback/minimo interessi 2026"), { target: { value: "2027-08-10" } });
    fireEvent.change(modal.getByLabelText("Decorrenza interessi"), { target: { value: "fixed_date" } });
    fireEvent.change(modal.getByPlaceholderText("Note operative"), { target: { value: "Nuova nota" } });
    fireEvent.click(modal.getByLabelText("Policy attiva"));
    fireEvent.click(modal.getByRole("button", { name: "Aggiorna" }));

    await waitFor(() => expect(mocks.updateTributiCalculationPolicy).toHaveBeenCalled());
    expect(mocks.updateTributiCalculationPolicy).toHaveBeenCalledWith("token", "policy-gaia-2024", {
      name: "Policy aggiornata 2025",
      year_from: 2025,
      year_to: 2025,
      bonario_due_date: "2026-07-31",
      surcharge_rate_percent: 4.5,
      surcharge_from: null,
      euribor_6m_rate_percent: 3.25,
      euribor_source_url: "https://data-api.ecb.europa.eu/service/data/FM/M.U2.EUR.RT.MM.EURIBOR6MD_.HSTA?format=csvdata&startPeriod=2025-01&endPeriod=2025-12",
      euribor_reference_period: "2025",
      euribor_fetched_at: "2026-08-06T14:00:00Z",
      interest_rate_percent: 0,
      interest_from: "2026-08-10",
      interest_start_mode: "fixed_date",
      is_active: false,
      notes: "Nuova nota",
    });
    expect(mocks.createTributiCalculationPolicy).toHaveBeenCalledWith("token", {
      name: "Policy aggiornata 2026",
      year_from: 2026,
      year_to: 2026,
      bonario_due_date: "2027-07-31",
      surcharge_rate_percent: 4.5,
      surcharge_from: null,
      euribor_6m_rate_percent: 3.25,
      euribor_source_url: "https://data-api.ecb.europa.eu/service/data/FM/M.U2.EUR.RT.MM.EURIBOR6MD_.HSTA?format=csvdata&startPeriod=2025-01&endPeriod=2025-12",
      euribor_reference_period: "2025",
      euribor_fetched_at: "2026-08-06T14:00:00Z",
      interest_rate_percent: 0,
      interest_from: "2027-08-10",
      interest_start_mode: "fixed_date",
      is_active: false,
      notes: "Nuova nota",
    });

    fireEvent.change(modal.getByPlaceholderText("Nome, es. Ruoli morosi 2024"), { target: { value: "Policy nuova" } });
    fireEvent.click(modal.getByRole("button", { name: "Aggiungi" }));
    await waitFor(() => expect(mocks.createTributiCalculationPolicy).toHaveBeenCalled());

    fireEvent.click(modal.getByRole("button", { name: "Modifica" }));
    fireEvent.click(modal.getByRole("button", { name: "Annulla" }));
    fireEvent.click(modal.getByRole("button", { name: "Elimina" }));
    await waitFor(() => expect(mocks.deleteTributiCalculationPolicy).toHaveBeenCalledWith("token", "policy-gaia-2024"));
    fireEvent.click(modal.getByRole("button", { name: "Chiudi" }));
    expect(screen.queryByText("Scadenza bonaria, maggiorazioni e interessi")).not.toBeInTheDocument();
  });

  test("updates a single annuality calculation policy with shared date fields", async () => {
    mocks.listTributiCalculationPolicies.mockResolvedValueOnce({
      items: [{ ...calculationPolicies[0], year_to: 2024, interest_from: null }],
    });
    render(<RuoloTributiPage />);

    expect(await screen.findByText("Regole ruolo")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Gestisci regole calcolo" }));

    const dialog = screen.getByText("Scadenza bonaria, maggiorazioni e interessi").closest("div")?.parentElement?.parentElement;
    expect(dialog).not.toBeNull();
    const modal = within(dialog as HTMLElement);
    fireEvent.click(await modal.findByRole("button", { name: "Modifica" }));

    expect(modal.queryByText("Date per annualita")).not.toBeInTheDocument();
    fireEvent.change(modal.getByLabelText("Scadenza pagamento bonario"), { target: { value: "2026-07-31" } });
    fireEvent.change(modal.getByLabelText("Fallback/minimo interessi"), { target: { value: "2026-08-10" } });
    fireEvent.click(modal.getByRole("button", { name: "Aggiorna" }));

    await waitFor(() => {
      expect(mocks.updateTributiCalculationPolicy).toHaveBeenCalledWith(
        "token",
        "policy-gaia-2024",
        expect.objectContaining({
          year_from: 2024,
          year_to: 2024,
          bonario_due_date: "2026-07-31",
          interest_from: "2026-08-10",
        }),
      );
    });
  });

  test("handles Euribor fetch validation and errors", async () => {
    render(<RuoloTributiPage />);

    expect(await screen.findByText("Regole ruolo")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Gestisci regole calcolo" }));

    const dialog = screen.getByText("Scadenza bonaria, maggiorazioni e interessi").closest("div")?.parentElement?.parentElement;
    expect(dialog).not.toBeNull();
    const modal = within(dialog as HTMLElement);
    fireEvent.click(await modal.findByRole("button", { name: "Modifica" }));

    fireEvent.change(modal.getByPlaceholderText("Anno da"), { target: { value: "" } });
    fireEvent.click(modal.getByRole("button", { name: "Recupera da BCE" }));
    expect(await screen.findByText("Inserisci prima l'anno della regola per recuperare l'Euribor BCE.")).toBeInTheDocument();

    mocks.fetchTributiEuribor6mRate.mockRejectedValueOnce(new Error("BCE non disponibile"));
    fireEvent.change(modal.getByPlaceholderText("Anno da"), { target: { value: "2025" } });
    fireEvent.click(modal.getByRole("button", { name: "Recupera da BCE" }));
    expect(await screen.findByText("BCE non disponibile")).toBeInTheDocument();

    mocks.fetchTributiEuribor6mRate.mockRejectedValueOnce("boom");
    fireEvent.click(modal.getByRole("button", { name: "Recupera da BCE" }));
    expect(await screen.findByText("Errore recupero Euribor BCE")).toBeInTheDocument();

    fireEvent.change(modal.getByPlaceholderText("es. 3,25"), { target: { value: "2,75" } });
    expect(modal.getByPlaceholderText("es. 3,25")).toHaveValue("2,75");
  });

  test("renders calculation policies without Euribor metadata", async () => {
    mocks.listTributiCalculationPolicies.mockResolvedValueOnce({
      items: [
        {
          ...calculationPolicies[0],
          id: "policy-no-euribor",
          euribor_source_url: null,
          euribor_reference_period: null,
          euribor_fetched_at: null,
        },
      ],
    });
    render(<RuoloTributiPage />);

    expect(await screen.findByText("Regole ruolo")).toBeInTheDocument();
    expect(screen.queryByText("Verifica BCE")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Gestisci regole calcolo" }));

    const dialog = screen.getByText("Scadenza bonaria, maggiorazioni e interessi").closest("div")?.parentElement?.parentElement;
    expect(dialog).not.toBeNull();
    const modal = within(dialog as HTMLElement);
    fireEvent.click(await modal.findByRole("button", { name: "Modifica" }));
    expect(modal.queryByText("verifica il dato BCE")).not.toBeInTheDocument();
  });

  test("renders Euribor source link with missing reference period fallback", async () => {
    mocks.listTributiCalculationPolicies.mockResolvedValueOnce({
      items: [
        {
          ...calculationPolicies[0],
          id: "policy-euribor-no-period",
          euribor_reference_period: null,
        },
      ],
    });
    render(<RuoloTributiPage />);

    expect(await screen.findByText("Regole ruolo")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Gestisci regole calcolo" }));

    const dialog = screen.getByText("Scadenza bonaria, maggiorazioni e interessi").closest("div")?.parentElement?.parentElement;
    expect(dialog).not.toBeNull();
    const modal = within(dialog as HTMLElement);
    fireEvent.click(await modal.findByRole("button", { name: "Modifica" }));
    expect(await modal.findByText(/Fonte -:/)).toBeInTheDocument();
  });

  test("creates one calculation policy per annuality when a closed range has multiple bonario due dates", async () => {
    render(<RuoloTributiPage />);

    expect(await screen.findByText("Regole ruolo")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Gestisci regole calcolo" }));

    const dialog = screen.getByText("Scadenza bonaria, maggiorazioni e interessi").closest("div")?.parentElement?.parentElement;
    expect(dialog).not.toBeNull();
    const modal = within(dialog as HTMLElement);

    fireEvent.change(modal.getByPlaceholderText("Nome, es. Ruoli morosi 2024"), { target: { value: "Ruoli bonari" } });
    fireEvent.change(modal.getByPlaceholderText("Anno da"), { target: { value: "2024" } });
    fireEvent.change(modal.getByPlaceholderText("Anno a"), { target: { value: "2025" } });
    expect(await modal.findByText("Date per annualita")).toBeInTheDocument();
    fireEvent.change(modal.getByLabelText("Scadenza pagamento bonario 2024"), { target: { value: "2026-07-31" } });
    fireEvent.change(modal.getByLabelText("Scadenza pagamento bonario 2025"), { target: { value: "2027-07-31" } });
    fireEvent.change(modal.getByLabelText("Fallback/minimo interessi 2024"), { target: { value: "2026-08-10" } });
    fireEvent.change(modal.getByLabelText("Fallback/minimo interessi 2025"), { target: { value: "2027-08-10" } });
    fireEvent.click(modal.getByRole("button", { name: "Aggiungi" }));

    await waitFor(() => expect(mocks.createTributiCalculationPolicy).toHaveBeenCalledTimes(2));
    expect(mocks.createTributiCalculationPolicy).toHaveBeenNthCalledWith(1, "token", {
      name: "Ruoli bonari 2024",
      year_from: 2024,
      year_to: 2024,
      bonario_due_date: "2026-07-31",
      surcharge_rate_percent: 0,
      surcharge_from: null,
      euribor_6m_rate_percent: 0,
      euribor_source_url: null,
      euribor_reference_period: null,
      euribor_fetched_at: null,
      interest_rate_percent: 0,
      interest_from: "2026-08-10",
      interest_start_mode: "notification_date",
      is_active: true,
      notes: null,
    });
    expect(mocks.createTributiCalculationPolicy).toHaveBeenNthCalledWith(2, "token", {
      name: "Ruoli bonari 2025",
      year_from: 2025,
      year_to: 2025,
      bonario_due_date: "2027-07-31",
      surcharge_rate_percent: 0,
      surcharge_from: null,
      euribor_6m_rate_percent: 0,
      euribor_source_url: null,
      euribor_reference_period: null,
      euribor_fetched_at: null,
      interest_rate_percent: 0,
      interest_from: "2027-08-10",
      interest_start_mode: "notification_date",
      is_active: true,
      notes: null,
    });
  });

  test("shows rules read-only for non admin users", async () => {
    mocks.getCurrentUser.mockResolvedValueOnce(buildCurrentUser({ role: "viewer", username: "viewer" }));
    render(<RuoloTributiPage />);

    expect(await screen.findByText("Maggiorazioni ruoli GAIA")).toBeInTheDocument();
    expect(await screen.findByText("Gestori annualita tributo")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Gestisci regole" })).toBeDisabled());
    expect(screen.getByRole("button", { name: "Gestisci regole calcolo" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Gestisci regole" }));
    fireEvent.click(screen.getByRole("button", { name: "Gestisci regole calcolo" }));

    expect(screen.queryByText("Configura competenza e policy calcolo")).not.toBeInTheDocument();
    expect(screen.queryByText("Scadenza bonaria, maggiorazioni e interessi")).not.toBeInTheDocument();
  });

  test("keeps rules read-only when current user loading fails", async () => {
    mocks.getCurrentUser.mockRejectedValueOnce(new Error("Sessione non disponibile"));
    render(<RuoloTributiPage />);

    expect(await screen.findByText("Maggiorazioni ruoli GAIA")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Gestisci regole calcolo" })).toBeDisabled());
    expect(screen.getByRole("button", { name: "Gestisci regole" })).toBeDisabled();
  });

  test("ignores late current user failures after unmount", async () => {
    let rejectCurrentUser: (error: Error) => void = () => undefined;
    const currentUserPromise = new Promise<CurrentUser>((_resolve, reject) => {
      rejectCurrentUser = reject;
    });
    mocks.getCurrentUser.mockReturnValueOnce(currentUserPromise);
    const rendered = render(<RuoloTributiPage />);

    await waitFor(() => expect(mocks.getCurrentUser).toHaveBeenCalledWith("token"));
    rendered.unmount();

    await act(async () => {
      rejectCurrentUser(new Error("Sessione scaduta"));
      await currentUserPromise.catch(() => undefined);
    });
  });

  test("renders calculation policy loading error branch", async () => {
    mocks.listTributiCalculationPolicies.mockRejectedValueOnce("boom");
    render(<RuoloTributiPage />);

    expect(await screen.findByText("Errore caricamento regole ruolo")).toBeInTheDocument();
  });

  test("renders calculation policy Error messages", async () => {
    mocks.listTributiCalculationPolicies.mockRejectedValueOnce(new Error("Policy non disponibili"));
    render(<RuoloTributiPage />);

    expect(await screen.findByText("Policy non disponibili")).toBeInTheDocument();
  });

  test("renders open range annualities for calculation policies", async () => {
    mocks.listTributiCalculationPolicies.mockResolvedValueOnce({
      items: [{ ...calculationPolicies[0], id: "policy-gaia-open", year_to: null }],
    });
    render(<RuoloTributiPage />);

    expect(await screen.findByText("Maggiorazioni ruoli GAIA")).toBeInTheDocument();
    expect(screen.getByText("Annualita dal 2024")).toBeInTheDocument();
  });

  test("renders annuality manager compact summary edge states", async () => {
    mocks.listTributiYearManagers.mockResolvedValueOnce({ items: [] });
    const emptyManagersRender = render(<RuoloTributiPage />);
    expect(await screen.findByText("Nessuna regola attiva")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Gestisci regole" }));
    expect(await screen.findByText("Nessuna regola configurata.")).toBeInTheDocument();
    emptyManagersRender.unmount();

    mocks.listTributiYearManagers.mockResolvedValueOnce({
      items: [
        ...yearManagers,
        {
          ...yearManagers[1],
          id: "manager-extra-1",
          manager_key: "extra_1",
          manager_label: "Extra 1",
          year_from: 2026,
          year_to: 2026,
        },
        {
          ...yearManagers[1],
          id: "manager-extra-2",
          manager_key: "extra_2",
          manager_label: "Extra 2",
          year_from: 2027,
          year_to: 2027,
        },
      ],
    });
    render(<RuoloTributiPage />);
    expect(await screen.findByText("+1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "2026 · Extra 1" }));
    expect(screen.getByRole("button", { name: "2026 · Extra 1" })).toHaveClass("bg-[#1D4E35]");
  });

  test("renders raccomandata hints when archive source is available", async () => {
    mocks.getTributiSummary.mockResolvedValueOnce({
      ...tributiSummary,
      raccomandata_count: 2,
      raccomandata_amount: 75,
      raccomandata_source_available: true,
    });

    render(<RuoloTributiPage />);

    expect(await screen.findByText("Via raccomandata")).toBeInTheDocument();
    expect(screen.getByText("Avvisi tracciati da archivio raccomandate")).toBeInTheDocument();
    expect(screen.getByText("75,00 €")).toBeInTheDocument();
    expect(screen.getByText("2 avvisi inviati via raccomandata")).toBeInTheDocument();
  });

  test("loads detail and submits payment, status and note", async () => {
    render(<RuoloTributiPage />);

    fireEvent.click(await screen.findByText("ROSSI MARIO"));
    expect(await screen.findByText("Registra pagamento")).toBeInTheDocument();
    expect(screen.getAllByText(/CNC 020210002922120/).length).toBeGreaterThan(0);
    expect(screen.getByText("Utente contattato")).toBeInTheDocument();
    expect(screen.getByText("Dettaglio tributo")).toBeInTheDocument();
    expect(screen.getByText("rossi.mario@pec.example.it")).toBeInTheDocument();
    expect(screen.getByText("17/12/2021 20:01:58")).toBeInTheDocument();
    expect(screen.getByText("Rateizzazione visibile in GAIA")).toBeInTheDocument();
    expect(screen.getByText("Costo rateizzazione").closest("div")).toHaveTextContent("3,00 €");
    expect(screen.getByText("Versato utenza").closest("div")).toHaveTextContent("40,00 €");
    const positionCard = screen.getByText("Anagrafica, collegamenti e riferimenti esterni").closest("article");
    expect(positionCard).not.toBeNull();
    expect(within(positionCard!).getByText("CF/P.IVA")).toBeInTheDocument();
    expect(within(positionCard!).getByText("RSSMRA80A01H501Z")).toBeInTheDocument();
    expect(
      screen
        .getAllByRole("link", { name: "Apri CapaciTas" })
        .some((link) => link.getAttribute("href") === "https://incass3.servizicapacitas.com/pages/dettaglioAvviso.aspx?avviso=1"),
    ).toBe(true);
    expect(screen.getByRole("link", { name: "Apri link CapaciTas" })).toHaveAttribute(
      "href",
      "https://incass3.servizicapacitas.com/pages/dettaglioAvviso.aspx?avviso=1",
    );

    fireEvent.change(screen.getByPlaceholderText("Importo"), { target: { value: "60" } });
    fireEvent.change(screen.getByPlaceholderText("Riferimento"), { target: { value: "PAY-002" } });
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

    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    expect(screen.queryByText("Dettaglio tributo")).not.toBeInTheDocument();
  });

  test("queues a punctual inCASS sync from the detail modal for the linked subject", async () => {
    mocks.getTributiAvviso.mockResolvedValueOnce({
      ...detail,
      subject_id: "subject-1",
      is_linked: true,
    });

    render(<RuoloTributiPage />);

    fireEvent.click(await screen.findByText("ROSSI MARIO"));
    fireEvent.click(await screen.findByRole("button", { name: "Accoda sync inCASS" }));

    await waitFor(() => {
      expect(mocks.createCapacitasInCassSyncJob).toHaveBeenCalledWith("token", {
        subject_ids: ["subject-1"],
        include_details: true,
        include_partitario: true,
        include_mailing_list: false,
        download_mailing_receipts: false,
        continue_on_error: true,
        throttle_ms: 250,
      });
    });
    expect(await screen.findByText("Sync inCASS puntuale accodata sul soggetto collegato. Job #88.")).toBeInTheDocument();
  });

  test("omits the rateization insight when the inCASS notice is not rateized", async () => {
    mocks.getTributiAvviso.mockResolvedValueOnce({
      ...detail,
      incass_notice: {
        ...detail.incass_notice,
        importo_rateizzato: null,
      },
    });

    render(<RuoloTributiPage />);

    fireEvent.click(await screen.findByText("ROSSI MARIO"));

    expect(await screen.findByText("Registra pagamento")).toBeInTheDocument();
    expect(screen.queryByText("Rateizzazione visibile in GAIA")).not.toBeInTheDocument();
  });

  test("renders rateization insight fallbacks when optional inCASS fields are missing", async () => {
    mocks.getTributiAvviso.mockResolvedValueOnce({
      ...detail,
      capacitas_avviso_code: null,
      incass_notice: {
        ...detail.incass_notice,
        source_notice_id: null,
        stato_label: null,
        importo_carico: null,
        importo_riscosso: null,
        importo_residuo: "0,00",
        rateization_fee_amount: null,
      },
    });

    render(<RuoloTributiPage />);

    fireEvent.click(await screen.findByText("ROSSI MARIO"));

    expect(await screen.findByText("Rateizzazione visibile in GAIA")).toBeInTheDocument();
    expect(screen.getByText(/CNC CNC-001/)).toBeInTheDocument();
    expect(screen.getByText("Avviso -")).toBeInTheDocument();
    expect(screen.getByText("Costo rateizzazione").closest("div")).toHaveTextContent("-");
    expect(screen.getByText("Versato utenza").closest("div")).toHaveTextContent("-");
    expect(screen.getByText("Residuo inCASS").closest("div")).toHaveTextContent("0,00 €");
  });

  test("calculates rateization fee and handles missing residual amount", async () => {
    mocks.getTributiAvviso.mockResolvedValueOnce({
      ...detail,
      incass_notice: {
        ...detail.incass_notice,
        importo_carico: "100,00",
        importo_residuo: null,
        rateization_fee_amount: null,
      },
    });

    render(<RuoloTributiPage />);

    fireEvent.click(await screen.findByText("ROSSI MARIO"));

    expect(await screen.findByText("Rateizzazione visibile in GAIA")).toBeInTheDocument();
    expect(screen.getByText("Costo rateizzazione").closest("div")).toHaveTextContent("3,00 €");
    expect(screen.getByText("Residuo inCASS").closest("div")).toHaveTextContent("-");
  });

  test("keeps the inCASS modal action safe without subject and surfaces queue errors", async () => {
    const unlinkedRender = render(<RuoloTributiPage />);

    fireEvent.click(await screen.findByText("ROSSI MARIO"));
    fireEvent.click(await screen.findByRole("button", { name: "Accoda sync inCASS" }));

    expect(await screen.findByText("Avviso non collegato a un soggetto GAIA: impossibile accodare una sync inCASS puntuale.")).toBeInTheDocument();
    expect(mocks.createCapacitasInCassSyncJob).not.toHaveBeenCalled();
    unlinkedRender.unmount();

    mocks.getTributiAvviso.mockResolvedValueOnce({
      ...detail,
      subject_id: "subject-1",
      is_linked: true,
    });
    mocks.createCapacitasInCassSyncJob.mockRejectedValueOnce(new Error("Queue down"));

    render(<RuoloTributiPage />);

    fireEvent.click(await screen.findByText("ROSSI MARIO"));
    fireEvent.click(await screen.findByRole("button", { name: "Accoda sync inCASS" }));

    expect(await screen.findByText("Queue down")).toBeInTheDocument();
  });

  test("shows the generic inCASS modal queue error for non-Error failures", async () => {
    mocks.getTributiAvviso.mockResolvedValueOnce({
      ...detail,
      subject_id: "subject-1",
      is_linked: true,
    });
    mocks.createCapacitasInCassSyncJob.mockRejectedValueOnce("boom");

    render(<RuoloTributiPage />);

    fireEvent.click(await screen.findByText("ROSSI MARIO"));
    fireEvent.click(await screen.findByRole("button", { name: "Accoda sync inCASS" }));

    expect(await screen.findByText("Errore accodamento sync inCASS")).toBeInTheDocument();
  });

  test("opens reminder wizard, supports manual selection and generates batch", async () => {
    render(<RuoloTributiPage />);

    fireEvent.click(await screen.findByRole("button", { name: "Wizard solleciti" }));

    expect(await screen.findByText("Crea batch PDF per utenze morose")).toBeInTheDocument();
    expect(await screen.findByText(/1 utenze aperte trovate/)).toBeInTheDocument();
    expect(screen.getAllByText(/CF\/P.IVA RSSMRA80A01H501Z/).length).toBeGreaterThan(0);
    await waitFor(() => expect(mocks.listTributiReminderCandidates).toHaveBeenCalledTimes(2));
    expect(mocks.listTributiReminderCandidates).toHaveBeenCalledWith(
      "token",
      expect.objectContaining({ anno_from: 2024, anno_to: 2024, page: 1, page_size: 80 }),
    );
    expect(mocks.listTributiReminderCandidates).toHaveBeenCalledWith(
      "token",
      expect.objectContaining({ anno_from: 2025, anno_to: 2025, page: 1, page_size: 80 }),
    );

    fireEvent.change(screen.getByPlaceholderText("Codice fiscale"), { target: { value: "bnclgu80a01h501y" } });
    fireEvent.click(within(screen.getByPlaceholderText("Codice fiscale").closest("div")!).getByRole("button", { name: "Aggiungi" }));

    fireEvent.click(screen.getByRole("button", { name: "Avanti" }));
    expect(await screen.findByText("Conferma generazione di 2 solleciti")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Genera PDF nel NAS" }));
    await waitFor(() => {
      expect(mocks.createTributiReminderBatch).toHaveBeenCalledWith(
        "token",
        expect.objectContaining({
          codice_fiscale: ["RSSMRA80A01H501Z", "BNCLGU80A01H501Y"],
          filters: expect.objectContaining({ years: [2024, 2025], anno_from: 2024, anno_to: 2025 }),
          template_path: "__gaia_proposal__",
        }),
      );
    });

    expect(await screen.findByText("1 PDF generati, 0 errori")).toBeInTheDocument();
    expect(screen.getByText(/Avviso 12026242500001/)).toBeInTheDocument();
    expect(screen.getByText(/RSSMRA80A01H501Z_avviso_sollecito_2024-2025.pdf/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi wizard" }));
    expect(screen.queryByText("Crea batch PDF per utenze morose")).not.toBeInTheDocument();
  });

  test("sorts reminder candidates and handles generation without selected years", async () => {
    const zetaFirst = {
      ...reminderCandidate2024,
      codice_fiscale: "ZZZAAA80A01H501Z",
      display_name: null,
      years: [2025, 2024],
      avvisi_count: 2,
      due_amount: null,
      saldo_amount: null,
      subject_id: null,
      annuality_managers: ["Zeta", "Alfa"],
      avvisi: [
        { ...reminderCandidate2025.avvisi[0], id: "zeta-2025", anno_tributario: 2025 },
        { ...reminderCandidate2024.avvisi[0], id: "zeta-2024", anno_tributario: 2024 },
      ],
    };
    const zetaSecond = {
      ...zetaFirst,
      display_name: "ZETA SPA",
      subject_id: "subject-zeta",
      years: [2026],
      avvisi: [{ ...reminderCandidate2025.avvisi[0], id: "zeta-2026", anno_tributario: 2026 }],
    };
    const alfa = {
      ...reminderCandidate2025,
      codice_fiscale: "AAAALF80A01H501Z",
      display_name: "ALFA SRL",
      years: [2025],
      avvisi: [{ ...reminderCandidate2025.avvisi[0], id: "alfa-2025", anno_tributario: 2025 }],
    };
    const unnamedFirst = {
      ...reminderCandidate2025,
      codice_fiscale: "BBBNULL80A01H501Z",
      display_name: null,
      due_amount: null,
      saldo_amount: null,
      years: [2025],
      avvisi: [{ ...reminderCandidate2025.avvisi[0], id: "unnamed-b", anno_tributario: 2025 }],
    };
    const unnamedSecond = {
      ...unnamedFirst,
      codice_fiscale: "CCCNULL80A01H501Z",
      avvisi: [{ ...reminderCandidate2025.avvisi[0], id: "unnamed-c", anno_tributario: 2025 }],
    };
    mocks.listTributiReminderCandidates
      .mockResolvedValueOnce({ items: [zetaFirst, alfa, unnamedSecond, unnamedFirst], total: 4, page: 1, page_size: 80 })
      .mockResolvedValueOnce({ items: [zetaSecond], total: 1, page: 1, page_size: 80 });

    render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Wizard solleciti" }));

    expect(await screen.findByText("ALFA SRL")).toBeInTheDocument();
    expect(screen.getByText("ZETA SPA")).toBeInTheDocument();
    expect(screen.getByText("BBBNULL80A01H501Z")).toBeInTheDocument();
    expect(screen.getByText("CCCNULL80A01H501Z")).toBeInTheDocument();
    expect(screen.getByText(/CF\/P\.IVA ZZZAAA80A01H501Z .* anni 2024, 2025, 2026/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Avanti" }));
    expect(await screen.findByText("Conferma generazione di 4 solleciti")).toBeInTheDocument();
    expect(screen.getByText("Dovuto selezione")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Torna alla selezione" }));
    expect(await screen.findByText("Utenze candidabili")).toBeInTheDocument();

    const year2024Button = screen.getByRole("button", { name: "2024" });
    const year2025Button = screen.getByRole("button", { name: "2025" });
    fireEvent.click(year2024Button);
    await waitFor(() => expect(year2024Button).toHaveAttribute("aria-pressed", "false"));
    fireEvent.click(year2024Button);
    await waitFor(() => expect(year2024Button).toHaveAttribute("aria-pressed", "true"));
    fireEvent.click(year2024Button);
    await waitFor(() => expect(year2024Button).toHaveAttribute("aria-pressed", "false"));
    fireEvent.click(year2025Button);
    await waitFor(() => expect(year2025Button).toHaveAttribute("aria-pressed", "false"));
    await waitFor(() => expect(screen.getByText("Nessuna utenza sollecitabile")).toBeInTheDocument());
    fireEvent.change(screen.getByPlaceholderText("Codice fiscale"), { target: { value: "manuale01h501z" } });
    fireEvent.click(within(screen.getByPlaceholderText("Codice fiscale").closest("div")!).getByRole("button", { name: "Aggiungi" }));
    fireEvent.click(screen.getByRole("button", { name: "Avanti" }));
    expect(await screen.findByText("Conferma generazione di 1 solleciti")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Genera PDF nel NAS" }));
    expect(await screen.findByText("Seleziona almeno una annualita da includere nel nuovo avviso.")).toBeInTheDocument();
  });

  test("generates a reminder preview from list rows and detail modal", async () => {
    render(<RuoloTributiPage />);

    fireEvent.click(await screen.findByRole("button", { name: "Avviso sollecito" }));

    await waitFor(() => {
      expect(mocks.createTributiReminderBatch).toHaveBeenCalledWith(
        "token",
        expect.objectContaining({
          codice_fiscale: ["RSSMRA80A01H501Z"],
          filters: { anno_from: 2024, anno_to: 2024, years: [2024], codice_fiscale: ["RSSMRA80A01H501Z"], preview_only: true, policy_group: true },
          template_path: "__gaia_proposal__",
        }),
      );
      expect(mocks.downloadTributiReminderDocument).toHaveBeenCalledWith("token", "/ruolo/tributi/solleciti/items/item-1/download");
    });
    expect(mocks.createTributiReminderBatch.mock.calls.map(([, payload]) => payload.template_path)).toEqual(["__gaia_proposal__"]);
    expect(await screen.findByText("Preview avviso sollecito")).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Template GAIA" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Template legacy" })).not.toBeInTheDocument();
    expect(screen.queryByText("Template legacy")).not.toBeInTheDocument();
    expect(screen.getByTitle("Preview PDF avviso sollecito")).toHaveAttribute("src", "blob:sollecito-preview#toolbar=0&navpanes=0&zoom=125");
    expect(screen.getByRole("link", { name: "Scarica PDF" })).toHaveAttribute("href", "blob:sollecito-preview");
    expect(screen.getByRole("link", { name: "Scarica PDF" })).toHaveAttribute("download", "RSSMRA80A01H501Z_avviso_sollecito_2024-2025.pdf");

    fireEvent.click(screen.getAllByRole("button", { name: "Avviso sollecito" })[0]);
    await waitFor(() => expect(mocks.createTributiReminderBatch).toHaveBeenCalledTimes(2));

    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    await waitFor(() => expect(screen.queryByText("Preview avviso sollecito")).not.toBeInTheDocument());
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:sollecito-preview");

    fireEvent.click(screen.getByRole("button", { name: "Dettaglio" }));
    expect(await screen.findByText("Registra pagamento")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Genera o riapri preview" }));
    await waitFor(() => expect(mocks.createTributiReminderBatch).toHaveBeenCalledTimes(3));
    fireEvent.click(screen.getAllByRole("button", { name: "Chiudi" }).at(-1)!);
    fireEvent.click(screen.getByRole("button", { name: "Preview avviso sollecito" }));
    await waitFor(() => expect(mocks.createTributiReminderBatch).toHaveBeenCalledTimes(4));
    fireEvent.click(screen.getAllByRole("button", { name: "Chiudi" }).at(-1)!);

    vi.mocked(URL.createObjectURL).mockReturnValueOnce("blob:sollecito-preview#page=2");
    fireEvent.click(screen.getByRole("button", { name: "Preview avviso sollecito" }));
    await waitFor(() => expect(mocks.createTributiReminderBatch).toHaveBeenCalledTimes(5));
    expect(mocks.createTributiReminderBatch.mock.calls.every(([, payload]) => payload.template_path === "__gaia_proposal__")).toBe(true);
    expect(await screen.findByTitle("Preview PDF avviso sollecito")).toHaveAttribute("src", "blob:sollecito-preview#page=2&toolbar=0&navpanes=0&zoom=125");
  });

  test("scales the reminder PDF preview down on mobile viewports", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 406,
    });

    render(<RuoloTributiPage />);

    fireEvent.click(await screen.findByRole("button", { name: "Avviso sollecito" }));

    expect(await screen.findByTitle("Preview PDF avviso sollecito")).toHaveAttribute("src", "blob:sollecito-preview#toolbar=0&navpanes=0&zoom=60");
  });

  test("shows disabled reminder quick actions for internal annualities without calculation rules", async () => {
    const stepItem: RuoloTributiAvvisoListItemResponse = {
      ...listItem,
      id: "avviso-step",
      anno_tributario: 2021,
      codice_cnc: "CNC-STEP",
      capacitas_avviso_code: null,
      annuality_manager_key: "step",
      annuality_manager_label: "STEP - Agenzia recupero crediti",
      calculation_policy: "external_recovery",
      reminder_enabled: false,
    };
    const missingRuleItem: RuoloTributiAvvisoListItemResponse = {
      ...listItem,
      id: "avviso-no-rule",
      anno_tributario: 2023,
      codice_cnc: "CNC-NO-RULE",
      capacitas_avviso_code: null,
      calculation_policy_id: null,
      calculation_policy_name: null,
      reminder_enabled: false,
    };
    mocks.listTributiAvvisi.mockResolvedValueOnce({ items: [listItem, stepItem, missingRuleItem], total: 3, page: 1, page_size: 25 });

    render(<RuoloTributiPage />);

    expect(await screen.findByText(/CNC CNC-STEP/)).toBeInTheDocument();
    expect(screen.getByText(/CNC CNC-NO-RULE/)).toBeInTheDocument();
    const reminderButtons = screen.getAllByRole("button", { name: "Avviso sollecito" });
    expect(reminderButtons).toHaveLength(2);
    expect(reminderButtons[0]).toBeEnabled();
    expect(reminderButtons[1]).toBeDisabled();
    expect(reminderButtons[1]).toHaveAttribute("title", "Regola ruolo non configurata per questa annualita");
    expect(screen.getAllByRole("button", { name: "Dettaglio" })).toHaveLength(3);

    mocks.getTributiAvviso.mockResolvedValueOnce({ ...detail, ...missingRuleItem });
    fireEvent.click(screen.getAllByRole("button", { name: "Dettaglio" })[2]);
    expect(await screen.findByText("Regola ruolo mancante")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Genera o riapri preview" })).toBeDisabled();
  });

  test("hides reminder actions in detail when the annuality is not enabled", async () => {
    mocks.getTributiAvviso.mockResolvedValueOnce({ ...detail, reminder_enabled: false });

    render(<RuoloTributiPage />);

    fireEvent.click(await screen.findByRole("button", { name: "Dettaglio" }));
    expect(await screen.findByText("Registra pagamento")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Preview avviso sollecito" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Genera o riapri preview" })).not.toBeInTheDocument();
  });

  test("opens the reminder preview modal while documents are still being generated", async () => {
    let resolveFirstBatch: (value: typeof reminderBatch) => void = () => undefined;
    mocks.createTributiReminderBatch.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveFirstBatch = resolve;
        }),
    );

    render(<RuoloTributiPage />);

    fireEvent.click(await screen.findByRole("button", { name: "Avviso sollecito" }));

    expect(await screen.findByText("Creazione preview avviso sollecito...")).toBeInTheDocument();
    expect(screen.getAllByText("ROSSI MARIO").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Chiudi" })).toBeDisabled();

    await act(async () => {
      resolveFirstBatch(reminderBatch);
    });

    expect(await screen.findByRole("link", { name: "Scarica PDF" })).toBeInTheDocument();
  });

  test("uses nominativo and tax code fallback labels while opening reminder previews", async () => {
    async function openPendingPreview(
      item: typeof listItem,
      expectedLabel: string,
    ) {
      let resolveFirstBatch: (value: typeof reminderBatch) => void = () => undefined;
      mocks.listTributiAvvisi.mockResolvedValueOnce({ items: [item], total: 1, page: 1, page_size: 25 });
      mocks.createTributiReminderBatch.mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveFirstBatch = resolve;
          }),
      );

      const view = render(<RuoloTributiPage />);
      fireEvent.click(await screen.findByRole("button", { name: "Avviso sollecito" }));

      expect(await screen.findByText("Creazione preview avviso sollecito...")).toBeInTheDocument();
      expect(screen.getAllByText(expectedLabel).length).toBeGreaterThan(0);

      await act(async () => {
        resolveFirstBatch(reminderBatch);
      });
      expect(await screen.findByRole("link", { name: "Scarica PDF" })).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
      await waitFor(() => expect(screen.queryByText("Preview avviso sollecito")).not.toBeInTheDocument());
      view.unmount();
    }

    await openPendingPreview({ ...listItem, display_name: null }, "ROSSI MARIO");
    await openPendingPreview({ ...listItem, display_name: null, nominativo_raw: null }, "RSSMRA80A01H501Z");
  });

  test("handles reminder preview errors and ISO delivery dates", async () => {
    const deliveredAt = "2026-07-22T10:30:00Z";
    const acceptedAt = "2026-07-22T10:29:00Z";
    const expectedDeliveredAt = new Intl.DateTimeFormat("it-IT", { dateStyle: "short", timeStyle: "short" }).format(new Date(deliveredAt));
    mocks.getTributiAvviso.mockResolvedValueOnce({
      ...detail,
      mailing_delivery: {
        ...detail.mailing_delivery,
        delivered_at: deliveredAt,
        accepted_at: acceptedAt,
      },
    });

    const isoDeliveryRender = render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Dettaglio" }));
    expect(await screen.findByText(expectedDeliveredAt)).toBeInTheDocument();
    isoDeliveryRender.unmount();

    mocks.getTributiAvviso.mockResolvedValueOnce({
      ...detail,
      mailing_delivery: {
        ...detail.mailing_delivery,
        delivered_at: null,
        accepted_at: null,
        receipt_groups: [],
      },
    });
    const emptyDeliveryFieldsRender = render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Dettaglio" }));
    expect(await screen.findByText("Ricevute archiviate")).toBeInTheDocument();
    emptyDeliveryFieldsRender.unmount();

    mocks.getTributiAvviso.mockResolvedValueOnce({
      ...detail,
      surcharge_amount: 3,
      interest_amount: 2,
      mailing_delivery: {
        ...detail.mailing_delivery,
        delivery_status: "",
      },
    });
    const fallbackDeliveryStatusRender = render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Dettaglio" }));
    expect(await screen.findByText("PEC acquisita")).toBeInTheDocument();
    fallbackDeliveryStatusRender.unmount();

    mocks.getTributiAvviso.mockResolvedValueOnce({
      ...detail,
      workflow_status: null,
      is_linked: true,
      subject_id: null,
    });
    const missingWorkflowRender = render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Dettaglio" }));
    expect(await screen.findByText("Serve uno stato operativo")).toBeInTheDocument();
    expect(screen.getByText("La posizione risulta collegata, ma non espone un soggetto apribile da questo pannello.")).toBeInTheDocument();
    missingWorkflowRender.unmount();

    mocks.getTributiAvviso.mockResolvedValueOnce({ ...detail, mailing_delivery: null });
    const missingDeliveryRender = render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Dettaglio" }));
    expect(await screen.findByText("Nessuna ricevuta PEC di consegna collegata all'avviso.")).toBeInTheDocument();
    missingDeliveryRender.unmount();

    mocks.listTributiAvvisi.mockResolvedValueOnce({
      items: [{ ...listItem, codice_fiscale_raw: null, payment_status: "unpaid", saldo_amount: 100 }],
      total: 1,
      page: 1,
      page_size: 25,
    });

    const missingTaxCodeRender = render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Avviso sollecito" }));
    expect(await screen.findByText("Codice fiscale/P.IVA mancante: impossibile predisporre il sollecito.")).toBeInTheDocument();
    missingTaxCodeRender.unmount();

    mocks.createTributiReminderBatch.mockResolvedValueOnce({
      ...reminderBatch,
      items: [{ ...reminderBatch.items[0], display_name: null, generated_document_path: null }],
    });
    mocks.downloadTributiReminderDocument.mockResolvedValueOnce(new Blob(["pdf"]));
    const fallbackFilenameRender = render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Avviso sollecito" }));
    expect(await screen.findByRole("link", { name: "Scarica PDF" })).toHaveAttribute("download", "RSSMRA80A01H501Z_avviso_sollecito.pdf");
    expect(screen.getAllByText("RSSMRA80A01H501Z").length).toBeGreaterThan(0);
    fallbackFilenameRender.unmount();

    mocks.createTributiReminderBatch.mockResolvedValueOnce({
      ...reminderBatch,
      items: [
        {
          ...reminderBatch.items[0],
          status: "generated_docx",
          generated_document_path: "/nas/R/RSSMRA80A01H501Z/solleciti/RSSMRA80A01H501Z_avviso_sollecito_2024-2025.docx",
          error_detail: "LibreOffice non disponibile: generato DOCX scaricabile senza preview PDF",
        },
      ],
    });
    mocks.downloadTributiReminderDocument.mockResolvedValueOnce(
      new Blob(["docx"], { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" }),
    );
    const docxFallbackRender = render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Avviso sollecito" }));
    expect(await screen.findByText("Preview PDF non disponibile")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Scarica DOCX" }).at(0)).toHaveAttribute("download", "RSSMRA80A01H501Z_avviso_sollecito_2024-2025.docx");
    expect(screen.queryByTitle("Preview PDF avviso sollecito")).not.toBeInTheDocument();
    docxFallbackRender.unmount();

    mocks.createTributiReminderBatch.mockResolvedValueOnce({
      ...reminderBatch,
      items: [{ ...reminderBatch.items[0], download_url: null, error_detail: "Cartella NAS mancante" }],
    });
    const failedPreviewRender = render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Avviso sollecito" }));
    expect(await screen.findByText("Cartella NAS mancante")).toBeInTheDocument();
    failedPreviewRender.unmount();

    mocks.createTributiReminderBatch.mockResolvedValueOnce({
      ...reminderBatch,
      items: [{ ...reminderBatch.items[0], download_url: null, error_detail: null }],
    });
    const fallbackPreviewErrorRender = render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Avviso sollecito" }));
    expect(await screen.findByText("PDF sollecito non disponibile per la preview Template GAIA.")).toBeInTheDocument();
    fallbackPreviewErrorRender.unmount();

    mocks.createTributiReminderBatch.mockRejectedValueOnce("boom");
    render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Avviso sollecito" }));
    expect(await screen.findByText("Errore predisposizione avviso di sollecito")).toBeInTheDocument();
  });

  test("handles reminder wizard empty, candidate error and generation error states", async () => {
    mocks.listTributiReminderCandidates.mockRejectedValueOnce(new Error("Candidature non disponibili"));
    const errorRender = render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Wizard solleciti" }));
    expect(await screen.findByText("Candidature non disponibili")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    errorRender.unmount();

    mocks.listTributiReminderCandidates.mockRejectedValueOnce("boom");
    const fallbackErrorRender = render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Wizard solleciti" }));
    expect(await screen.findByText("Errore caricamento utenze sollecitabili")).toBeInTheDocument();
    fallbackErrorRender.unmount();

    mocks.listTributiReminderCandidates
      .mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 80 })
      .mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 80 });
    const emptyRender = render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Wizard solleciti" }));
    expect(await screen.findByText("Nessuna utenza sollecitabile")).toBeInTheDocument();
    fireEvent.click(within(screen.getByPlaceholderText("Codice fiscale").closest("div")!).getByRole("button", { name: "Aggiungi" }));
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    emptyRender.unmount();

    mocks.listTributiReminderCandidates
      .mockResolvedValueOnce({
        items: [{ ...reminderCandidate2024, has_nas_folder: false, nas_folder_path: null, display_name: null, comune: null, due_amount: null, saldo_amount: null, annuality_managers: [] }],
        total: 1,
        page: 1,
        page_size: 80,
      })
      .mockResolvedValueOnce({
        items: [{ ...reminderCandidate2025, has_nas_folder: false, nas_folder_path: null, display_name: null, comune: null, due_amount: null, saldo_amount: null, annuality_managers: [] }],
        total: 1,
        page: 1,
        page_size: 80,
      });
    mocks.createTributiReminderBatch.mockRejectedValueOnce("boom");
    render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Wizard solleciti" }));
    expect(await screen.findByText(/Cartella NAS mancante/)).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(/CF\/P.IVA RSSMRA80A01H501Z/));
    fireEvent.click(screen.getByLabelText(/CF\/P.IVA RSSMRA80A01H501Z/));
    fireEvent.change(screen.getByPlaceholderText("Codice fiscale"), { target: { value: "RSSMRA80A01H501Z" } });
    fireEvent.click(within(screen.getByPlaceholderText("Codice fiscale").closest("div")!).getByRole("button", { name: "Aggiungi" }));
    fireEvent.click(screen.getByRole("button", { name: "Avanti" }));
    expect(await screen.findByText("Conferma generazione di 1 solleciti")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Torna alla selezione" }));
    fireEvent.click(screen.getByRole("button", { name: "Avanti" }));
    fireEvent.click(screen.getByRole("button", { name: "Genera PDF nel NAS" }));
    expect(await screen.findByText("Errore generazione batch solleciti")).toBeInTheDocument();
  });

  test("covers reminder wizard branch variants for filters and failed result items", async () => {
    mocks.searchParams = new URLSearchParams("q=Rossi&anno=2024&comune=Uras");
    mocks.createTributiReminderBatch
      .mockRejectedValueOnce(new Error("Generazione non disponibile"))
      .mockResolvedValueOnce({
        ...reminderBatch,
        items_generated: 0,
        items_failed: 1,
        items: [
          {
            ...reminderBatch.items[0],
            display_name: null,
            generated_document_path: null,
            status: "failed",
            error_detail: null,
            payload_json: null,
          },
        ],
      });

    render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Wizard solleciti" }));
    await screen.findByText(/1 utenze aperte trovate/);
    await waitFor(() => expect(mocks.listTributiReminderCandidates).toHaveBeenCalledTimes(2));
    expect(mocks.listTributiReminderCandidates).toHaveBeenCalledWith(
      "token",
      expect.objectContaining({ anno_from: 2024, anno_to: 2024, q: "Rossi", comune: "Uras" }),
    );
    expect(mocks.listTributiReminderCandidates).toHaveBeenCalledWith(
      "token",
      expect.objectContaining({ anno_from: 2025, anno_to: 2025, q: "Rossi", comune: "Uras" }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    fireEvent.click(screen.getByRole("button", { name: "Wizard solleciti" }));
    await waitFor(() => expect(mocks.listTributiReminderCandidates).toHaveBeenCalledTimes(4));

    fireEvent.change(screen.getByPlaceholderText("Codice fiscale"), { target: { value: "RSSMRA80A01H501Z" } });
    fireEvent.click(within(screen.getByPlaceholderText("Codice fiscale").closest("div")!).getByRole("button", { name: "Aggiungi" }));
    fireEvent.change(screen.getByPlaceholderText("Codice fiscale"), { target: { value: "RSSMRA80A01H501Z" } });
    fireEvent.click(within(screen.getByPlaceholderText("Codice fiscale").closest("div")!).getByRole("button", { name: "Aggiungi" }));
    fireEvent.click(screen.getByRole("button", { name: "Avanti" }));

    fireEvent.click(screen.getByRole("button", { name: "Genera PDF nel NAS" }));
    expect(await screen.findByText("Generazione non disponibile")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Genera PDF nel NAS" }));
    expect(await screen.findByText("0 PDF generati, 1 errori")).toBeInTheDocument();
    expect(screen.getByText("In attesa")).toBeInTheDocument();
  });

  test("renders empty and loading/error states", async () => {
    mocks.listTributiAvvisi.mockReturnValue(new Promise(() => undefined));
    const { unmount } = render(<RuoloTributiPage />);
    expect(await screen.findByText("Caricamento tributi...")).toBeInTheDocument();
    unmount();

    mocks.listTributiAvvisi.mockResolvedValueOnce({ items: [listItem], total: 1, page: 1, page_size: 25 });
    mocks.getTributiSummary.mockReturnValueOnce(new Promise(() => undefined));
    const slowSummaryRender = render(<RuoloTributiPage />);
    expect(await screen.findByText("ROSSI MARIO")).toBeInTheDocument();
    expect(screen.queryByText("Caricamento tributi...")).not.toBeInTheDocument();
    slowSummaryRender.unmount();

    mocks.listTributiAvvisi.mockResolvedValueOnce({ items: [listItem], total: 1, page: 1, page_size: 25 });
    mocks.getTributiSummary.mockRejectedValueOnce(new Error("Summary lenta"));
    const summaryErrorRender = render(<RuoloTributiPage />);
    expect(await screen.findByText("ROSSI MARIO")).toBeInTheDocument();
    expect(screen.queryByText("Summary lenta")).not.toBeInTheDocument();
    summaryErrorRender.unmount();

    let resolveSummary: (value: typeof tributiSummary) => void = () => {};
    const cancellableSummary = new Promise<typeof tributiSummary>((resolve) => {
      resolveSummary = resolve;
    });
    mocks.listTributiAvvisi.mockResolvedValueOnce({ items: [listItem], total: 1, page: 1, page_size: 25 });
    mocks.getTributiSummary.mockReturnValueOnce(cancellableSummary);
    const cancellableSummaryRender = render(<RuoloTributiPage />);
    expect(await screen.findByText("ROSSI MARIO")).toBeInTheDocument();
    cancellableSummaryRender.unmount();
    await act(async () => {
      resolveSummary(tributiSummary);
      await cancellableSummary;
    });

    let resolveList: (value: { items: (typeof listItem)[]; total: number; page: number; page_size: number }) => void = () => {};
    const cancellableList = new Promise<{ items: (typeof listItem)[]; total: number; page: number; page_size: number }>((resolve) => {
      resolveList = resolve;
    });
    mocks.listTributiAvvisi.mockReturnValueOnce(cancellableList);
    const cancellableListRender = render(<RuoloTributiPage />);
    cancellableListRender.unmount();
    await act(async () => {
      resolveList({ items: [listItem], total: 1, page: 1, page_size: 25 });
      await cancellableList;
    });

    let rejectList: (reason: Error) => void = () => {};
    const rejectableList = new Promise<{ items: (typeof listItem)[]; total: number; page: number; page_size: number }>((_resolve, reject) => {
      rejectList = reject;
    });
    mocks.listTributiAvvisi.mockReturnValueOnce(rejectableList);
    const rejectableListRender = render(<RuoloTributiPage />);
    rejectableListRender.unmount();
    await act(async () => {
      rejectList(new Error("Unmounted"));
      await rejectableList.catch(() => undefined);
    });

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
        { ...listItem, id: "paid", subject_id: "subject-paid", payment_status: "paid", workflow_status: null, saldo_amount: 0, paid_amount: 100, is_linked: true },
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
          annuality_manager_key: null,
          annuality_manager_label: null,
          calculation_policy: null,
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
    const subjectButtons = screen.getAllByRole("button", { name: "Dettaglio soggetto" });
    const enabledSubjectButton = subjectButtons.find((button) => !button.hasAttribute("disabled"));
    expect(enabledSubjectButton).toBeDefined();
    expect(subjectButtons.some((button) => button.hasAttribute("disabled"))).toBe(true);
    fireEvent.click(enabledSubjectButton!);
    expect(await screen.findByTitle("Dettaglio soggetto ROSSI MARIO")).toHaveAttribute("src", "/utenze/subject-paid?embedded=1");
    expect(screen.getByRole("link", { name: "Apri pagina" })).toHaveAttribute("href", "/utenze/subject-paid");
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));

    const comboboxes = screen.getAllByRole("combobox");
    fireEvent.change(comboboxes[0], { target: { value: "paid" } });
    fireEvent.change(comboboxes[1], { target: { value: "moroso" } });
    fireEvent.click(screen.getByLabelText("Solo scoperti"));
    fireEvent.click(screen.getByLabelText("Solo scoperti"));
    fireEvent.click(screen.getByLabelText("Non collegati"));
    fireEvent.click(screen.getByLabelText("Non collegati"));

    await waitFor(() => {
      expect(mocks.replace).toHaveBeenCalledWith(expect.stringContaining("payment_status=paid"));
      expect(mocks.replace).toHaveBeenCalledWith(expect.stringContaining("workflow_status=moroso"));
      expect(mocks.replace).toHaveBeenCalledWith(expect.stringContaining("open_only=false"));
      expect(mocks.replace).toHaveBeenCalledWith(expect.stringContaining("unlinked=true"));
    });

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
      subject_id: "subject-linked",
      codice_fiscale_raw: null,
      codice_utenza: null,
      saldo_amount: null,
      is_linked: true,
      workflow_status: null,
      capacitas_url: null,
      capacitas_avviso_code: null,
      annuality_manager_key: null,
      annuality_manager_label: null,
      calculation_policy: null,
      payments: [],
      notes: [],
    });
    render(<RuoloTributiPage />);
    fireEvent.click(await screen.findByText("ROSSI MARIO"));

    expect(await screen.findByText("Avviso selezionato")).toBeInTheDocument();
    expect(screen.getByText(/Utenza - · CF\/P.IVA -/)).toBeInTheDocument();
    expect(screen.getByText("Collegato")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Dettaglio soggetto" }).find((button) => !button.hasAttribute("disabled"))!);
    expect(await screen.findByTitle("Dettaglio soggetto subject-linked")).toHaveAttribute("src", "/utenze/subject-linked?embedded=1");
    expect(screen.getByRole("link", { name: "Apri pagina" })).toHaveAttribute("href", "/utenze/subject-linked");
    fireEvent.click(screen.getAllByRole("button", { name: "Chiudi" }).at(-1)!);
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
