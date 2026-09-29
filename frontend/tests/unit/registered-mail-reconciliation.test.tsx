import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import * as XLSX from "xlsx";

import { RegisteredMailReconciliation } from "@/components/ruolo/registered-mail-reconciliation";
import type { RegisteredMailCampaignItem, RegisteredMailCampaignPreview } from "@/types/registered-mail-campaign";

const mocks = vi.hoisted(() => ({ preview: vi.fn(), update: vi.fn(), check: vi.fn() }));
vi.mock("@/lib/registered-mail-api", () => ({
  getRegisteredMailCampaignPreview: mocks.preview,
  updateTributiRegisteredMailAssociation: mocks.update,
  checkRegisteredMailReferences: mocks.check,
}));

const item: RegisteredMailCampaignItem = {
  mail_id: "mail-1", source_shipment_id: "shipment-1", recipient_name: "ROSSI MARIO", recipient_address: "VIA ROMA 1",
  tracking_number: "TRK-1", legacy_avviso_id: null, classification: "proposed_pair", reasons: [],
  requires_operator_confirmation: true, register_document_id: null, register_avviso_ids: [],
  candidate_notices: [
    { avviso_id: "a22", subject_id: "subject", tax_year: 2022, codice_cnc: "CNC22", codice_fiscale: "RSSMRA80A01H501Z", nominativo: "ROSSI MARIO" },
    { avviso_id: "a23", subject_id: "subject", tax_year: 2023, codice_cnc: "CNC23", codice_fiscale: "RSSMRA80A01H501Z", nominativo: "ROSSI MARIO" },
  ],
};

function preview(items: RegisteredMailCampaignItem[] = [item]): RegisteredMailCampaignPreview {
  return { campaign: "historical_poste_2022_2023", created_before: "", expected_years: [2022, 2023], read_only: true, total: items.length, counts: { proposed_pair: items.length }, items };
}

function uploadWorkbook(withData = true, withSheet = true): File {
  const row = Array(57).fill("");
  row[2] = "02022"; row[3] = "02023"; row[13] = "ROSSI MARIO"; row[14] = "VIA ROMA 1";
  row[16] = "URAS"; row[20] = "RSSMRA80A01H501Z"; row[21] = "120242223"; row[56] = "2023";
  const book = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(book, XLSX.utils.aoa_to_sheet(withData ? [Array(57).fill(""), row] : [["Header"]]), withSheet ? "Dati" : "Altro");
  const bytes = XLSX.write(book, { type: "array", bookType: "xlsx" });
  const file = new File([bytes], "operatori.xlsx", { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  Object.defineProperty(file, "arrayBuffer", { configurable: true, value: async () => bytes });
  return file;
}

describe("RegisteredMailReconciliation", () => {
  beforeEach(() => {
    mocks.preview.mockReset().mockResolvedValue(preview());
    mocks.update.mockReset().mockResolvedValue({});
    mocks.check.mockReset().mockResolvedValue({ verified: true, reason: "Riferimenti inCASS e contribuente coerenti" });
    Object.defineProperty(globalThis, "crypto", { configurable: true, value: { subtle: { digest: async () => new Uint8Array(32).buffer } } });
  });

  test("keeps workbook local and records explicit per-mail confirmation", async () => {
    render(<RegisteredMailReconciliation canEdit token="token" />);
    expect(await screen.findByText(/Riconciliazione assistita/)).toBeInTheDocument();
    await waitFor(() => expect(mocks.preview).toHaveBeenCalledWith("token", "2026-09-29T00:00:00+02:00"));
    fireEvent.change(screen.getByLabelText(/Seleziona Excel operatori/), { target: { files: [uploadWorkbook()] } });
    expect(await screen.findByText(/1 righe operative/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /ROSSI MARIO.*invio shipment-1/ }));
    expect(screen.getByText(/Riga 2.*cumulativo/)).toBeInTheDocument();
    expect(screen.getByText("Nominativo concordante")).toBeInTheDocument();
    expect(await screen.findByText("Riferimenti inCASS e contribuente coerenti")).toBeInTheDocument();
    const confirm = screen.getByRole("button", { name: "Associa entrambi gli avvisi" });
    expect(confirm).toBeDisabled();
    fireEvent.click(screen.getByLabelText(/Ho verificato che questo invio/));
    fireEvent.click(confirm);
    await waitFor(() => expect(mocks.update).toHaveBeenCalledWith("token", "mail-1", {
      avviso_ids: ["a22", "a23"],
      review_evidence: { source_sha256: "0".repeat(64), sheet: "Dati", row: 2, ref_2022: "02022", ref_2023: "02023" },
    }));
    expect(mocks.preview).toHaveBeenCalledTimes(2);
  });

  test("rejects an incompatible workbook and does not save", async () => {
    render(<RegisteredMailReconciliation canEdit token="token" />);
    fireEvent.change(screen.getByLabelText(/Seleziona Excel operatori/), { target: { files: [uploadWorkbook(false, false)] } });
    expect(await screen.findByRole("alert")).toHaveTextContent("Il foglio Dati non e presente");
    expect(mocks.update).not.toHaveBeenCalled();
  });

  test("hides the review queue without edit permission", () => {
    render(<RegisteredMailReconciliation canEdit={false} token="token" />);
    expect(screen.queryByText("Riconciliazione assistita")).not.toBeInTheDocument();
    expect(mocks.preview).not.toHaveBeenCalled();
  });

  test("keeps association blocked when inCASS cannot validate references", async () => {
    mocks.check.mockResolvedValue({ verified: false, reason: "Riferimento inCASS 2023 non trovato" });
    render(<RegisteredMailReconciliation canEdit token="token" />);
    await screen.findByText(/ROSSI MARIO/);
    fireEvent.change(screen.getByLabelText(/Seleziona Excel operatori/), { target: { files: [uploadWorkbook()] } });
    await screen.findByText(/1 righe operative/);
    fireEvent.click(screen.getByRole("button", { name: /ROSSI MARIO.*invio shipment-1/ }));
    expect(await screen.findByText("Riferimento inCASS 2023 non trovato")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Associa entrambi gli avvisi" })).not.toBeInTheDocument();
    expect(mocks.update).not.toHaveBeenCalled();
  });

  test("shows failed save and preserves the individual confirmation", async () => {
    mocks.update.mockRejectedValue(new Error("Conflitto concorrente"));
    render(<RegisteredMailReconciliation canEdit token="token" />);
    await screen.findByText(/ROSSI MARIO/);
    fireEvent.change(screen.getByLabelText(/Seleziona Excel operatori/), { target: { files: [uploadWorkbook()] } });
    await screen.findByText(/1 righe operative/);
    fireEvent.click(screen.getByRole("button", { name: /ROSSI MARIO.*invio shipment-1/ }));
    await screen.findByText("Riferimenti inCASS e contribuente coerenti");
    fireEvent.click(screen.getByLabelText(/Ho verificato che questo invio/));
    fireEvent.click(screen.getByRole("button", { name: "Associa entrambi gli avvisi" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Conflitto concorrente");
    expect(mocks.preview).toHaveBeenCalledTimes(1);
  });

  test("reports preview, reference and workbook errors without saving", async () => {
    mocks.preview.mockRejectedValueOnce(new Error("Anteprima non disponibile"));
    const view = render(<RegisteredMailReconciliation canEdit token="token" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Anteprima non disponibile");
    view.unmount();
    mocks.preview.mockResolvedValue(preview());
    const again = render(<RegisteredMailReconciliation canEdit token="token" />);
    await screen.findByText(/ROSSI MARIO/);
    fireEvent.change(screen.getByLabelText(/Seleziona Excel operatori/), { target: { files: [uploadWorkbook(false)] } });
    expect(await screen.findByRole("alert")).toHaveTextContent("Nessuna riga operativa");
    fireEvent.change(screen.getByLabelText(/Seleziona Excel operatori/), { target: { files: [uploadWorkbook()] } });
    await screen.findByText(/1 righe operative/);
    mocks.check.mockRejectedValueOnce(new Error("inCASS non raggiungibile"));
    fireEvent.click(screen.getByRole("button", { name: /ROSSI MARIO.*invio shipment-1/ }));
    expect(await screen.findByText("inCASS non raggiungibile")).toBeInTheDocument();
    expect(mocks.update).not.toHaveBeenCalled();
    again.unmount();
  });

  test("filters and pages the review queue without selecting an association", async () => {
    const items = Array.from({ length: 21 }, (_, index) => ({ ...item, mail_id: `mail-${index}`, source_shipment_id: `shipment-${index}` }));
    items.push({ ...item, mail_id: "other", classification: "custom", recipient_name: null, recipient_address: null, tracking_number: null, candidate_notices: [] });
    mocks.preview.mockResolvedValue(preview(items));
    render(<RegisteredMailReconciliation canEdit token="token" />);
    await waitFor(() => expect(screen.getByText(/20 di 21 mostrati/)).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Successiva" }));
    expect(screen.getByText(/1 di 21 mostrati/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Precedente" }));
    fireEvent.click(screen.getByRole("button", { name: /^Tutte / }));
    expect(screen.getByText(/20 di 22 mostrati/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Successiva" }));
    fireEvent.click(screen.getByRole("button", { name: /Destinatario non letto/ }));
    expect(screen.getByText("Indirizzo assente")).toBeInTheDocument();
    expect(screen.getByText(/Nessuna riga cumulativa univoca/)).toBeInTheDocument();
    expect(screen.getByText(/custom/)).toBeInTheDocument();
  });

  test("shows identity warnings, closes details, and ignores an empty file choice", async () => {
    mocks.preview.mockResolvedValue(preview([{ ...item, recipient_name: "ALTRO", candidate_notices: item.candidate_notices.map((notice) => ({ ...notice, nominativo: null })) }]));
    render(<RegisteredMailReconciliation canEdit token="token" />);
    await screen.findByText(/ALTRO/);
    fireEvent.change(screen.getByLabelText(/Seleziona Excel operatori/), { target: { files: [] } });
    fireEvent.change(screen.getByLabelText(/Seleziona Excel operatori/), { target: { files: [uploadWorkbook()] } });
    await screen.findByText(/1 righe operative/);
    const rowButton = screen.getByRole("button", { name: /ALTRO.*invio shipment-1/ });
    fireEvent.click(rowButton);
    expect(await screen.findByText("Nominativo da controllare")).toBeInTheDocument();
    expect(screen.getAllByText(/Nominativo assente/)).toHaveLength(2);
    fireEvent.click(rowButton);
    expect(screen.queryByText("Nominativo da controllare")).not.toBeInTheDocument();
  });

  test("uses safe fallback messages for unexpected failures", async () => {
    mocks.preview.mockRejectedValueOnce("bad");
    const first = render(<RegisteredMailReconciliation canEdit token="token" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Anteprima non disponibile");
    first.unmount();
    mocks.preview.mockResolvedValue(preview());
    const second = render(<RegisteredMailReconciliation canEdit token="token" />);
    await screen.findByText(/ROSSI MARIO/);
    const broken = uploadWorkbook();
    Object.defineProperty(broken, "arrayBuffer", { value: async () => { throw "bad"; } });
    fireEvent.change(screen.getByLabelText(/Seleziona Excel operatori/), { target: { files: [broken] } });
    expect(await screen.findByRole("alert")).toHaveTextContent("Impossibile leggere il file Excel");
    fireEvent.change(screen.getByLabelText(/Seleziona Excel operatori/), { target: { files: [uploadWorkbook()] } });
    await screen.findByText(/1 righe operative/);
    mocks.check.mockRejectedValueOnce("bad");
    const rowButton = screen.getByRole("button", { name: /ROSSI MARIO.*invio shipment-1/ });
    fireEvent.click(rowButton);
    expect(await screen.findByText("Verifica inCASS non disponibile")).toBeInTheDocument();
    fireEvent.click(rowButton);
    mocks.update.mockRejectedValueOnce("bad");
    fireEvent.click(rowButton);
    await screen.findByText("Riferimenti inCASS e contribuente coerenti");
    fireEvent.click(screen.getByLabelText(/Ho verificato che questo invio/));
    fireEvent.click(screen.getByRole("button", { name: "Associa entrambi gli avvisi" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Associazione non salvata");
    second.unmount();
  });

  test("drops late reference responses after the review closes", async () => {
    let resolveCheck: ((result: { verified: boolean; reason: string }) => void) | undefined;
    let rejectCheck: ((cause: unknown) => void) | undefined;
    mocks.check.mockImplementationOnce(() => new Promise((resolve) => { resolveCheck = resolve; }))
      .mockImplementationOnce(() => new Promise((_, reject) => { rejectCheck = reject; }));
    render(<RegisteredMailReconciliation canEdit token="token" />);
    await screen.findByText(/ROSSI MARIO/);
    fireEvent.change(screen.getByLabelText(/Seleziona Excel operatori/), { target: { files: [uploadWorkbook()] } });
    await screen.findByText(/1 righe operative/);
    const rowButton = screen.getByRole("button", { name: /ROSSI MARIO.*invio shipment-1/ });
    fireEvent.click(rowButton);
    await waitFor(() => expect(mocks.check).toHaveBeenCalledTimes(1));
    fireEvent.click(rowButton);
    resolveCheck?.({ verified: true, reason: "late" });
    fireEvent.click(rowButton);
    await waitFor(() => expect(mocks.check).toHaveBeenCalledTimes(2));
    fireEvent.click(rowButton);
    rejectCheck?.("late");
    expect(mocks.update).not.toHaveBeenCalled();
  });
});
