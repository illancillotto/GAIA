import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/core";
import { recoverablePhoneContact, WhatsAppPhoneRecovery } from "@/components/presenze/whatsapp-phone-recovery";
import { WhatsAppManualMessage } from "@/components/presenze/whatsapp-manual-message";

vi.mock("@/lib/use-session-bootstrap", () => ({ useSessionBootstrap: () => ({ token: "token", currentUser: { role: "admin" } }) }));
const contact = { application_user_id: 42, collaborator_name: "COLLABORATORE TEST" };
const data = { ...contact, code: "operator_profile_missing", message: "Aggiungi il numero" };
const reply = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

describe("Phone recovery", () => {
  it.each([null, new Error("offline"), new ApiError("error"), new ApiError("error", {}), new ApiError("error", { ...data, code: "opted_out" }), new ApiError("error", { ...data, application_user_id: "42" }), new ApiError("error", { ...data, collaborator_name: null })])("ignores non-recoverable errors", (error) => {
    expect(recoverablePhoneContact(error)).toBeNull();
  });
  it.each(["operator_profile_missing", "phone_missing", "phone_invalid"])("accepts structured %s", (code) => {
    expect(recoverablePhoneContact(new ApiError("error", { ...data, code }))).toEqual(contact);
  });
  it("is hidden without a recoverable canonical contact", () => {
    const view = render(<WhatsAppPhoneRecovery token="token" contact={null} onSaved={vi.fn()} />);
    expect(view.container).toBeEmptyDOMElement();
  });
  it("opens and cancels without writes, rejecting invalid input", () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    render(<WhatsAppPhoneRecovery token="token" contact={contact} onSaved={vi.fn()} />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("button", { name: "Salva numero e prepara messaggio" })).toBeDisabled();
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva numero e prepara messaggio" }));
    expect(screen.getByRole("alert")).toHaveTextContent("numero valido");
    fireEvent.click(screen.getByRole("button", { name: "Annulla" }));
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it.each([new Error("offline"), "offline"])("keeps the editor after a save failure", async (error) => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(error));
    render(<WhatsAppPhoneRecovery token="token" contact={contact} onSaved={vi.fn()} />);
    fireEvent.click(screen.getByRole("button"));
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "+393331234567" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva numero e prepara messaggio" }));
    await screen.findByRole("alert");
    expect(screen.getByRole("textbox")).toHaveValue("+393331234567");
  });
  it("saves once on double click and refreshes the preview without sending", async () => {
    let resolve!: (response: Response) => void;
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(reply({ detail: data }, 409))
      .mockImplementationOnce(() => new Promise<Response>((done) => { resolve = done; }))
      .mockResolvedValueOnce(reply({ record_id: "day", collaborator_name: contact.collaborator_name, phone_e164: "+393331234567", work_date: "2026-09-07", reason: "Uscita mancante", text: "Ciao\nUscita mancante\nCorreggi su INAZ", provider: "dry_run", fingerprint: "a".repeat(64) }));
    vi.stubGlobal("fetch", fetchMock);
    render(<WhatsAppManualMessage recordId="day" />);
    fireEvent.click(screen.getByRole("button", { name: "Prepara messaggio WhatsApp" }));
    fireEvent.click(await screen.findByRole("button", { name: "Aggiungi numero WhatsApp" }));
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "0039 333 1234567" } });
    const save = screen.getByRole("button", { name: "Salva numero e prepara messaggio" });
    act(() => { save.click(); save.click(); });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1][0]).toBe("/api/presenze/whatsapp/users/42/phone");
    expect(fetchMock.mock.calls[1][1]).toEqual(expect.objectContaining({ method: "PATCH", body: JSON.stringify({ phone: "+393331234567" }) }));
    await act(async () => resolve(reply({ application_user_id: 42, phone: "+393331234567" })));
    await screen.findByRole("button", { name: "Conferma simulazione" });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls.every(([url]) => !String(url).endsWith("/send"))).toBe(true);
  });
});
