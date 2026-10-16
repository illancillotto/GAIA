import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { UtenzeSubjectsSection } from "@/components/utenze/utenze-subjects-section";
import type { UtenzeDocument, UtenzeSubjectDetail, UtenzeSubjectListItem } from "@/types/api";

const api = vi.hoisted(() => ({
  getUtenzeSubjects: vi.fn(),
  getUtenzeSubject: vi.fn(),
  getUtenzeSubjectAuditLog: vi.fn(),
  downloadUtenzeDocumentBlob: vi.fn(),
  getUtenzeSubjectPaymentNotices: vi.fn(),
  listCapacitasInCassSyncJobs: vi.fn(),
  getAvvisiBySubject: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getUtenzeSubjects: api.getUtenzeSubjects,
  getUtenzeSubject: api.getUtenzeSubject,
  getUtenzeSubjectAuditLog: api.getUtenzeSubjectAuditLog,
  downloadUtenzeDocumentBlob: api.downloadUtenzeDocumentBlob,
  getUtenzeSubjectPaymentNotices: api.getUtenzeSubjectPaymentNotices,
  listCapacitasInCassSyncJobs: api.listCapacitasInCassSyncJobs,
}));
vi.mock("@/lib/ruolo-api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/ruolo-api")>()),
  getAvvisiBySubject: api.getAvvisiBySubject,
}));

const listItem: UtenzeSubjectListItem = {
  id: "subject-1",
  subject_type: "person",
  status: "active",
  source_system: "nas",
  source_external_id: null,
  source_name_raw: "Rossi_Mario_RSSMRA80A01H501U",
  display_name: "Rossi Mario",
  codice_fiscale: "RSSMRA80A01H501U",
  partita_iva: null,
  nas_folder_path: "/archive/R/Rossi_Mario",
  nas_folder_letter: "R",
  requires_review: false,
  imported_at: null,
  document_count: 1,
  created_at: "2026-10-01T08:00:00Z",
  updated_at: "2026-10-02T08:00:00Z",
};

const pdfDocument = {
  id: "doc-1",
  filename: "report.pdf",
  relative_path: "report.pdf",
  nas_path: "/archive/R/Rossi_Mario/report.pdf",
  extension: ".pdf",
  is_pdf: true,
  doc_type: "visura",
  classification_source: "archive",
  smart_category: "cadastral",
  smart_category_label: "Visure",
  smart_priority: 60,
  smart_confidence: 0.85,
  smart_reason: null,
  content_classification_status: "not_started",
  content_category: null,
  content_category_label: null,
  content_confidence: null,
  content_reason: null,
  content_excerpt: null,
  content_classification_source: null,
  content_classified_at: null,
  content_classification_error: null,
  warnings: [],
} as UtenzeDocument;

const subjectDetail: UtenzeSubjectDetail = {
  id: "subject-1",
  subject_type: "person",
  status: "active",
  source_system: "nas",
  source_external_id: null,
  source_name_raw: "Rossi_Mario_RSSMRA80A01H501U",
  nas_folder_path: "/archive/R/Rossi_Mario",
  nas_folder_letter: "R",
  requires_review: false,
  imported_at: null,
  created_at: "2026-10-01T08:00:00Z",
  updated_at: "2026-10-02T08:00:00Z",
  person: {
    subject_id: "subject-1",
    cognome: "Rossi",
    nome: "Mario",
    codice_fiscale: "RSSMRA80A01H501U",
    anpr_id: null,
    stato_anpr: null,
    data_decesso: null,
    luogo_decesso_comune: null,
    last_anpr_check_at: null,
    last_c030_check_at: null,
    data_nascita: null,
    comune_nascita: "Oristano",
    indirizzo: null,
    comune_residenza: "Cabras",
    cap: null,
    email: null,
    telefono: null,
    note: null,
    created_at: "2026-10-01T08:00:00Z",
    updated_at: "2026-10-02T08:00:00Z",
  },
  company: null,
  documents: [pdfDocument],
  audit_log: [],
  catasto_documents: [],
};

function closeButtonOf(dialog: HTMLElement): HTMLElement {
  return within(dialog).getByRole("button", { name: "Chiudi" });
}

async function renderLoaded() {
  render(<UtenzeSubjectsSection token="token" />);
  await waitFor(() => expect(screen.queryByText("Caricamento utenti in corso.")).not.toBeInTheDocument());
}

// The opener is focused explicitly before the click, as a browser does for a focusable control.
function focusAndClick(element: HTMLElement) {
  element.focus();
  fireEvent.click(element);
}

async function openSubjectDialog(): Promise<{ opener: HTMLElement; dialog: HTMLElement }> {
  const opener = screen.getByPlaceholderText("Cerca per nome, cognome o CF...");
  opener.focus();
  fireEvent.click(screen.getByText("Rossi Mario"));
  const dialog = await screen.findByRole("dialog", { name: "Vista rapida del registro" });
  await within(dialog).findByText("report.pdf");
  return { opener, dialog };
}

beforeEach(() => {
  vi.clearAllMocks();
  Object.defineProperty(URL, "createObjectURL", { configurable: true, writable: true, value: vi.fn(() => "blob:preview-1") });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, writable: true, value: vi.fn() });
  api.getUtenzeSubjects.mockResolvedValue({ items: [listItem], total: 1, page: 1, page_size: 20 });
  api.getUtenzeSubject.mockResolvedValue(subjectDetail);
  api.getUtenzeSubjectAuditLog.mockResolvedValue([]);
  api.downloadUtenzeDocumentBlob.mockResolvedValue(new Blob(["%PDF"]));
  api.getUtenzeSubjectPaymentNotices.mockResolvedValue([]);
  api.listCapacitasInCassSyncJobs.mockResolvedValue([]);
  api.getAvvisiBySubject.mockResolvedValue([]);
});

afterEach(() => {
  cleanup();
});

describe("UtenzeSubjectsSection overlays accessibility (R139)", () => {
  test("subject detail overlay is a labelled modal dialog that takes and returns focus", async () => {
    await renderLoaded();
    const { opener, dialog } = await openSubjectDialog();

    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAccessibleName("Vista rapida del registro");
    expect(document.getElementById("utenze-subject-detail-title")).toHaveTextContent("Vista rapida del registro");
    expect(closeButtonOf(dialog)).toHaveFocus();

    fireEvent.click(closeButtonOf(dialog));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });

  test("subject detail overlay closed with Escape returns focus to the opener", async () => {
    await renderLoaded();
    const { opener } = await openSubjectDialog();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });

  test("document preview overlay is a labelled modal dialog that takes and returns focus", async () => {
    await renderLoaded();
    const { dialog: subjectDialog } = await openSubjectDialog();
    const documentButton = within(subjectDialog).getByRole("button", { name: /report\.pdf/ });

    focusAndClick(documentButton);
    const preview = await screen.findByRole("dialog", { name: "Anteprima documento" });
    expect(preview).toHaveAttribute("aria-modal", "true");
    expect(document.getElementById("utenze-document-preview-title")).toHaveTextContent("Anteprima documento");
    expect(closeButtonOf(preview)).toHaveFocus();
    await within(preview).findByTitle("report.pdf");

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Anteprima documento" })).not.toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Vista rapida del registro" })).toBeInTheDocument();
    expect(documentButton).toHaveFocus();
  });

  test("document preview overlay closed with its button returns focus to the document", async () => {
    await renderLoaded();
    const { dialog: subjectDialog } = await openSubjectDialog();
    const documentButton = within(subjectDialog).getByRole("button", { name: /report\.pdf/ });

    focusAndClick(documentButton);
    const preview = await screen.findByRole("dialog", { name: "Anteprima documento" });
    await within(preview).findByTitle("report.pdf");

    fireEvent.click(closeButtonOf(preview));
    expect(screen.queryByRole("dialog", { name: "Anteprima documento" })).not.toBeInTheDocument();
    expect(documentButton).toHaveFocus();
  });

  test("stacked preview over subject restores each opener on successive Escapes", async () => {
    await renderLoaded();
    const { opener: subjectOpener, dialog: subjectDialog } = await openSubjectDialog();
    expect(closeButtonOf(subjectDialog)).toHaveFocus();
    const documentButton = within(subjectDialog).getByRole("button", { name: /report\.pdf/ });

    focusAndClick(documentButton);
    const preview = await screen.findByRole("dialog", { name: "Anteprima documento" });
    expect(closeButtonOf(preview)).toHaveFocus();
    await within(preview).findByTitle("report.pdf");

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Anteprima documento" })).not.toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Vista rapida del registro" })).toBeInTheDocument();
    expect(documentButton).toHaveFocus();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(subjectOpener).toHaveFocus();
  });

  test("history overlay is a labelled modal dialog that takes and returns focus", async () => {
    await renderLoaded();
    const historyButton = screen.getByTitle("Visualizza storico modifiche");

    focusAndClick(historyButton);
    const history = await screen.findByRole("dialog", { name: "Storico modifiche Rossi Mario" });
    expect(history).toHaveAttribute("aria-modal", "true");
    expect(document.getElementById("utenze-subject-history-kicker")).toHaveTextContent("Storico modifiche");
    expect(document.getElementById("utenze-subject-history-title")).toHaveTextContent("Rossi Mario");
    expect(closeButtonOf(history)).toHaveFocus();
    await within(history).findByText("Nessuna voce di storico disponibile per questo utente.");
    expect(screen.queryByRole("dialog", { name: "Vista rapida del registro" })).not.toBeInTheDocument();

    fireEvent.click(closeButtonOf(history));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(historyButton).toHaveFocus();
  });
});
