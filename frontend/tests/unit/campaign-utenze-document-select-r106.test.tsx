import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import UtenzeSubjectDetailPage from "@/app/utenze/[id]/page";
import type { AnagraficaDocument, AnagraficaSubjectDetail, CurrentUser } from "@/types/api";

const api = vi.hoisted(() => ({
  router: { push: vi.fn(), replace: vi.fn() },
  getStoredAccessToken: vi.fn(), clearStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn<typeof import("@/lib/api").getCurrentUser>(),
  getMyPermissions: vi.fn<typeof import("@/lib/api").getMyPermissions>(),
  getUtenzeSubject: vi.fn<typeof import("@/lib/api").getUtenzeSubject>(),
  getUtenzeSubjectPaymentNotices: vi.fn<typeof import("@/lib/api").getUtenzeSubjectPaymentNotices>(),
  getUtenzeSubjectNasImportStatus: vi.fn<typeof import("@/lib/api").getUtenzeSubjectNasImportStatus>(),
  getUtenzeSubjectNasCandidates: vi.fn<typeof import("@/lib/api").getUtenzeSubjectNasCandidates>(),
  updateUtenzeSubject: vi.fn<typeof import("@/lib/api").updateUtenzeSubject>(),
  updateUtenzeDocument: vi.fn<typeof import("@/lib/api").updateUtenzeDocument>(),
  classifyUtenzeDocumentContent: vi.fn<typeof import("@/lib/api").classifyUtenzeDocumentContent>(),
  deleteUtenzeDocument: vi.fn<typeof import("@/lib/api").deleteUtenzeDocument>(),
  uploadUtenzeSubjectDocument: vi.fn<typeof import("@/lib/api").uploadUtenzeSubjectDocument>(),
  importUtenzeSubjectFromNas: vi.fn<typeof import("@/lib/api").importUtenzeSubjectFromNas>(),
  createElaborazioneRichiesta: vi.fn<typeof import("@/lib/api").createElaborazioneRichiesta>(),
  downloadUtenzeDocumentBlob: vi.fn<typeof import("@/lib/api").downloadUtenzeDocumentBlob>(),
  downloadCatastoDocumentBlob: vi.fn<typeof import("@/lib/api").downloadCatastoDocumentBlob>(),
  sendPresenceHeartbeat: vi.fn<typeof import("@/lib/api").sendPresenceHeartbeat>(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "subject-r106" }), useRouter: () => api.router,
  useSearchParams: () => new URLSearchParams(window.location.search),
  usePathname: () => window.location.pathname,
}));
vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: api.getStoredAccessToken, clearStoredAccessToken: api.clearStoredAccessToken,
}));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getCurrentUser: api.getCurrentUser, getMyPermissions: api.getMyPermissions,
  getUtenzeSubject: api.getUtenzeSubject,
  getUtenzeSubjectPaymentNotices: api.getUtenzeSubjectPaymentNotices,
  getUtenzeSubjectNasImportStatus: api.getUtenzeSubjectNasImportStatus,
  getUtenzeSubjectNasCandidates: api.getUtenzeSubjectNasCandidates,
  updateUtenzeSubject: api.updateUtenzeSubject, updateUtenzeDocument: api.updateUtenzeDocument,
  classifyUtenzeDocumentContent: api.classifyUtenzeDocumentContent,
  deleteUtenzeDocument: api.deleteUtenzeDocument,
  uploadUtenzeSubjectDocument: api.uploadUtenzeSubjectDocument,
  importUtenzeSubjectFromNas: api.importUtenzeSubjectFromNas,
  createElaborazioneRichiesta: api.createElaborazioneRichiesta,
  downloadUtenzeDocumentBlob: api.downloadUtenzeDocumentBlob,
  downloadCatastoDocumentBlob: api.downloadCatastoDocumentBlob,
  sendPresenceHeartbeat: api.sendPresenceHeartbeat,
}));

const token = "r106-select-token";
const timestamp = "2026-10-15T10:00:00Z";
const filename = "select-isolation-r106.pdf";

function userFixture(): CurrentUser {
  return {
    id: 106, username: "r106", email: "r106@example.invalid", role: "viewer", is_active: true,
    module_accessi: false, module_rete: false, module_inventario: false, module_catasto: false,
    module_utenze: true, module_operazioni: false, module_riordino: false,
    module_ruolo: false, module_presenze: false, enabled_modules: ["utenze"],
  };
}

function documentFixture(overrides: Partial<AnagraficaDocument> = {}): AnagraficaDocument {
  return {
    id: "document-r106", filename, relative_path: filename, nas_path: `/archive/${filename}`,
    extension: ".pdf", is_pdf: true, doc_type: "altro", classification_source: "manual",
    smart_category: "other", smart_category_label: "Altro da classificare", smart_priority: 10,
    smart_confidence: 0, smart_reason: null, content_classification_status: "not_started",
    content_category: null, content_category_label: null, content_confidence: null,
    content_reason: null, content_excerpt: null, content_classification_source: null,
    content_classified_at: null, content_classification_error: null, warnings: [], ...overrides,
  };
}

function subjectFixture(document: AnagraficaDocument): AnagraficaSubjectDetail {
  return {
    id: "subject-r106", subject_type: "company", status: "active", source_system: "campaign-r106",
    source_external_id: null, source_name_raw: "Azienda R106", nas_folder_path: null,
    nas_folder_letter: null, requires_review: false, imported_at: null,
    created_at: timestamp, updated_at: timestamp, person: null,
    company: {
      subject_id: "subject-r106", ragione_sociale: "Azienda R106", partita_iva: "12345678901",
      codice_fiscale: null, forma_giuridica: null, sede_legale: null, comune_sede: null,
      cap: null, email_pec: null, telefono: null, note: null, created_at: timestamp, updated_at: timestamp,
    },
    documents: [document], catasto_documents: [], audit_log: [],
  };
}

function typeSelect() {
  const collection = screen.getByRole("searchbox", { name: "Cerca documenti associati" }).closest("article");
  if (!(collection instanceof HTMLElement)) throw new Error("Missing actual document collection article");
  const row = within(collection).getByText(filename, { exact: true }).closest('[role="button"]');
  if (!(row instanceof HTMLElement)) throw new Error("Missing actual document row");
  return within(row).getByRole("combobox");
}

function enableEditing() {
  fireEvent.click(screen.getByRole("button", { name: "Modifica" }));
  fireEvent.click(screen.getByRole("button", { name: "Abilita modifica" }));
  expect(screen.getByText("Modalità modifica attiva")).toBeVisible();
  expect(typeSelect()).toBeEnabled();
}

async function ready(subject: AnagraficaSubjectDetail) {
  api.getUtenzeSubject.mockResolvedValue(subject);
  render(<UtenzeSubjectDetailPage />);
  await screen.findByText("R106 NAS pronto");
  await act(async () => {});
  expect(typeSelect()).toBeDisabled();
  enableEditing();
}

function expectNoPreviewOrOtherOperations() {
  expect(screen.queryByText("Anteprima documento", { exact: true })).not.toBeInTheDocument();
  expect(screen.queryByText("Caricamento anteprima...", { exact: true })).not.toBeInTheDocument();
  expect(screen.queryByTitle(filename, { exact: true })).not.toBeInTheDocument();
  expect(document.querySelector('[href^="blob:"], [src^="blob:"]')).toBeNull();
  for (const request of [
    api.downloadUtenzeDocumentBlob, api.downloadCatastoDocumentBlob,
    api.getUtenzeSubjectNasCandidates, api.updateUtenzeSubject,
    api.classifyUtenzeDocumentContent, api.deleteUtenzeDocument,
    api.uploadUtenzeSubjectDocument, api.importUtenzeSubjectFromNas, api.createElaborazioneRichiesta,
  ]) {
    expect(request).not.toHaveBeenCalled();
  }
  expect(api.router.push).not.toHaveBeenCalled();
  expect(api.router.replace).not.toHaveBeenCalled();
}

beforeEach(() => {
  vi.resetAllMocks();
  window.history.replaceState(null, "", "/utenze/subject-r106?embedded=1");
  api.getStoredAccessToken.mockReturnValue(token);
  api.getCurrentUser.mockResolvedValue(userFixture());
  api.getMyPermissions.mockResolvedValue({ sections: [], granted_keys: [] });
  api.getUtenzeSubjectPaymentNotices.mockResolvedValue([]);
  api.getUtenzeSubjectNasImportStatus.mockResolvedValue({
    can_import_from_nas: false, missing_in_nas: true, matched_folder_path: null,
    matched_folder_name: null, total_files_in_nas: 0, pending_files_in_nas: 0, message: "R106 NAS pronto",
  });
  api.sendPresenceHeartbeat.mockResolvedValue({ ok: true, last_seen_at: timestamp });
  api.downloadUtenzeDocumentBlob.mockResolvedValue(new Blob(["%PDF-1.4 R106"], { type: "application/pdf" }));
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("R106 real enabled document-type select click isolation", () => {
  test("clicking the enabled select alone preserves type and input without preview, mutation or reload", async () => {
    const subject = subjectFixture(documentFixture());
    const originalSubject = JSON.stringify(subject);
    await ready(subject);
    const select = typeSelect();
    expect(select).toHaveValue("altro");
    await act(async () => { fireEvent.click(select); });
    expect(select).toBeEnabled();
    expect(select).toHaveValue("altro");
    expect(screen.getByText("Modalità modifica attiva")).toBeVisible();
    expect(api.updateUtenzeDocument).not.toHaveBeenCalled();
    expect(api.getUtenzeSubject).toHaveBeenCalledExactlyOnceWith(token, "subject-r106");
    expect(api.getUtenzeSubjectPaymentNotices).toHaveBeenCalledExactlyOnceWith(token, "subject-r106");
    expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledExactlyOnceWith(token, "subject-r106");
    expectNoPreviewOrOtherOperations();
    expect(JSON.stringify(subject)).toBe(originalSubject);
  });

  test("click then selection changes type once, reloads, and the refreshed enabled select still isolates clicks", async () => {
    await ready(subjectFixture(documentFixture()));
    const updatedDocument = documentFixture({
      doc_type: "contratto", smart_category: "contract", smart_category_label: "Contratti e convenzioni", smart_priority: 50,
    });
    api.updateUtenzeDocument.mockResolvedValueOnce(updatedDocument);
    api.getUtenzeSubject.mockResolvedValueOnce(subjectFixture(updatedDocument));
    await act(async () => { fireEvent.click(typeSelect()); });
    expect(api.updateUtenzeDocument).not.toHaveBeenCalled();
    expect(api.getUtenzeSubject).toHaveBeenCalledTimes(1);
    expectNoPreviewOrOtherOperations();
    fireEvent.change(typeSelect(), { target: { value: "contratto" } });
    await waitFor(() => expect(typeSelect()).toBeDisabled());
    await waitFor(() => expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledTimes(2));
    expect(typeSelect()).toHaveValue("contratto");
    expect(api.updateUtenzeDocument).toHaveBeenCalledExactlyOnceWith(token, "document-r106", { doc_type: "contratto" });
    expect(api.getUtenzeSubject.mock.calls).toEqual([[token, "subject-r106"], [token, "subject-r106"]]);
    expect(api.updateUtenzeDocument.mock.invocationCallOrder[0]).toBeLessThan(api.getUtenzeSubject.mock.invocationCallOrder[1]);
    expect(api.getUtenzeSubjectPaymentNotices).toHaveBeenCalledExactlyOnceWith(token, "subject-r106");
    expectNoPreviewOrOtherOperations();
    enableEditing();
    await act(async () => { fireEvent.click(typeSelect()); });
    expect(typeSelect()).toBeEnabled();
    expect(typeSelect()).toHaveValue("contratto");
    expect(api.updateUtenzeDocument).toHaveBeenCalledTimes(1);
    expect(api.getUtenzeSubject).toHaveBeenCalledTimes(2);
    expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledTimes(2);
    expectNoPreviewOrOtherOperations();
  });
});
