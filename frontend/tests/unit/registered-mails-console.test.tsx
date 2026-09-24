import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { RegisteredMailAssociationModal } from "@/components/ruolo/registered-mail-association-modal";
import { RegisteredMailsAccess, RegisteredMailsConsole } from "@/components/ruolo/registered-mails-console";
import type { RuoloTributiAvvisoListItemResponse, RuoloTributiRegisteredMailResponse } from "@/types/ruolo";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  listTributiAvvisi: vi.fn(),
  listTributiRegisteredMails: vi.fn(),
  getTributiRegisteredMailSummary: vi.fn(),
  updateTributiRegisteredMailAssociation: vi.fn(),
  useSessionBootstrap: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/ruolo-api", () => ({
  listTributiAvvisi: mocks.listTributiAvvisi,
  listTributiRegisteredMails: mocks.listTributiRegisteredMails,
}));

vi.mock("@/lib/registered-mail-api", () => ({
  getTributiRegisteredMailSummary: mocks.getTributiRegisteredMailSummary,
  updateTributiRegisteredMailAssociation: mocks.updateTributiRegisteredMailAssociation,
}));

vi.mock("@/lib/use-session-bootstrap", () => ({
  useSessionBootstrap: mocks.useSessionBootstrap,
}));

function registeredMail(
  overrides: Partial<RuoloTributiRegisteredMailResponse> = {},
): RuoloTributiRegisteredMailResponse {
  return {
    id: "mail-1",
    import_job_id: "job-1",
    avviso_id: "avviso-1",
    subject_id: "subject-1",
    source_system: "poste-online",
    source_shipment_id: "SHP-001",
    recipient_index: 0,
    shipment_name: "Spedizione Rossi",
    service: "Raccomandata",
    status_label: "Consegnata",
    sent_at: "2026-07-20T00:00:00Z",
    recipient_name: "ROSSI MARIO",
    recipient_address: "VIA ROMA 1",
    recipient_city: "URAS",
    recipient_province: "OR",
    recipient_zipcode: "09099",
    tracking_number: "TRK001",
    price_amount: 6.5,
    annualita_json: [2024],
    match_status: "matched",
    match_score: 96,
    match_reason: "codice fiscale e indirizzo",
    anomaly_key: null,
    recovery_status: "recovered",
    recovered_payment_id: "pay-1",
    raw_payload_json: null,
    created_at: "2026-07-20T00:00:00Z",
    updated_at: "2026-07-20T00:00:00Z",
    ...overrides,
  };
}

function avviso(overrides: Partial<RuoloTributiAvvisoListItemResponse> = {}): RuoloTributiAvvisoListItemResponse {
  return {
    id: "avviso-1",
    codice_cnc: "CNC-1",
    anno_tributario: 2022,
    subject_id: "subject-1",
    codice_fiscale_raw: "RSSMRA80A01H501Z",
    nominativo_raw: "ROSSI MARIO",
    codice_utenza: "UT-1",
    importo_totale_euro: 100,
    paid_amount: 0,
    saldo_amount: 100,
    payment_status: "unpaid",
    workflow_status: null,
    last_payment_at: null,
    capacitas_url: null,
    capacitas_avviso_code: null,
    display_name: "ROSSI MARIO",
    is_linked: true,
    notes_count: 0,
    annuality_manager_key: null,
    annuality_manager_label: null,
    calculation_policy: null,
    reminder_enabled: false,
    ...overrides,
  };
}

async function flushDebounce(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 380));
}

describe("RegisteredMailsConsole", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReset();
    mocks.listTributiAvvisi.mockReset();
    mocks.listTributiRegisteredMails.mockReset();
    mocks.getTributiRegisteredMailSummary.mockReset();
    mocks.getTributiRegisteredMailSummary.mockResolvedValue({ total: 2307, associated: 113, anomalies: 2194 });
    mocks.updateTributiRegisteredMailAssociation.mockReset();
    mocks.useSessionBootstrap.mockReset();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.useSessionBootstrap.mockReturnValue({
      status: "ready",
      token: "token",
      currentUser: { role: "admin", enabled_modules: ["ruolo"] },
      grantedSectionKeys: ["ruolo.tributi.view", "ruolo.tributi.manage_status"],
    });
  });

  test("loads registered mails, filters anomalies and paginates", async () => {
    mocks.listTributiRegisteredMails
      .mockResolvedValueOnce({
        items: [
          registeredMail(),
          registeredMail({
            id: "mail-2",
            avviso_id: null,
            source_shipment_id: "SHP-002",
            recipient_name: null,
            shipment_name: null,
            recipient_address: null,
            recipient_city: null,
            tracking_number: null,
            sent_at: null,
            price_amount: null,
            match_status: "unmatched",
            match_score: null,
            match_reason: null,
            anomaly_key: "no_candidate",
            recovery_status: "pending",
          }),
          registeredMail({
            id: "mail-3",
            avviso_id: null,
            source_shipment_id: "SHP-003",
            match_status: "ambiguous",
            match_reason: "piu candidati compatibili",
            recovery_status: "not_applicable",
          }),
        ],
        total: 30,
        page: 1,
        page_size: 25,
      })
      .mockResolvedValueOnce({ items: [], total: 30, page: 2, page_size: 25 })
      .mockResolvedValueOnce({ items: [], total: 30, page: 1, page_size: 25 })
      .mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 25 })
      .mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 25 })
      .mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 25 });

    render(<RegisteredMailsConsole className="extra-class" />);
    await flushDebounce();

    await screen.findByText("Pagina 1 · 3 elementi mostrati su 30");
    expect(screen.getByText("Associati totali").nextElementSibling).toHaveTextContent("113");
    expect(screen.getByText("Anomalie totali").nextElementSibling).toHaveTextContent("2194");
    expect(screen.getAllByText("ROSSI MARIO").length).toBeGreaterThan(0);
    expect(screen.getByText("Destinatario non letto")).toBeInTheDocument();
    expect(screen.getAllByText("Tracking TRK001").length).toBeGreaterThan(0);
    expect(screen.getByText("Tracking -")).toBeInTheDocument();
    expect(screen.getByText("Associata")).toBeInTheDocument();
    expect(screen.getByText("Non associata")).toBeInTheDocument();
    expect(screen.getByText("Ambigua")).toBeInTheDocument();
    expect(screen.getByText("Recuperata")).toBeInTheDocument();
    expect(screen.getAllByText("Da recuperare").length).toBeGreaterThan(0);
    expect(screen.getByText("Non applicabile")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Apri avviso" })).toHaveAttribute("href", "/ruolo/tributi?avviso=avviso-1");
    expect(screen.getAllByText("Non associato").length).toBeGreaterThan(0);
    expect(screen.getByText("Pagina 1 · 3 elementi mostrati su 30")).toBeInTheDocument();

    const footer = screen.getByText(/Pagina 1/).closest("div")?.parentElement;
    expect(footer).not.toBeNull();
    fireEvent.click(within(footer as HTMLElement).getByRole("button", { name: "Raccomandate successiva" }));
    await waitFor(() =>
      expect(mocks.listTributiRegisteredMails).toHaveBeenLastCalledWith("token", expect.objectContaining({ page: 2 })),
    );
    await screen.findByText("Pagina 2 · 0 elementi mostrati su 30");
    expect(screen.getByText("Associati totali").nextElementSibling).toHaveTextContent("113");
    fireEvent.click(screen.getByRole("button", { name: "Raccomandate precedente" }));
    await waitFor(() =>
      expect(mocks.listTributiRegisteredMails).toHaveBeenLastCalledWith("token", expect.objectContaining({ page: 1 })),
    );

    fireEvent.change(screen.getByPlaceholderText("Destinatario, tracking, indirizzo, shipment id..."), {
      target: { value: "Ro" },
    });
    await flushDebounce();
    expect(mocks.listTributiRegisteredMails).toHaveBeenLastCalledWith(
      "token",
      expect.objectContaining({ anomalies_only: true, page: 1, page_size: 25, q: undefined }),
    );

    fireEvent.change(screen.getByPlaceholderText("Destinatario, tracking, indirizzo, shipment id..."), {
      target: { value: "Rossi" },
    });
    fireEvent.change(screen.getByDisplayValue("Tutti i match"), { target: { value: "ambiguous" } });
    fireEvent.change(screen.getByDisplayValue("Tutti recuperi"), { target: { value: "not_applicable" } });
    fireEvent.click(screen.getByLabelText("Solo anomalie"));
    await flushDebounce();
    expect(mocks.listTributiRegisteredMails).toHaveBeenLastCalledWith(
      "token",
      expect.objectContaining({
        anomalies_only: false,
        match_status: "ambiguous",
        q: "Rossi",
        recovery_status: "not_applicable",
      }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Aggiorna raccomandate" }));
    await waitFor(() => expect(mocks.listTributiRegisteredMails).toHaveBeenCalledTimes(6));
  });

  test("renders empty state and skips API calls without a token", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);

    render(<RegisteredMailsConsole />);
    await flushDebounce();

    expect(mocks.listTributiRegisteredMails).not.toHaveBeenCalled();
    expect(screen.getByText("Nessuna raccomandata trovata")).toBeInTheDocument();
  });

  test("shows API errors", async () => {
    mocks.listTributiRegisteredMails.mockRejectedValueOnce(new Error("errore backend"));

    render(<RegisteredMailsConsole />);
    await flushDebounce();

    expect(await screen.findByText("errore backend")).toBeInTheDocument();
  });

  test("shows fallback error text for non-error failures and unknown statuses", async () => {
    mocks.listTributiRegisteredMails
      .mockRejectedValueOnce("bad")
      .mockResolvedValueOnce({
        items: [
          registeredMail({
            id: "mail-unknown",
            avviso_id: null,
            match_status: "custom_match",
            match_reason: null,
            anomaly_key: null,
            recovery_status: "custom_recovery",
          }),
        ],
        total: 1,
        page: 1,
        page_size: 25,
      });

    render(<RegisteredMailsConsole />);
    await flushDebounce();

    expect(await screen.findByText("Errore caricamento raccomandate Poste Online")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna raccomandate" }));

    expect(await screen.findByText("custom_match")).toBeInTheDocument();
    expect(screen.getByText("custom_recovery")).toBeInTheDocument();
    expect(screen.getByText("Score 96 · nessuna nota")).toBeInTheDocument();
  });

  test("opens matching modal, associates a candidate and updates the row", async () => {
    const unmatched = registeredMail({
      avviso_id: null,
      match_status: "ambiguous",
      raw_payload_json: { candidate_avviso_ids: ["avviso-1", 42] },
    });
    const updated = registeredMail({ match_reason: "Associazione manuale impostata dall'operatore" });
    mocks.listTributiRegisteredMails
      .mockResolvedValueOnce({
        items: [unmatched, registeredMail({ id: "mail-other", source_shipment_id: "SHP-OTHER" })],
        total: 2,
        page: 1,
        page_size: 25,
      })
      .mockResolvedValue({
        items: [updated, registeredMail({ id: "mail-other", source_shipment_id: "SHP-OTHER" })],
        total: 2,
        page: 1,
        page_size: 25,
      });
    mocks.listTributiAvvisi.mockResolvedValue({
      items: [avviso(), avviso({ id: "avviso-2", display_name: null, nominativo_raw: null, codice_fiscale_raw: null, codice_utenza: null, importo_totale_euro: null })],
      total: 2,
      page: 1,
      page_size: 20,
    });
    mocks.updateTributiRegisteredMailAssociation.mockResolvedValue(updated);

    render(<RegisteredMailsConsole canEdit token="token" />);
    await flushDebounce();
    fireEvent.click(await screen.findByRole("button", { name: "Associa manualmente" }));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    await waitFor(() => expect(mocks.listTributiAvvisi).toHaveBeenCalledWith("token", expect.objectContaining({ q: "ROSSI MARIO" })));
    expect(screen.getByText("Candidato automatico")).toBeInTheDocument();
    expect(screen.getByText("Nominativo assente")).toBeInTheDocument();
    expect(screen.getByText(/CF assente/)).toBeInTheDocument();
    expect(screen.getAllByText("-").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("checkbox", { name: /ROSSI MARIO/ }));
    fireEvent.click(screen.getByRole("button", { name: "Conferma 1 avvisi" }));
    await waitFor(() =>
      expect(mocks.updateTributiRegisteredMailAssociation).toHaveBeenCalledWith("token", "mail-1", { avviso_ids: ["avviso-1"] }),
    );
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await waitFor(() => expect(mocks.getTributiRegisteredMailSummary).toHaveBeenCalledTimes(2));
    expect(screen.getAllByRole("button", { name: "Cambia associazione" })).toHaveLength(2);
    expect(screen.getByText(/Associazione manuale impostata/)).toBeInTheDocument();
  });

  test("removes an existing association", async () => {
    const matched = registeredMail();
    const unlinked = registeredMail({ avviso_id: null, match_status: "unmatched", anomaly_key: "manual_unlinked" });
    mocks.listTributiRegisteredMails
      .mockResolvedValueOnce({ items: [matched], total: 1, page: 1, page_size: 25 })
      .mockResolvedValue({ items: [unlinked], total: 1, page: 1, page_size: 25 });
    mocks.listTributiAvvisi.mockResolvedValue({ items: [avviso()], total: 1, page: 1, page_size: 20 });
    mocks.updateTributiRegisteredMailAssociation.mockResolvedValue(unlinked);

    render(<RegisteredMailsConsole canEdit token="token" />);
    await flushDebounce();
    fireEvent.click(await screen.findByRole("button", { name: "Cambia associazione" }));
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cambia associazione" }));
    fireEvent.click(screen.getByRole("button", { name: "Rimuovi associazione" }));
    await waitFor(() =>
      expect(mocks.updateTributiRegisteredMailAssociation).toHaveBeenCalledWith("token", "mail-1", { avviso_ids: [] }),
    );
    expect(await screen.findByRole("button", { name: "Associa manualmente" })).toBeInTheDocument();
  });

  test("handles modal search, save errors and keyboard close", async () => {
    const onClose = vi.fn();
    const onSaved = vi.fn();
    mocks.listTributiAvvisi
      .mockRejectedValueOnce("bad search")
      .mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 20 })
      .mockResolvedValueOnce({ items: [avviso()], total: 1, page: 1, page_size: 20 });
    mocks.updateTributiRegisteredMailAssociation
      .mockRejectedValueOnce("bad save")
      .mockRejectedValueOnce(new Error("salvataggio fallito"));

    const { rerender } = render(
      <RegisteredMailAssociationModal mail={registeredMail({ avviso_id: null, recipient_name: null })} token="token" onClose={onClose} onSaved={onSaved} />,
    );
    expect(document.body.style.overflow).toBe("hidden");
    expect(await screen.findByText("Errore ricerca avvisi")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Nominativo, codice fiscale, CNC o utenza"), { target: { value: "" } });
    expect(await screen.findByText("Nessun avviso trovato.")).toBeInTheDocument();
    mocks.listTributiAvvisi.mockReset();
    mocks.listTributiAvvisi.mockResolvedValue({ items: [avviso()], total: 1, page: 1, page_size: 20 });
    fireEvent.change(screen.getByPlaceholderText("Nominativo, codice fiscale, CNC o utenza"), { target: { value: "Rossi" } });
    await screen.findByRole("checkbox");
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Conferma 1 avvisi" }));
    expect(await screen.findByText("Errore aggiornamento associazione")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Conferma 1 avvisi" }));
    expect(await screen.findByText("salvataggio fallito")).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Enter" });
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
    rerender(<div />);
    expect(document.body.style.overflow).toBe("");
    expect(onSaved).not.toHaveBeenCalled();
  });

  test("ignores completed searches after cancellation", async () => {
    let resolveSearch: (value: { items: RuoloTributiAvvisoListItemResponse[]; total: number; page: number; page_size: number }) => void = () => {};
    const pendingSearch = new Promise<{ items: RuoloTributiAvvisoListItemResponse[]; total: number; page: number; page_size: number }>((resolve) => {
      resolveSearch = resolve;
    });
    mocks.listTributiAvvisi
      .mockReturnValueOnce(pendingSearch)
      .mockRejectedValueOnce(new Error("ricerca fallita"));

    render(
      <RegisteredMailAssociationModal
        mail={registeredMail({ recipient_name: null, shipment_name: null, raw_payload_json: { candidate_avviso_ids: "invalid" } })}
        token="token"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );
    await waitFor(() => expect(mocks.listTributiAvvisi).toHaveBeenCalledWith("token", expect.objectContaining({ q: undefined })));
    fireEvent.change(screen.getByPlaceholderText("Nominativo, codice fiscale, CNC o utenza"), { target: { value: "Nuova ricerca" } });
    resolveSearch({ items: [avviso()], total: 1, page: 1, page_size: 20 });
    expect(await screen.findByText("ricerca fallita")).toBeInTheDocument();
    expect(screen.getByText(/Destinatario non letto/)).toBeInTheDocument();
  });

  test("ignores rejected searches after unmount", async () => {
    let rejectSearch: (error: Error) => void = () => {};
    const pendingSearch = new Promise<never>((_resolve, reject) => {
      rejectSearch = reject;
    });
    mocks.listTributiAvvisi.mockReturnValueOnce(pendingSearch);
    const view = render(
      <RegisteredMailAssociationModal mail={registeredMail()} token="token" onClose={vi.fn()} onSaved={vi.fn()} />,
    );
    await waitFor(() => expect(mocks.listTributiAvvisi).toHaveBeenCalledTimes(1));
    view.unmount();
    rejectSearch(new Error("late failure"));
    await Promise.resolve();
    expect(screen.queryByText("late failure")).not.toBeInTheDocument();
  });

  test("enforces access state before rendering the editable console", async () => {
    mocks.useSessionBootstrap.mockReturnValueOnce({ status: "checking", token: null, currentUser: null, grantedSectionKeys: [] });
    const { rerender } = render(<RegisteredMailsAccess />);
    expect(screen.getByRole("status")).toHaveTextContent("Verifica accesso");

    mocks.useSessionBootstrap.mockReturnValueOnce({
      status: "ready",
      token: "token",
      currentUser: { role: "viewer", enabled_modules: [] },
      grantedSectionKeys: ["ruolo.tributi.view"],
    });
    rerender(<RegisteredMailsAccess />);
    expect(screen.getByRole("alert")).toHaveTextContent("non autorizzato");

    mocks.listTributiRegisteredMails.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 25 });
    mocks.useSessionBootstrap.mockReturnValueOnce({
      status: "ready",
      token: "token",
      currentUser: { role: "super_admin", enabled_modules: [] },
      grantedSectionKeys: ["ruolo.tributi.view", "ruolo.tributi.manage_status"],
    });
    rerender(<RegisteredMailsAccess />);
    await flushDebounce();
    expect(await screen.findByText("Nessuna raccomandata trovata")).toBeInTheDocument();
  });
});
