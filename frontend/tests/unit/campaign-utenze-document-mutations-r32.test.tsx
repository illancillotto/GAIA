import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import UtenzeSubjectDetailPage from "@/app/utenze/[id]/page";
import type { AnagraficaDocument, AnagraficaSubjectDetail, AnagraficaSubjectNasImportStatus, CurrentUser } from "@/types/api";

const api = vi.hoisted(() => ({
  subjectId: "subject-1",
  router: { push: vi.fn(), replace: vi.fn() },
  getStoredAccessToken: vi.fn(), clearStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn(), getMyPermissions: vi.fn(),
  getUtenzeSubject: vi.fn(), getUtenzeSubjectPaymentNotices: vi.fn(),
  getUtenzeSubjectNasImportStatus: vi.fn(), updateUtenzeDocument: vi.fn(),
  classifyUtenzeDocumentContent: vi.fn(), deleteUtenzeDocument: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: api.subjectId }), useRouter: () => api.router,
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
  updateUtenzeDocument: api.updateUtenzeDocument,
  classifyUtenzeDocumentContent: api.classifyUtenzeDocumentContent,
  deleteUtenzeDocument: api.deleteUtenzeDocument,
}));

const token = "r32-document-token";
const classificationSuccess = "Classificazione contenutistica documento aggiornata.";

function userFixture(): CurrentUser {
  return {
    id: 32, username: "r32", email: "r32@example.invalid", role: "viewer", is_active: true,
    module_accessi: false, module_rete: false, module_inventario: false, module_catasto: false,
    module_utenze: true, module_operazioni: false, module_riordino: false,
    module_ruolo: false, module_presenze: false, enabled_modules: ["utenze"],
  };
}
function documentFixture(overrides: Partial<AnagraficaDocument> = {}): AnagraficaDocument {
  return {
    id: "document-32", filename: "mutation.pdf", relative_path: "mutation.pdf",
    nas_path: "/archive/mutation.pdf", extension: ".pdf", is_pdf: true,
    doc_type: "altro", classification_source: "manual", smart_category: "other",
    smart_category_label: "Altro", smart_priority: 10, smart_confidence: 0, smart_reason: null,
    content_classification_status: "not_started", content_category: null,
    content_category_label: null, content_confidence: null, content_reason: null,
    content_excerpt: null, content_classification_source: null, content_classified_at: null,
    content_classification_error: null, warnings: [], ...overrides,
  };
}
function subjectFixture(overrides: Partial<AnagraficaSubjectDetail> = {}): AnagraficaSubjectDetail {
  const id = overrides.id ?? "subject-1";
  return {
    id, subject_type: "company", status: "active", source_system: "campaign-r32",
    source_external_id: null, source_name_raw: `Azienda R32 ${id}`,
    nas_folder_path: null, nas_folder_letter: null, requires_review: false, imported_at: null,
    created_at: "2026-10-11T10:00:00Z", updated_at: "2026-10-11T10:00:00Z", person: null,
    company: {
      subject_id: id, ragione_sociale: `Azienda R32 ${id}`, partita_iva: "12345678901",
      codice_fiscale: null, forma_giuridica: null, sede_legale: null, comune_sede: null,
      cap: null, email_pec: null, telefono: null, note: null,
      created_at: "2026-10-11T10:00:00Z", updated_at: "2026-10-11T10:00:00Z",
    },
    documents: [documentFixture()], audit_log: [], catasto_documents: [], ...overrides,
  };
}
function statusFixture(): AnagraficaSubjectNasImportStatus {
  return {
    can_import_from_nas: false, missing_in_nas: true, matched_folder_path: null,
    matched_folder_name: null, total_files_in_nas: 0, pending_files_in_nas: 0,
    message: "R32 NAS ready",
  };
}
function deferred<Result>() {
  let resolve!: (value: Result) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<Result>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
async function resolveRequest<Result>(request: ReturnType<typeof deferred<Result>>, value: Result) {
  await act(async () => { request.resolve(value); });
}
async function ready(subject = subjectFixture()) {
  api.getUtenzeSubject.mockResolvedValueOnce(subject);
  const view = render(<UtenzeSubjectDetailPage />);
  await screen.findByText("R32 NAS ready");
  await act(async () => {});
  return view;
}
function enableEditing() {
  fireEvent.click(screen.getByRole("button", { name: "Modifica" }));
  fireEvent.click(screen.getByRole("button", { name: "Abilita modifica" }));
  expect(screen.getByText("Modalità modifica attiva")).toBeInTheDocument();
}
function documentRow(filename = "mutation.pdf") {
  const row = screen.getByText(filename).closest<HTMLElement>('[role="button"]');
  if (!row) throw new Error("Missing rendered document row");
  return within(row);
}
function typeSelect(filename = "mutation.pdf") { return documentRow(filename).getByRole("combobox"); }
function classify(filename = "mutation.pdf") {
  const button = documentRow(filename).getByRole("button", { name: "Analizza contenuto" });
  expect(button).toBeEnabled();
  fireEvent.click(button);
}
function deletionPanel() {
  const panel = screen.getByText("Cancellazione documento").parentElement?.parentElement;
  if (!panel) throw new Error("Missing public deletion panel");
  return within(panel);
}
function openDelete(filename = "mutation.pdf") {
  enableEditing();
  fireEvent.click(documentRow(filename).getByRole("button", { name: "Rimuovi" }));
  expect(deletionPanel().getByLabelText("Password")).toHaveValue("");
}
function setPassword(password: string) {
  const input = deletionPanel().getByLabelText("Password");
  expect(input).toBeEnabled();
  fireEvent.change(input, { target: { value: password } });
}
function confirmDelete() {
  const button = deletionPanel().getByRole("button", { name: "Elimina" });
  expect(button).toBeEnabled();
  fireEvent.click(button);
}
function expectDeleteBusy() {
  expect(deletionPanel().getByLabelText("Password")).toBeDisabled();
  expect(deletionPanel().getByRole("button", { name: "Annulla" })).toBeDisabled();
  expect(deletionPanel().getByRole("button", { name: "Eliminazione..." })).toBeDisabled();
}
function cancelDelete() {
  const button = deletionPanel().getByRole("button", { name: "Annulla" });
  expect(button).toBeEnabled();
  fireEvent.click(button);
}

beforeEach(() => {
  vi.resetAllMocks();
  api.subjectId = "subject-1";
  window.history.replaceState(null, "", "/utenze/subject-1?embedded=1");
  api.getStoredAccessToken.mockReturnValue(token);
  api.getCurrentUser.mockResolvedValue(userFixture());
  api.getMyPermissions.mockResolvedValue({ granted_keys: [] });
  api.getUtenzeSubject.mockImplementation(async (_token: string, id: string) => subjectFixture({ id }));
  api.getUtenzeSubjectPaymentNotices.mockResolvedValue([]);
  api.getUtenzeSubjectNasImportStatus.mockResolvedValue(statusFixture());
  api.updateUtenzeDocument.mockResolvedValue(documentFixture());
  api.classifyUtenzeDocumentContent.mockResolvedValue(documentFixture());
  api.deleteUtenzeDocument.mockResolvedValue(undefined);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("R32 original public document eligibility and type updates", () => {
  test("view mode permits classification but not type changes or deletion", async () => {
    await ready();
    expect(typeSelect()).toBeDisabled();
    expect(documentRow().getByRole("button", { name: "Analizza contenuto" })).toBeEnabled();
    expect(documentRow().queryByRole("button", { name: "Rimuovi" })).not.toBeInTheDocument();
    expect(api.updateUtenzeDocument).not.toHaveBeenCalled();
    expect(api.deleteUtenzeDocument).not.toHaveBeenCalled();
  });
  test("valid NAS-only document without persisted id has no mutation commands", async () => {
    await ready(subjectFixture({ documents: [documentFixture({ id: null })] }));
    enableEditing();
    expect(typeSelect()).toBeEnabled();
    fireEvent.change(typeSelect(), { target: { value: "contratto" } });
    expect(api.updateUtenzeDocument).not.toHaveBeenCalled();
    expect(documentRow().queryByRole("button", { name: "Analizza contenuto" })).not.toBeInTheDocument();
    expect(documentRow().queryByRole("button", { name: "Rimuovi" })).not.toBeInTheDocument();
  });
  test.each(["ingiunzione", "notifica", "estratto_debito", "pratica_interna", "visura", "corrispondenza", "contratto", "altro"])("type %s updates exact payload then hydrates subject", async (docType) => {
    const initialDocType = docType === "altro" ? "visura" : "altro";
    await ready(subjectFixture({ documents: [documentFixture({ doc_type: initialDocType })] }));
    enableEditing();
    expect(typeSelect()).toHaveValue(initialDocType);
    expect(initialDocType).not.toBe(docType);
    api.getUtenzeSubject.mockResolvedValueOnce(subjectFixture({ documents: [documentFixture({ doc_type: docType })] }));
    const beforeReload = api.getUtenzeSubject.mock.calls.length;
    fireEvent.change(typeSelect(), { target: { value: docType } });
    await waitFor(() => expect(typeSelect()).toBeDisabled());
    expect(typeSelect()).toHaveValue(docType);
    expect(api.updateUtenzeDocument).toHaveBeenCalledExactlyOnceWith(token, "document-32", { doc_type: docType });
    expect(api.getUtenzeSubject.mock.calls[beforeReload]).toEqual([token, "subject-1"]);
    expect(api.updateUtenzeDocument.mock.invocationCallOrder[0]).toBeLessThan(api.getUtenzeSubject.mock.invocationCallOrder[beforeReload]);
    expect(screen.queryByText("Modalità modifica attiva")).not.toBeInTheDocument();
    expect(screen.queryByText("Anteprima documento")).not.toBeInTheDocument();
  });
  test.each([
    ["api", new Error("type denied"), "type denied"],
    ["api", "offline", "Errore aggiornamento documento"],
    ["reload", new Error("type reload denied"), "type reload denied"],
    ["reload", null, "Errore aggiornamento documento"],
  ])("type %s failure preserves editing and current document (%s)", async (phase, reason, message) => {
    await ready(); enableEditing();
    const beforeReload = api.getUtenzeSubject.mock.calls.length;
    if (phase === "api") api.updateUtenzeDocument.mockRejectedValueOnce(reason);
    else api.getUtenzeSubject.mockRejectedValueOnce(reason);
    fireEvent.change(typeSelect(), { target: { value: "contratto" } });
    await screen.findByText(message as string);
    expect(typeSelect()).toBeEnabled();
    expect(typeSelect()).toHaveValue("altro");
    expect(api.getUtenzeSubject).toHaveBeenCalledTimes(beforeReload + (phase === "reload" ? 1 : 0));
  });
  test("type request has no busy lock and preserves previous feedback until hydration", async () => {
    await ready();
    classify(); await screen.findByText(classificationSuccess);
    enableEditing();
    const request = deferred<AnagraficaDocument>();
    api.updateUtenzeDocument.mockReturnValueOnce(request.promise);
    fireEvent.change(typeSelect(), { target: { value: "visura" } });
    expect(typeSelect()).toBeEnabled();
    expect(screen.getByText(classificationSuccess)).toBeInTheDocument();
    await resolveRequest(request, documentFixture({ doc_type: "visura" }));
    await waitFor(() => expect(typeSelect()).toBeDisabled());
    expect(screen.getByText(classificationSuccess)).toBeInTheDocument();
  });
  test("pending type command reloads captured route after real route prop transition", async () => {
    const view = await ready(); enableEditing();
    const request = deferred<AnagraficaDocument>();
    api.updateUtenzeDocument.mockReturnValueOnce(request.promise);
    fireEvent.change(typeSelect(), { target: { value: "visura" } });
    api.subjectId = "subject-2";
    window.history.replaceState(null, "", "/utenze/subject-2?embedded=1");
    view.rerender(<UtenzeSubjectDetailPage />);
    await waitFor(() => expect(api.getUtenzeSubject).toHaveBeenLastCalledWith(token, "subject-2"));
    await act(async () => {});
    await resolveRequest(request, documentFixture());
    expect(api.getUtenzeSubject).toHaveBeenLastCalledWith(token, "subject-1");
    expect(api.updateUtenzeDocument).toHaveBeenCalledExactlyOnceWith(token, "document-32", { doc_type: "visura" });
  });
});

describe("R32 original public content classification", () => {
  test("classification stays busy through reload and renders hydrated content", async () => {
    await ready();
    const request = deferred<AnagraficaDocument>();
    const reload = deferred<AnagraficaSubjectDetail>();
    api.classifyUtenzeDocumentContent.mockReturnValueOnce(request.promise);
    api.getUtenzeSubject.mockReturnValueOnce(reload.promise);
    const beforeReload = api.getUtenzeSubject.mock.calls.length;
    classify();
    expect(documentRow().getByRole("button", { name: "Analisi..." })).toBeDisabled();
    expect(api.getUtenzeSubject).toHaveBeenCalledTimes(beforeReload);
    await resolveRequest(request, documentFixture());
    expect(documentRow().getByRole("button", { name: "Analisi..." })).toBeDisabled();
    await resolveRequest(reload, subjectFixture({ documents: [documentFixture({
      content_category_label: "Contratto rilevato", content_reason: "firma presente",
      content_excerpt: "testo acquisito", content_classification_error: "nota archivio",
    })] }));
    await screen.findByText(classificationSuccess);
    expect(documentRow().getByRole("button", { name: "Analizza contenuto" })).toBeEnabled();
    expect(documentRow().getByText("contenuto: Contratto rilevato")).toBeInTheDocument();
    expect(documentRow().getByText("Contenuto: firma presente")).toBeInTheDocument();
    expect(documentRow().getByText("Estratto: testo acquisito")).toBeInTheDocument();
    expect(documentRow().getByText("Nota: nota archivio")).toBeInTheDocument();
    expect(api.classifyUtenzeDocumentContent).toHaveBeenCalledExactlyOnceWith(token, "document-32");
    expect(api.classifyUtenzeDocumentContent.mock.invocationCallOrder[0]).toBeLessThan(api.getUtenzeSubject.mock.invocationCallOrder[beforeReload]);
  });
  test.each([
    ["api", new Error("classification denied"), "classification denied"],
    ["api", "offline", "Errore classificazione contenuto documento"],
    ["reload", new Error("classification reload denied"), "classification reload denied"],
    ["reload", undefined, "Errore classificazione contenuto documento"],
  ])("classification %s failure clears busy and permits genuine retry (%s)", async (phase, reason, message) => {
    await ready();
    if (phase === "api") api.classifyUtenzeDocumentContent.mockRejectedValueOnce(reason);
    else api.getUtenzeSubject.mockRejectedValueOnce(reason);
    classify(); await screen.findByText(message as string);
    expect(documentRow().getByRole("button", { name: "Analizza contenuto" })).toBeEnabled();
    expect(screen.queryByText(classificationSuccess)).not.toBeInTheDocument();
    classify(); await screen.findByText(classificationSuccess);
    expect(screen.queryByText(message as string)).not.toBeInTheDocument();
    expect(api.classifyUtenzeDocumentContent).toHaveBeenCalledTimes(2);
  });
  test("new classification clears earlier success while genuinely pending", async () => {
    await ready(); classify(); await screen.findByText(classificationSuccess);
    const request = deferred<AnagraficaDocument>();
    api.classifyUtenzeDocumentContent.mockReturnValueOnce(request.promise);
    classify();
    expect(screen.queryByText(classificationSuccess)).not.toBeInTheDocument();
    await resolveRequest(request, documentFixture());
    await screen.findByText(classificationSuccess);
  });
  test("distinct visible documents can overlap and the single busy id follows last start", async () => {
    const second = documentFixture({ id: "document-33", filename: "second.pdf", nas_path: "/archive/second.pdf" });
    const subject = subjectFixture({ documents: [documentFixture(), second] });
    await ready(subject);
    api.getUtenzeSubject.mockResolvedValue(subject);
    const firstRequest = deferred<AnagraficaDocument>();
    const secondRequest = deferred<AnagraficaDocument>();
    api.classifyUtenzeDocumentContent.mockReturnValueOnce(firstRequest.promise).mockReturnValueOnce(secondRequest.promise);
    classify(); classify("second.pdf");
    expect(documentRow().getByRole("button", { name: "Analizza contenuto" })).toBeEnabled();
    expect(documentRow("second.pdf").getByRole("button", { name: "Analisi..." })).toBeDisabled();
    await resolveRequest(firstRequest, documentFixture());
    expect(documentRow("second.pdf").getByRole("button", { name: "Analizza contenuto" })).toBeEnabled();
    await resolveRequest(secondRequest, second);
    expect(api.classifyUtenzeDocumentContent.mock.calls).toEqual([[token, "document-32"], [token, "document-33"]]);
    expect(screen.getByText(classificationSuccess)).toBeInTheDocument();
  });
});

describe("R32 original public password-confirmed deletion", () => {
  test("opening clears feedback and cancel resets password without API mutation", async () => {
    await ready(); classify(); await screen.findByText(classificationSuccess);
    openDelete();
    expect(screen.queryByText(classificationSuccess)).not.toBeInTheDocument();
    setPassword("first secret"); cancelDelete();
    expect(screen.queryByText("Cancellazione documento")).not.toBeInTheDocument();
    fireEvent.click(documentRow().getByRole("button", { name: "Rimuovi" }));
    expect(deletionPanel().getByLabelText("Password")).toHaveValue("");
    cancelDelete();
    expect(api.deleteUtenzeDocument).not.toHaveBeenCalled();
  });
  test.each(["", " \t\n "])("blank trimmed password %j does not enter busy or mutate", async (password) => {
    await ready(); openDelete(); setPassword(password); confirmDelete();
    expect(screen.getByText("Inserisci la password per cancellare il documento.")).toBeInTheDocument();
    expect(deletionPanel().queryByText("Inserisci la password per cancellare il documento.")).not.toBeInTheDocument();
    expect(deletionPanel().getByRole("button", { name: "Elimina" })).toBeEnabled();
    expect(deletionPanel().getByLabelText("Password")).toBeEnabled();
    expect(api.deleteUtenzeDocument).not.toHaveBeenCalled();
    cancelDelete();
  });
  test("delete trims password, orders delete/reload/NAS and locks only real modal controls", async () => {
    await ready(); openDelete(); setPassword("  genuine secret\t ");
    const request = deferred<void>();
    const reload = deferred<AnagraficaSubjectDetail>();
    api.deleteUtenzeDocument.mockReturnValueOnce(request.promise);
    api.getUtenzeSubject.mockReturnValueOnce(reload.promise);
    const beforeReload = api.getUtenzeSubject.mock.calls.length;
    const beforeNas = api.getUtenzeSubjectNasImportStatus.mock.calls.length;
    confirmDelete(); expectDeleteBusy();
    expect(api.deleteUtenzeDocument).toHaveBeenCalledExactlyOnceWith(token, "document-32", "genuine secret");
    expect(api.getUtenzeSubject).toHaveBeenCalledTimes(beforeReload);
    await resolveRequest(request, undefined); expectDeleteBusy();
    expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledTimes(beforeNas);
    await resolveRequest(reload, subjectFixture({ documents: [] }));
    await screen.findByText("Documento eliminato.");
    expect(screen.queryByText("Cancellazione documento")).not.toBeInTheDocument();
    expect(screen.getByText("Nessun documento associato.")).toBeInTheDocument();
    expect(api.getUtenzeSubject.mock.calls[beforeReload]).toEqual([token, "subject-1"]);
    expect(api.deleteUtenzeDocument.mock.invocationCallOrder[0]).toBeLessThan(api.getUtenzeSubject.mock.invocationCallOrder[beforeReload]);
    expect(api.getUtenzeSubject.mock.invocationCallOrder[beforeReload]).toBeLessThan(api.getUtenzeSubjectNasImportStatus.mock.invocationCallOrder[beforeNas]);
    expect(api.getUtenzeSubjectNasImportStatus.mock.calls.slice(beforeNas).every((args) => JSON.stringify(args) === JSON.stringify([token, "subject-1"]))).toBe(true);
    expect(screen.queryByText("Modalità modifica attiva")).not.toBeInTheDocument();
  });
  test.each([
    ["api", new Error("password rejected"), "password rejected"],
    ["api", "offline", "Errore eliminazione documento"],
    ["reload", new Error("delete reload denied"), "delete reload denied"],
    ["reload", null, "Errore eliminazione documento"],
  ])("delete %s failure preserves target/password and re-enables modal (%s)", async (phase, reason, message) => {
    await ready(); openDelete(); setPassword("retained password");
    const beforeReload = api.getUtenzeSubject.mock.calls.length;
    const beforeNas = api.getUtenzeSubjectNasImportStatus.mock.calls.length;
    if (phase === "api") api.deleteUtenzeDocument.mockRejectedValueOnce(reason);
    else api.getUtenzeSubject.mockRejectedValueOnce(reason);
    confirmDelete();
    await waitFor(() => expect(deletionPanel().getByRole("button", { name: "Elimina" })).toBeEnabled());
    expect(deletionPanel().getByLabelText("Password")).toHaveValue("retained password");
    expect(screen.getByText(message as string)).toBeInTheDocument();
    expect(deletionPanel().queryByText(message as string)).not.toBeInTheDocument();
    expect(api.getUtenzeSubject).toHaveBeenCalledTimes(beforeReload + (phase === "reload" ? 1 : 0));
    expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledTimes(beforeNas);
    cancelDelete();
    expect(screen.getByText("mutation.pdf")).toBeInTheDocument();
  });
  test.each([
    [new Error("NAS verification unavailable"), "NAS verification unavailable"],
    ["offline", "Verifica NAS non disponibile"],
  ])("NAS status failure is swallowed after successful delete (%s)", async (reason, message) => {
    await ready(); openDelete(); setPassword("secret");
    api.getUtenzeSubject.mockResolvedValueOnce(subjectFixture({ documents: [] }));
    api.getUtenzeSubjectNasImportStatus.mockRejectedValue(reason);
    confirmDelete();
    await screen.findByText("Documento eliminato.");
    await screen.findByText(message as string);
    expect(screen.queryByText("Cancellazione documento")).not.toBeInTheDocument();
    expect(screen.getByText("Nessun documento associato.")).toBeInTheDocument();
  });
});
