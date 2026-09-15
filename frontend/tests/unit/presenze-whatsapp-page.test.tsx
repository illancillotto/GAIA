import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import PresenzeWhatsAppPage from "@/app/presenze/whatsapp/page";
import { WhatsAppMessageDialog, WhatsAppPreviewDialog } from "@/app/presenze/whatsapp/whatsapp-dialogs";
import { formatWhatsAppDateTime, whatsappSessionLabel, whatsappSkipLabel, whatsappStatusLabel, whatsappStatusTone } from "@/app/presenze/whatsapp/whatsapp-ui";
import type { PresenzeWhatsAppMessage, PresenzeWhatsAppPreview } from "@/types/api";

const mocks = vi.hoisted(() => ({
  token: vi.fn(), dashboard: vi.fn(), messages: vi.fn(), preview: vi.fn(), optOuts: vi.fn(), restore: vi.fn(), phone: vi.fn(), reconcile: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", () => ({
  getPresenzeWhatsAppDashboard: mocks.dashboard,
  listPresenzeWhatsAppMessages: mocks.messages,
  getPresenzeWhatsAppPreview: mocks.preview,
  listPresenzeWhatsAppOptOuts: mocks.optOuts,
  restorePresenzeWhatsAppUser: mocks.restore,
  updatePresenzeWhatsAppPhone: mocks.phone,
  reconcilePresenzeWhatsAppMessage: mocks.reconcile,
}));
vi.mock("@/components/app/protected-page", () => ({ ProtectedPage: ({ children, title }: { children: React.ReactNode; title: string }) => <main><h1>{title}</h1>{children}</main> }));

const message: PresenzeWhatsAppMessage = {
  id: "m1", collaborator_id: "c1", collaborator_name: "ROSSI MARIO", application_user_id: 7,
  user_label: "Mario Rossi", username: "mrossi", phone_e164: "+393331234567", text_body: "Ciao Mario\nControlla la timbratura",
  days: [{ work_date: "2026-09-14", problem: "missing_exit", detail: "uscita mancante" }], status: "UNKNOWN", provider: "waha",
  provider_message_id: null, error_code: "timeout", error_message: "Esito non noto", created_at: "2026-09-15T07:30:00Z",
  updated_at: "2026-09-15T07:31:00Z", delivered_at: null, read_at: null,
};

const preview: PresenzeWhatsAppPreview = {
  generated_at: "2026-09-15T08:00:00Z",
  ready: [{ collaborator_id: "c1", collaborator_name: "ROSSI MARIO", application_user_id: 7, phone_e164: "+39333", days: message.days, message_text: "Ciao Mario", ready: true, reason: null }],
  skipped: [
    { collaborator_id: "c2", collaborator_name: "BIANCHI ANNA", application_user_id: 8, phone_e164: null, days: message.days, message_text: null, ready: false, reason: "phone_missing" },
    { collaborator_id: "c3", collaborator_name: "NERI LUCA", application_user_id: null, phone_e164: null, days: message.days, message_text: null, ready: false, reason: "operator_not_linked" },
  ],
};

describe("Presenze WhatsApp UI helpers", () => {
  test("labels known and unknown states", () => {
    expect(whatsappStatusLabel("READ")).toBe("Letto");
    expect(whatsappStatusLabel("CUSTOM")).toBe("CUSTOM");
    expect(whatsappSkipLabel("phone_missing")).toContain("mancante");
    expect(whatsappSkipLabel("custom")).toBe("custom");
    expect(whatsappSkipLabel(null)).toContain("non disponibile");
    expect(whatsappStatusTone("READ")).toContain("emerald");
    expect(whatsappStatusTone("SENT")).toContain("sky");
    expect(whatsappStatusTone("UNKNOWN")).toContain("amber");
    expect(whatsappStatusTone("FAILED")).toContain("rose");
    expect(formatWhatsAppDateTime(null)).toBe("—");
    expect(formatWhatsAppDateTime("2026-09-15T07:30:00Z")).not.toBe("—");
    for (const state of ["working", "dry_run", "disabled", "starting", "scan_qr_code", "stopped", "failed", "unavailable", "misconfigured", "unsupported", "invalid_response"]) {
      expect(whatsappSessionLabel(state)).not.toBe(state);
    }
    expect(whatsappSessionLabel("custom")).toBe("custom");
    expect(whatsappSessionLabel(undefined)).toBe("Stato non disponibile");
  });
});

describe("Presenze WhatsApp dialogs", () => {
  test("shows full message and reconciles either outcome", async () => {
    const close = vi.fn();
    const reconcile = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(<WhatsAppMessageDialog message={message} busy={false} onClose={close} onReconcile={reconcile} />);
    expect(screen.getByText("Esito non noto")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Chiudi dettaglio messaggio"));
    expect(close).toHaveBeenCalled();
    fireEvent.change(screen.getByPlaceholderText("Evidenza della verifica"), { target: { value: "Controllato" } });
    fireEvent.change(screen.getByPlaceholderText("ID messaggio WAHA, se inviato"), { target: { value: "wa-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Conferma inviato" }));
    expect(reconcile).toHaveBeenCalledWith(true, "Controllato", "wa-1");
    fireEvent.click(screen.getByRole("button", { name: "Segna non inviato" }));
    expect(reconcile).toHaveBeenCalledWith(false, "Controllato", "");
    rerender(<WhatsAppMessageDialog message={{ ...message, status: "READ", error_message: null, username: null, provider_message_id: "wa-2", delivered_at: message.updated_at, read_at: message.updated_at }} busy={true} onClose={close} onReconcile={reconcile} />);
    expect(screen.queryByText("Riconciliazione manuale")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    rerender(<WhatsAppMessageDialog message={{ ...message, error_code: null }} busy={false} onClose={close} onReconcile={reconcile} />);
    expect(screen.getByText("Errore invio")).toBeInTheDocument();
  });

  test("previews messages, saves phones and restores STOP", async () => {
    const close = vi.fn(), restore = vi.fn().mockResolvedValue(undefined), phone = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(<WhatsAppPreviewDialog preview={preview} optOuts={[{ application_user_id: 9, user_label: "Paolo Verdi", username: null, collaborator_name: null, phone_e164: null, source: "reply", created_at: "2026-09-15T08:00:00Z" }]} onClose={close} onRestore={restore} onUpdatePhone={phone} />);
    fireEvent.change(screen.getByPlaceholderText("+39 333 1234567"), { target: { value: "+39333111" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva" }));
    expect(phone).toHaveBeenCalledWith(8, "+39333111");
    fireEvent.click(screen.getByRole("button", { name: "Riattiva promemoria" }));
    expect(restore).toHaveBeenCalledWith(9);
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    expect(close).toHaveBeenCalled();
    rerender(<WhatsAppPreviewDialog preview={{ ...preview, ready: [], skipped: [{ ...preview.skipped[0], reason: "phone_invalid" }] }} optOuts={[]} onClose={close} onRestore={restore} onUpdatePhone={phone} />);
    expect(screen.getByText(/Nessun promemoria pronto/)).toBeInTheDocument();
    expect(screen.getByDisplayValue("+39333111")).toBeInTheDocument();
  });
});

describe("Presenze WhatsApp page", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mocks.token.mockReturnValue("token");
    mocks.dashboard.mockResolvedValue({ provider_enabled: false, provider: null, session_status: "disabled", session_detail: null, cron: "30 9 * * 1-5", next_run_at: null, send_window: "08:00-19:00", max_per_run: 40, sent_total: 3, delivered_total: 2, read_total: 1, failed_total: 1, uncertain_total: 1, opted_out_total: 1 });
    mocks.messages.mockResolvedValue({ items: [message], total: 26, page: 1, page_size: 25 });
    mocks.optOuts.mockResolvedValue([]);
    mocks.preview.mockResolvedValue(preview);
    mocks.restore.mockResolvedValue(undefined);
    mocks.phone.mockResolvedValue({ application_user_id: 8, phone: "+39333" });
    mocks.reconcile.mockResolvedValue(undefined);
  });

  test("loads, filters, pages and opens both large modals", async () => {
    render(<PresenzeWhatsAppPage />);
    expect(await screen.findByText("Mario Rossi")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Nome, username, telefono"), { target: { value: "Rossi" } });
    fireEvent.change(screen.getByLabelText("Stato"), { target: { value: "READ" } });
    await waitFor(() => expect(mocks.messages).toHaveBeenLastCalledWith("token", expect.objectContaining({ status: "READ", q: "Rossi" })));
    fireEvent.click(screen.getByRole("button", { name: "Avanti" }));
    await waitFor(() => expect(mocks.messages).toHaveBeenLastCalledWith("token", expect.objectContaining({ page: 2 })));
    fireEvent.click(screen.getByRole("button", { name: "Indietro" }));
    fireEvent.click(screen.getByRole("button", { name: "Apri" }));
    expect(screen.getByRole("dialog", { name: "Mario Rossi" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    fireEvent.click(screen.getByRole("button", { name: "Apri anteprima" }));
    expect(await screen.findByRole("dialog", { name: "Prossimi promemoria" })).toBeInTheDocument();
  });

  test("runs phone, STOP and reconciliation actions", async () => {
    mocks.optOuts.mockResolvedValue([{ application_user_id: 9, user_label: "Paolo", username: null, collaborator_name: null, phone_e164: "+399", source: "reply", created_at: message.created_at }]);
    render(<PresenzeWhatsAppPage />);
    await screen.findByText("Mario Rossi");
    fireEvent.click(screen.getByRole("button", { name: "Apri anteprima" }));
    await screen.findByText("Paolo");
    fireEvent.click(screen.getByRole("button", { name: "Riattiva promemoria" }));
    await waitFor(() => expect(mocks.restore).toHaveBeenCalledWith("token", 9));
    fireEvent.change(screen.getByPlaceholderText("+39 333 1234567"), { target: { value: "+39333" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva" }));
    await waitFor(() => expect(mocks.phone).toHaveBeenCalledWith("token", 8, "+39333"));
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    fireEvent.click(screen.getByRole("button", { name: "Apri" }));
    fireEvent.change(screen.getByPlaceholderText("Evidenza della verifica"), { target: { value: "Verificato" } });
    fireEvent.change(screen.getByPlaceholderText("ID messaggio WAHA, se inviato"), { target: { value: "wa-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Conferma inviato" }));
    await waitFor(() => expect(mocks.reconcile).toHaveBeenCalled());
  });

  test("reconciles a confirmed non-send without a provider id", async () => {
    mocks.dashboard.mockResolvedValue({ ...(await mocks.dashboard()), provider_enabled: true, provider: "dry_run", session_status: "dry_run", session_detail: null });
    render(<PresenzeWhatsAppPage />);
    await screen.findByText("Mario Rossi");
    fireEvent.click(screen.getByRole("button", { name: "Apri" }));
    fireEvent.change(screen.getByPlaceholderText("Evidenza della verifica"), { target: { value: "Non presente in WAHA" } });
    fireEvent.click(screen.getByRole("button", { name: "Segna non inviato" }));
    await waitFor(() => expect(mocks.reconcile).toHaveBeenCalledWith("token", "m1", expect.objectContaining({ sent: false, provider_message_id: null })));
  });

  test("shows active channel, empty history and loading failures", async () => {
    mocks.dashboard.mockResolvedValue({ ...(await mocks.dashboard()), provider_enabled: true, provider: "waha", session_status: "working", session_detail: "Sessione default", next_run_at: "2026-09-16T07:30:00Z" });
    mocks.messages.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 25 });
    render(<PresenzeWhatsAppPage />);
    expect(await screen.findByText("Nessun messaggio corrisponde ai filtri.")).toBeInTheDocument();
    expect(screen.getByText("Collegata")).toBeInTheDocument();
    mocks.preview.mockRejectedValueOnce("errore preview");
    fireEvent.click(screen.getByRole("button", { name: "Apri anteprima" }));
    expect(await screen.findByText("Impossibile calcolare l’anteprima")).toBeInTheDocument();
  });

  test("shows the preview API error message", async () => {
    mocks.preview.mockRejectedValueOnce(new Error("anteprima non disponibile"));
    render(<PresenzeWhatsAppPage />);
    await screen.findByText("Mario Rossi");
    fireEvent.click(screen.getByRole("button", { name: "Apri anteprima" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("anteprima non disponibile");
  });

  test("handles initial errors and missing tokens", async () => {
    mocks.dashboard.mockRejectedValueOnce(new Error("backend non disponibile"));
    render(<PresenzeWhatsAppPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("backend non disponibile");
    mocks.token.mockReturnValue(null);
    render(<PresenzeWhatsAppPage />);
    expect(mocks.dashboard).toHaveBeenCalledTimes(1);
  });

  test("covers fallback errors and ignores actions after the session disappears", async () => {
    mocks.dashboard.mockRejectedValueOnce("errore generico");
    const { unmount } = render(<PresenzeWhatsAppPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Impossibile caricare la dashboard WhatsApp");
    unmount();

    mocks.dashboard.mockResolvedValue({ provider_enabled: false, provider: null, session_status: "disabled", session_detail: null, cron: "30 9 * * 1-5", next_run_at: null, send_window: "08:00-19:00", max_per_run: 40, sent_total: 0, delivered_total: 0, read_total: 0, failed_total: 0, uncertain_total: 0, opted_out_total: 0 });
    mocks.messages.mockResolvedValue({ items: [{ ...message, username: null, days: [...message.days, { ...message.days[0], work_date: "2026-09-13" }] }], total: 1, page: 1, page_size: 25 });
    render(<PresenzeWhatsAppPage />);
    await screen.findByText("giornate");
    mocks.token.mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: "Apri anteprima" }));
    expect(mocks.preview).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Apri" }));
    fireEvent.change(screen.getByPlaceholderText("Evidenza della verifica"), { target: { value: "Verificato" } });
    fireEvent.click(screen.getByRole("button", { name: "Segna non inviato" }));
    expect(mocks.reconcile).not.toHaveBeenCalled();
  });

  test("ignores STOP and phone changes when the token is gone", async () => {
    mocks.optOuts.mockResolvedValue([{ application_user_id: 9, user_label: "Paolo", username: null, collaborator_name: null, phone_e164: null, source: "reply", created_at: message.created_at }]);
    render(<PresenzeWhatsAppPage />);
    await screen.findByText("Mario Rossi");
    fireEvent.click(screen.getByRole("button", { name: "Apri anteprima" }));
    await screen.findByText("Paolo");
    mocks.token.mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: "Riattiva promemoria" }));
    fireEvent.click(screen.getByRole("button", { name: "Salva" }));
    expect(mocks.restore).not.toHaveBeenCalled();
    expect(mocks.phone).not.toHaveBeenCalled();
  });
});
