import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { RegisteredMailCards } from "@/components/ruolo/registered-mail-cards";
import type { RegisteredMailCard } from "@/lib/registered-mail-documents-api";
import type { RuoloTributiRegisteredMailResponse } from "@/types/ruolo";

const mocks = vi.hoisted(() => ({ listRegisteredMailCards: vi.fn(), uploadRegisteredMailCard: vi.fn(), downloadRegisteredMailCard: vi.fn() }));
vi.mock("@/lib/registered-mail-documents-api", () => mocks);
const card: RegisteredMailCard = { id: "card-1", document_id: "doc-1", subject_id: "subject-1", filename: "card.pdf", tracking_number: "619592000378", sha256: "a".repeat(64), scanned_on: "2025-09-12", source_reference: null, created_at: "2026-10-02" };
const mail = { id: "mail-1", subject_id: "subject-1", avviso_id: "notice-1", match_status: "matched", anomaly_key: null, recipient_name: "MARTUCCI CARLA", tracking_number: "619592000378" } as RuoloTributiRegisteredMailResponse;

beforeEach(() => {
  vi.clearAllMocks();
  mocks.listRegisteredMailCards.mockResolvedValue([]);
  mocks.uploadRegisteredMailCard.mockResolvedValue(card);
  mocks.downloadRegisteredMailCard.mockResolvedValue(new Blob(["%PDF-"]));
  URL.createObjectURL = vi.fn(() => "blob:card");
  URL.revokeObjectURL = vi.fn();
});

function open(overrides: Partial<RuoloTributiRegisteredMailResponse> = {}, canEdit = true) {
  const result = render(<RegisteredMailCards canEdit={canEdit} mail={{ ...mail, ...overrides }} token="token" />);
  fireEvent.click(screen.getByRole("button", { name: "Cartoline scansionate" }));
  return result;
}

async function fill() {
  await screen.findByText("Nessuna cartolina salvata.");
  fireEvent.change(screen.getByLabelText("PDF cartolina (massimo 20 MiB)"), { target: { files: [new File(["%PDF-"], "card.pdf")] } });
  fireEvent.change(screen.getByLabelText("Data di scansione"), { target: { value: "2025-09-12" } });
  fireEvent.click(screen.getByRole("checkbox"));
}

test("no token exposes neither actions nor requests", () => {
  const { container } = render(<RegisteredMailCards canEdit mail={mail} token={null} />);
  expect(container).toBeEmptyDOMElement();
  expect(mocks.listRegisteredMailCards).not.toHaveBeenCalled();
});

test("upload, preview, authenticated download and object URL cleanup", async () => {
  open();
  expect(screen.getByRole("status")).toHaveTextContent("Caricamento cartoline");
  await fill();
  fireEvent.click(screen.getByRole("button", { name: "Salva cartolina" }));
  expect(await screen.findByTitle("Cartolina card.pdf")).toHaveAttribute("src", "blob:card");
  expect(screen.getByRole("link", { name: "Scarica card.pdf" })).toHaveAttribute("download", "card.pdf");
  expect(mocks.uploadRegisteredMailCard).toHaveBeenCalledWith("token", "mail-1", expect.any(File), mail.tracking_number, "2025-09-12");
  fireEvent.click(screen.getByRole("button", { name: "Chiudi cartoline" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:card");
});

test("existing cards are previewable without editing", async () => {
  mocks.listRegisteredMailCards.mockResolvedValue([card]);
  open({}, false);
  fireEvent.click(await screen.findByRole("button", { name: "card.pdf · scansione 2025-09-12" }));
  expect(await screen.findByTitle("Cartolina card.pdf")).toBeInTheDocument();
  expect(screen.queryByLabelText("Data di scansione")).not.toBeInTheDocument();
});

test.each([{ match_status: "unmatched" }, { avviso_id: null }, { subject_id: null }, { anomaly_key: "ambiguous" }])("unconfirmed or anomalous identity does not expose upload: %j", async (overrides) => {
  open(overrides);
  await screen.findByText("Nessuna cartolina salvata.");
  expect(screen.queryByRole("button", { name: "Salva cartolina" })).not.toBeInTheDocument();
});

test("missing inputs never upload even if form submission is forced", async () => {
  open({ tracking_number: null });
  await screen.findByText("Nessuna cartolina salvata.");
  const button = screen.getByRole("button", { name: "Salva cartolina" });
  expect(button).toBeDisabled();
  fireEvent.submit(button.closest("form")!);
  fireEvent.change(screen.getByLabelText("PDF cartolina (massimo 20 MiB)"), { target: { files: [] } });
  fireEvent.change(screen.getByLabelText("PDF cartolina (massimo 20 MiB)"), { target: { files: [new File(["pdf"], "x.pdf")] } });
  fireEvent.submit(button.closest("form")!);
  fireEvent.change(screen.getByLabelText("Data di scansione"), { target: { value: "2025-09-12" } });
  fireEvent.submit(button.closest("form")!);
  expect(mocks.uploadRegisteredMailCard).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.submit(button.closest("form")!);
  await waitFor(() => expect(mocks.uploadRegisteredMailCard).toHaveBeenCalledWith("token", "mail-1", expect.any(File), "", "2025-09-12"));
});

test("idempotent response does not duplicate the card", async () => {
  mocks.listRegisteredMailCards.mockResolvedValue([card]);
  open();
  await screen.findByRole("button", { name: "card.pdf · scansione 2025-09-12" });
  fireEvent.change(screen.getByLabelText("PDF cartolina (massimo 20 MiB)"), { target: { files: [new File(["pdf"], "card.pdf")] } });
  fireEvent.change(screen.getByLabelText("Data di scansione"), { target: { value: "2025-09-12" } });
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Salva cartolina" }));
  await screen.findByTitle("Cartolina card.pdf");
  expect(screen.getAllByRole("button", { name: "card.pdf · scansione 2025-09-12" })).toHaveLength(1);
});

test.each([new Error("NAS offline"), "unknown"])("upload errors are visible and retry remains possible: %s", async (error) => {
  mocks.uploadRegisteredMailCard.mockRejectedValue(error);
  open();
  await fill();
  fireEvent.click(screen.getByRole("button", { name: "Salva cartolina" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(error instanceof Error ? error.message : "Operazione cartolina non riuscita");
  expect(screen.getByRole("button", { name: "Salva cartolina" })).toBeEnabled();
});

test("list errors and preview errors remain visible", async () => {
  mocks.listRegisteredMailCards.mockRejectedValue(new Error("List denied"));
  const result = open();
  expect(await screen.findByRole("alert")).toHaveTextContent("List denied");
  result.unmount();
  mocks.listRegisteredMailCards.mockResolvedValue([card]);
  mocks.downloadRegisteredMailCard.mockRejectedValue(new Error("PDF unavailable"));
  open();
  fireEvent.click(await screen.findByRole("button", { name: "card.pdf · scansione 2025-09-12" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("PDF unavailable");
});

test.each([true, false])("late list response after close is ignored, success=%s", async (success) => {
  let resolve!: (value: RegisteredMailCard[]) => void;
  let reject!: (reason: Error) => void;
  mocks.listRegisteredMailCards.mockReturnValue(new Promise((done, failed) => { resolve = done; reject = failed; }));
  open();
  fireEvent.click(screen.getByRole("button", { name: "Chiudi cartoline" }));
  await act(async () => { if (success) resolve([card]); else reject(new Error("late")); });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test.each([true, false])("late preview completion after close never leaks object URLs, success=%s", async (success) => {
  let resolve!: (value: Blob) => void;
  let reject!: (reason: Error) => void;
  mocks.downloadRegisteredMailCard.mockReturnValue(new Promise((done, failed) => { resolve = done; reject = failed; }));
  mocks.listRegisteredMailCards.mockResolvedValue([card]);
  open();
  fireEvent.click(await screen.findByRole("button", { name: "card.pdf · scansione 2025-09-12" }));
  expect(screen.getByRole("status")).toHaveTextContent("Caricamento anteprima");
  fireEvent.click(screen.getByRole("button", { name: "Chiudi cartoline" }));
  await act(async () => { if (success) resolve(new Blob(["pdf"])); else reject(new Error("late")); });
  expect(URL.createObjectURL).not.toHaveBeenCalled();
});

test("upload shows saving state while request is pending", async () => {
  let resolve!: (value: RegisteredMailCard) => void;
  mocks.uploadRegisteredMailCard.mockReturnValue(new Promise((done) => { resolve = done; }));
  open();
  await fill();
  fireEvent.click(screen.getByRole("button", { name: "Salva cartolina" }));
  expect(screen.getByRole("button", { name: "Salvataggio..." })).toBeDisabled();
  await act(async () => resolve(card));
  expect(await screen.findByTitle("Cartolina card.pdf")).toBeInTheDocument();
});
