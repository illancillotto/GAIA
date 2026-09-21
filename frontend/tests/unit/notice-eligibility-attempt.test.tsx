import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { EligibilityPanel } from "@/components/ruolo/notice-register/eligibility-panel";
import { AttemptForm } from "@/components/ruolo/notice-register/attempt-form";
import { DocumentDetail } from "@/components/ruolo/notice-register/document-detail";
import { jsonResponse, noticeFixture } from "./notice-register-fixtures";

const check = {
  document_id: "doc-1", version: 1, checked_at: "2026-09-21T10:00:00Z",
  eligible: false, authorizes_dispatch: false, reasons: ["step_non_liberato", "future_reason"],
  positions: [{ position_id: "pos-1", avviso_id: "a", tax_year: 2022, eligible: false, reasons: ["notifica_perfezionata", "new_position_reason"] }],
};

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("loads eligibility on demand and rechecks without offering dispatch", async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse(check)).mockResolvedValueOnce(jsonResponse({
    ...check, eligible: true, reasons: [], positions: [{ ...check.positions[0], eligible: true, reasons: [] }],
  }));
  vi.stubGlobal("fetch", fetchMock);
  render(<EligibilityPanel token="token" documentId="doc-1" />);
  expect(fetchMock).not.toHaveBeenCalled();
  expect(screen.getByText(/non prenota e non autorizza un invio/)).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Verifica dati aggiornati" }));
  expect(await screen.findByText("Affidamento STEP presente o da verificare.")).toBeVisible();
  expect(screen.getByText("Notifica gia perfezionata.")).toBeVisible();
  expect(screen.getByText("future_reason")).toBeVisible();
  expect(screen.getByText("new_position_reason")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Verifica dati aggiornati" }));
  expect(await screen.findByText("Nessun blocco rilevato nella verifica corrente.")).toBeVisible();
  expect(screen.getByText("Annualita 2022: nessun blocco rilevato")).toBeVisible();
  expect(screen.queryByText("Affidamento STEP presente o da verificare.")).not.toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

it("reports an eligibility read failure without displaying an approval", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Rete non disponibile")));
  render(<EligibilityPanel token="token" documentId="doc-1" />);
  fireEvent.click(screen.getByRole("button", { name: "Verifica dati aggiornati" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Rete non disponibile");
  expect(screen.queryByText("Nessun blocco rilevato nella verifica corrente.")).not.toBeInTheDocument();
});

it.each(["TRACK-123", ""])("records a confirmed past attempt with optional tracking %s", async (tracking) => {
  const saved = vi.fn();
  const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ document_id: "doc-1", resource_id: "attempt", version: 5 }));
  vi.stubGlobal("fetch", fetchMock);
  render(<AttemptForm documentId="doc-1" context={{ token: "token", version: 4, onSaved: saved }} />);
  fireEvent.click(screen.getByText("Registra invio gia effettuato"));
  fireEvent.change(screen.getByLabelText("Canale"), { target: { value: "pec" } });
  fireEvent.change(screen.getByLabelText("Tracking o protocollo (facoltativo)"), { target: { value: tracking } });
  fireEvent.change(screen.getByLabelText("Data e ora invio (ora locale)"), { target: { value: "2024-06-29T12:00" } });
  fireEvent.change(screen.getByLabelText("Riferimento evidenza dell'invio"), { target: { value: " Distinta 42 " } });
  fireEvent.change(screen.getByLabelText("Motivo della registrazione o correzione"), { target: { value: " Riscontro " } });
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.submit(screen.getByRole("form", { name: "Invio gia effettuato" }));
  await waitFor(() => expect(saved).toHaveBeenCalledTimes(1));
  expect(fetchMock.mock.calls[0][0]).toContain("/doc-1/invii");
  expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
    expected_version: 4, reason: "Riscontro", data: {
      channel: "pec", tracking_code: tracking || null,
      sent_at: new Date("2024-06-29T12:00").toISOString(), evidence_reference: "Distinta 42", confirmed: true,
    },
  });
});

it("retains the historical declaration on a conflict and never assumes it was saved", async () => {
  const saved = vi.fn();
  const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ detail: "Conflitto" }, 409));
  vi.stubGlobal("fetch", fetchMock);
  render(<AttemptForm documentId="doc-1" context={{ token: "token", version: 1, onSaved: saved }} />);
  fireEvent.click(screen.getByText("Registra invio gia effettuato"));
  fireEvent.change(screen.getByLabelText("Data e ora invio (ora locale)"), { target: { value: "2024-06-29T12:00" } });
  fireEvent.submit(screen.getByRole("form", { name: "Invio gia effettuato" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/ricarica/i);
  expect(JSON.parse(fetchMock.mock.calls[0][1].body).data.confirmed).toBe(false);
  expect(saved).not.toHaveBeenCalled();
  expect(screen.getByLabelText("Data e ora invio (ora locale)")).toHaveValue("2024-06-29T12:00");
});

it("lets a viewer consult eligibility but not record shipments", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => jsonResponse(
    url.endsWith("/doc-1") ? noticeFixture() : url.endsWith("/ammissibilita") ? check : { items: [], total: 0, page: 1, page_size: 10 }
  )));
  render(<DocumentDetail token="token" documentId="doc-1" canEdit={false} onSelect={vi.fn()} />);
  expect(await screen.findByRole("heading", { name: "CUM-2022-2023" })).toBeVisible();
  expect(screen.queryByText("Registra invio gia effettuato")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Verifica dati aggiornati" }));
  const panel = screen.getByRole("region", { name: "Verifica ammissibilita" });
  expect(await within(panel).findByText("Notifica gia perfezionata.")).toBeVisible();
});
