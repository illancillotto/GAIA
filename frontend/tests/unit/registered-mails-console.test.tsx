import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { RegisteredMailsConsole } from "@/components/ruolo/registered-mails-console";
import type { RuoloTributiRegisteredMailResponse } from "@/types/ruolo";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  listTributiRegisteredMails: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/ruolo-api", () => ({
  listTributiRegisteredMails: mocks.listTributiRegisteredMails,
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

async function flushDebounce(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 380));
}

describe("RegisteredMailsConsole", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReset();
    mocks.listTributiRegisteredMails.mockReset();
    mocks.getStoredAccessToken.mockReturnValue("token");
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
});
