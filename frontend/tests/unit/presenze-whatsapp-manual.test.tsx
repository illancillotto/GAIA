import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WhatsAppManualMessage } from "@/components/presenze/whatsapp-manual-message";
import { previewManualWhatsApp, sendManualWhatsApp } from "@/lib/api/presenze-whatsapp-manual";

const state = vi.hoisted(() => ({ token: "token" as string | null, currentUser: { role: "admin" } as { role: string } | null }));
vi.mock("@/lib/use-session-bootstrap", () => ({ useSessionBootstrap: () => state }));

const preview = { record_id: "day-1", collaborator_name: "ROSSI MARIO", phone_e164: "+393331234567", work_date: "2026-09-07", reason: "Uscita mancante", text: "Ciao\nUscita mancante\nCorreggi su INAZ", fingerprint: "a".repeat(64), provider: "waha" as const };
function response(value: unknown) { return new Response(JSON.stringify(value), { status: 200, headers: { "content-type": "application/json" } }); }
let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => {
  state.token = "token";
  state.currentUser = { role: "admin" };
  fetchMock = vi.fn().mockImplementation(async () => response(preview));
  vi.stubGlobal("fetch", fetchMock);
});

async function open() {
  render(<WhatsAppManualMessage recordId="day-1" />);
  fireEvent.click(screen.getByRole("button", { name: "Prepara messaggio WhatsApp" }));
  await screen.findByRole("textbox");
}

describe("Manual WhatsApp", () => {
  it("requires admin and authentication", () => {
    state.token = null;
    const view = render(<WhatsAppManualMessage recordId="day-1" />);
    expect(view.container).toBeEmptyDOMElement();
    state.token = "token"; state.currentUser = null;
    view.rerender(<WhatsAppManualMessage recordId="day-1" />);
    expect(view.container).toBeEmptyDOMElement();
    state.currentUser = { role: "operator" };
    view.rerender(<WhatsAppManualMessage recordId="day-1" />);
    expect(view.container).toBeEmptyDOMElement();
  });

  it("previews, edits and sends only after confirmation", async () => {
    await open();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "   " } });
    expect(screen.getByRole("button", { name: "Conferma e invia WhatsApp" })).toBeDisabled();
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "Ingresso mancante alle 08:00" } });
    expect(screen.getByLabelText("Anteprima messaggio")).toHaveTextContent("Ingresso mancante alle 08:00");
    fetchMock.mockResolvedValueOnce(response({ status: "SENT", message_id: "m1" }));
    fireEvent.click(screen.getByRole("button", { name: "Conferma e invia WhatsApp" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Messaggio inviato");
    expect(fetchMock.mock.calls[1][1]).toEqual(expect.objectContaining({ method: "POST", body: JSON.stringify({ fingerprint: preview.fingerprint, reason: "Ingresso mancante alle 08:00", allow_outside_window: false }) }));
  });

  it("explicitly allows one manual send outside the window and resets on reopening", async () => {
    await open();
    const checkbox = screen.getByRole("checkbox", { name: /Invia anche fuori fascia/ });
    expect(checkbox).not.toBeChecked();
    fireEvent.click(checkbox);
    fetchMock.mockResolvedValueOnce(response({ status: "SENT", message_id: "m1" }));
    fireEvent.click(screen.getByRole("button", { name: "Conferma e invia WhatsApp" }));
    await screen.findByRole("status");
    expect(JSON.parse(fetchMock.mock.calls[1][1].body).allow_outside_window).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Prepara messaggio WhatsApp" }));
    expect(await screen.findByRole("checkbox", { name: /Invia anche fuori fascia/ })).not.toBeChecked();
  });

  it("cancels without sending and resets when the selected day changes", async () => {
    const view = render(<WhatsAppManualMessage recordId="day-1" />);
    fireEvent.click(screen.getByRole("button")); await screen.findByRole("textbox");
    fireEvent.click(screen.getByRole("button", { name: "Annulla" }));
    expect(screen.queryByRole("textbox")).toBeNull();
    fireEvent.click(screen.getByRole("button")); await screen.findByRole("textbox");
    view.rerender(<WhatsAppManualMessage recordId="day-2" />);
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it.each(["DRY_RUN", "FAILED", "UNKNOWN", "UNEXPECTED"])("shows truthful outcome %s", async (status) => {
    fetchMock.mockResolvedValueOnce(response({ ...preview, provider: "dry_run" }));
    await open();
    expect(screen.getByText(/Modalità di prova/)).toBeInTheDocument();
    fetchMock.mockResolvedValueOnce(response({ status }));
    fireEvent.click(screen.getByRole("button", { name: "Conferma simulazione" }));
    expect(await screen.findByRole("status")).not.toHaveTextContent("Messaggio inviato.");
  });

  it.each([new Error("offline"), "offline"])("handles preview failures", async (error) => {
    fetchMock.mockRejectedValue(error);
    render(<WhatsAppManualMessage recordId="day-1" />);
    fireEvent.click(screen.getByRole("button"));
    await screen.findByRole("status");
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  it.each([new Error("offline"), "offline"])("does not automatically retry failed confirmation", async (error) => {
    await open();
    fetchMock.mockRejectedValue(error);
    fireEvent.click(screen.getByRole("button", { name: "Conferma e invia WhatsApp" }));
    await screen.findByRole("status");
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  it("prevents overlapping preview and send requests", async () => {
    let resolve!: (value: Response) => void;
    fetchMock.mockImplementationOnce(() => new Promise<Response>((done) => { resolve = done; }));
    render(<WhatsAppManualMessage recordId="day-1" />);
    const button = screen.getByRole("button");
    act(() => { button.click(); button.click(); });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await act(async () => resolve(response(preview)));
    fetchMock.mockImplementationOnce(() => new Promise<Response>((done) => { resolve = done; }));
    const confirm = screen.getByRole("button", { name: "Conferma e invia WhatsApp" });
    act(() => { confirm.click(); confirm.click(); });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    await act(async () => resolve(response({ status: "SENT" })));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("inviato"));
  });

  it("uses authenticated, no-store API calls", async () => {
    await previewManualWhatsApp("token", "day-1");
    await sendManualWhatsApp("token", preview, "Motivo chiaro");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/presenze/whatsapp/daily/day-1/preview");
    expect(fetchMock.mock.calls[0][1]).toEqual(expect.objectContaining({ cache: "no-store", headers: expect.objectContaining({ Authorization: "Bearer token" }) }));
  });
});
