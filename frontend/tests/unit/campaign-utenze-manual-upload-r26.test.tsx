import { act, cleanup, createEvent, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import UtenzeSubjectDetailPage from "@/app/utenze/[id]/page";
import type { AnagraficaDocument, AnagraficaSubjectDetail, AnagraficaSubjectNasImportStatus, AnprSubjectStatus, CurrentUser } from "@/types/api";

const api = vi.hoisted(() => ({
  subjectId: "subject-1",
  router: { push: vi.fn(), replace: vi.fn() },
  getStoredAccessToken: vi.fn(), clearStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn(), getMyPermissions: vi.fn(), getUtenzeAnprStatus: vi.fn(),
  getUtenzeSubject: vi.fn(), getUtenzeSubjectPaymentNotices: vi.fn(),
  getUtenzeSubjectNasImportStatus: vi.fn(), uploadUtenzeSubjectDocument: vi.fn(),
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
  getUtenzeAnprStatus: api.getUtenzeAnprStatus, getUtenzeSubject: api.getUtenzeSubject,
  getUtenzeSubjectPaymentNotices: api.getUtenzeSubjectPaymentNotices,
  getUtenzeSubjectNasImportStatus: api.getUtenzeSubjectNasImportStatus,
  uploadUtenzeSubjectDocument: api.uploadUtenzeSubjectDocument,
}));

const token = "r26-upload-token";
const fallbackEntry = "Nessun dato rilevato nel NAS, importa manualmente";
const singularSuccess = "Documento caricato manualmente e associato al soggetto.";
const emptyError = "Seleziona almeno un file da caricare.";
const emptyList = "Nessun file selezionato. Puoi scegliere piu file e classificarli singolarmente prima del caricamento.";
const uploadFallback = "Errore caricamento manuale documento";

function userFixture(): CurrentUser {
  return {
    id: 26, username: "r26", email: "r26@example.invalid", role: "viewer", is_active: true,
    module_accessi: false, module_rete: false, module_inventario: false, module_catasto: false,
    module_utenze: true, module_operazioni: false, module_riordino: false,
    module_ruolo: false, module_presenze: false, enabled_modules: ["utenze"],
  };
}
function documentFixture(overrides: Partial<AnagraficaDocument> = {}): AnagraficaDocument {
  return {
    id: "document-26", filename: "existing.pdf", relative_path: "existing.pdf",
    nas_path: "/archive/existing.pdf", extension: ".pdf", is_pdf: true,
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
    id, subject_type: "company", status: "active", source_system: "campaign-r26",
    source_external_id: null, source_name_raw: `Azienda R26 ${id}`,
    nas_folder_path: null, nas_folder_letter: null, requires_review: false, imported_at: null,
    created_at: "2026-10-11T10:00:00Z", updated_at: "2026-10-11T10:00:00Z", person: null,
    company: {
      subject_id: id, ragione_sociale: `Azienda R26 ${id}`, partita_iva: "12345678901",
      codice_fiscale: null, forma_giuridica: null, sede_legale: null, comune_sede: null,
      cap: null, email_pec: null, telefono: null, note: null,
      created_at: "2026-10-11T10:00:00Z", updated_at: "2026-10-11T10:00:00Z",
    },
    documents: [], audit_log: [], catasto_documents: [], ...overrides,
  };
}
function personFixture(): AnagraficaSubjectDetail {
  return subjectFixture({
    subject_type: "person", source_name_raw: "Rossi Mario", company: null,
    person: {
      subject_id: "subject-1", cognome: "Rossi", nome: "Mario", codice_fiscale: "RSSMRA80A01H501U",
      anpr_id: null, stato_anpr: null, data_decesso: null, luogo_decesso_comune: null,
      last_anpr_check_at: null, last_c030_check_at: null, data_nascita: null,
      comune_nascita: null, indirizzo: null, comune_residenza: null, cap: null,
      email: null, telefono: null, note: null,
      created_at: "2026-10-11T10:00:00Z", updated_at: "2026-10-11T10:00:00Z",
    },
  });
}
function statusFixture(overrides: Partial<AnagraficaSubjectNasImportStatus> = {}): AnagraficaSubjectNasImportStatus {
  return {
    can_import_from_nas: false, missing_in_nas: true, matched_folder_path: null,
    matched_folder_name: null, total_files_in_nas: 0, pending_files_in_nas: 0,
    message: "R26 NAS ready", ...overrides,
  };
}
function fileFixture(name = "selected.pdf", bytes: BlobPart[] = ["bytes"]): File {
  return new File(bytes, name, { type: "application/octet-stream", lastModified: 123456 });
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
async function rejectRequest<Result>(request: ReturnType<typeof deferred<Result>>, reason: unknown) {
  await act(async () => { request.reject(reason); });
}
async function ready(subject = subjectFixture()) {
  api.getUtenzeSubject.mockResolvedValueOnce(subject);
  const view = render(<UtenzeSubjectDetailPage />);
  await screen.findByText("R26 NAS ready");
  await act(async () => {});
  return view;
}
function enableEditing() {
  fireEvent.click(screen.getByRole("button", { name: "Modifica" }));
  fireEvent.click(screen.getByRole("button", { name: "Abilita modifica" }));
  expect(screen.getByText("Modalità modifica attiva")).toBeInTheDocument();
}
function openManual(entry = "Inserisci file") {
  if (!screen.queryByText("Modalità modifica attiva")) enableEditing();
  fireEvent.click(screen.getByRole("button", { name: entry }));
  expect(screen.getByText("Import manuale documento")).toBeInTheDocument();
}
function panel(): HTMLElement {
  const element = screen.getByText("Import manuale documento").parentElement?.parentElement;
  if (!element) throw new Error("Missing public manual-upload panel");
  return element;
}
function input(): HTMLInputElement {
  const element = panel().querySelector<HTMLInputElement>('input[type="file"]');
  if (!element) throw new Error("Missing native file input");
  return element;
}
function dropTarget() {
  return within(panel()).getByRole("button", { name: "Trascina qui i file o clicca per selezionarli" });
}
function selectFiles(files: File[] | null) {
  fireEvent.change(input(), { target: { files } });
}
function rows(): HTMLElement[] {
  return within(panel()).queryAllByRole("button", { name: "Rimuovi" }).map((button) => {
    const element = button.parentElement?.parentElement;
    if (!element) throw new Error("Missing public upload item");
    return element;
  });
}
function category(index: number) { return within(rows()[index]).getByLabelText("Categoria documento"); }
function notes(index: number) { return within(rows()[index]).getByLabelText("Note"); }
function submit() {
  fireEvent.click(within(panel()).getByRole("button", { name: /^Carica(?: documento| \d+ documenti)$/ }));
}
function cancel() { fireEvent.click(within(panel()).getByRole("button", { name: "Annulla" })); }
function expectNoModal() { expect(screen.queryByText("Import manuale documento")).not.toBeInTheDocument(); }
function expectBusy() {
  expect(within(panel()).getByRole("button", { name: "Caricamento..." })).toBeDisabled();
  expect(within(panel()).getByRole("button", { name: "Annulla" })).toBeDisabled();
  for (const row of rows()) {
    expect(within(row).getByRole("button", { name: "Rimuovi" })).toBeDisabled();
    expect(within(row).getByLabelText("Categoria documento")).toBeDisabled();
    expect(within(row).getByLabelText("Note")).toBeDisabled();
  }
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
  api.uploadUtenzeSubjectDocument.mockResolvedValue(documentFixture());
  api.getUtenzeAnprStatus.mockImplementation(async (_token: string, id: string): Promise<AnprSubjectStatus> => ({
    subject_id: id, anpr_id: null, stato_anpr: "unknown", data_decesso: null,
    luogo_decesso_comune: null, last_anpr_check_at: null, last_c030_check_at: null,
  }));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("R26 public manual-upload access and modal", () => {
  test("read-only hides both entry points until real edit confirmation", async () => {
    await ready();
    expect(screen.queryByRole("button", { name: "Inserisci file" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: fallbackEntry })).not.toBeInTheDocument();
    enableEditing();
    expect(screen.getByRole("button", { name: "Inserisci file" })).toBeEnabled();
    expect(screen.getByRole("button", { name: fallbackEntry })).toBeEnabled();
    expect(api.uploadUtenzeSubjectDocument).not.toHaveBeenCalled();
  });
  test.each(["Inserisci file", fallbackEntry])("%s opens the same empty public modal", async (entry) => {
    await ready(); openManual(entry);
    expect(within(panel()).getByText(emptyList)).toBeInTheDocument();
    expect(input()).toHaveAttribute("multiple");
    expect(input()).not.toHaveAttribute("accept");
    expect(api.uploadUtenzeSubjectDocument).not.toHaveBeenCalled();
  });
  test("eligible NAS hides header fallback without suppressing Inserisci file", async () => {
    api.getUtenzeSubjectNasImportStatus.mockResolvedValue(statusFixture({ can_import_from_nas: true, missing_in_nas: false }));
    await ready(); enableEditing();
    expect(screen.queryByRole("button", { name: fallbackEntry })).not.toBeInTheDocument();
    openManual(); expect(within(panel()).getByText(emptyList)).toBeInTheDocument();
  });
  test.each([null, "/archive/linked"])("modal explanation follows actual subject NAS path %s", async (path) => {
    await ready(subjectFixture({ nas_folder_path: path })); openManual();
    expect(within(panel()).getByText(path
      ? /sincronizzati anche sul NAS nella cartella GAIA_UPLOADS/
      : /il soggetto non ha ancora una cartella NAS collegata/)).toBeInTheDocument();
  });
  test("existing associated documents remain distinct from new selection", async () => {
    await ready(subjectFixture({ documents: [documentFixture()] })); openManual();
    expect(within(panel()).getByText("existing.pdf")).toBeInTheDocument();
    expect(within(panel()).getByText("/archive/existing.pdf")).toBeInTheDocument();
    expect(rows()).toHaveLength(0);
    expect(within(panel()).getByText(emptyList)).toBeInTheDocument();
  });
  test("real person/ANPR child does not replace public manual file behavior", async () => {
    await ready(personFixture());
    await waitFor(() => expect(api.getUtenzeAnprStatus).toHaveBeenCalledWith(token, "subject-1"));
    expect(screen.getByText("Rossi Mario")).toBeInTheDocument();
    openManual(); const file = fileFixture(); selectFiles([file]); submit();
    await screen.findByText(singularSuccess);
    expect(api.uploadUtenzeSubjectDocument).toHaveBeenCalledWith(token, "subject-1", file, "altro", undefined);
  });
});

describe("R26 real selection, duplicates and item metadata", () => {
  test("empty upload validates without busy, upload, reload or NAS refresh", async () => {
    await ready(); openManual();
    const subjectCalls = api.getUtenzeSubject.mock.calls.length;
    const statusCalls = api.getUtenzeSubjectNasImportStatus.mock.calls.length;
    submit();
    expect(screen.getByText(emptyError)).toBeInTheDocument();
    expect(within(panel()).getByRole("button", { name: "Carica documento" })).toBeEnabled();
    expect(api.uploadUtenzeSubjectDocument).not.toHaveBeenCalled();
    expect(api.getUtenzeSubject).toHaveBeenCalledTimes(subjectCalls);
    expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledTimes(statusCalls);
  });
  test("native multiple input appends selection order with independent default metadata", async () => {
    await ready(); openManual();
    selectFiles([fileFixture("first.pdf"), fileFixture("second.pdf")]);
    selectFiles([fileFixture("third.pdf")]);
    expect(rows()).toHaveLength(3);
    for (const [index, name] of ["first.pdf", "second.pdf", "third.pdf"].entries()) {
      expect(within(rows()[index]).getByText(name)).toBeInTheDocument();
      expect(category(index)).toHaveValue("altro"); expect(notes(index)).toHaveValue("");
      expect(within(rows()[index]).getByText(new RegExp(`File ${index + 1} ·`))).toBeInTheDocument();
    }
    expect(within(panel()).getByRole("button", { name: "Carica 3 documenti" })).toBeEnabled();
  });
  test("reset input permits reselecting identical File without deduplication", async () => {
    await ready(); openManual(); const file = fileFixture("repeat.pdf");
    selectFiles([file]); expect(input()).toHaveValue("");
    selectFiles([file]); expect(rows()).toHaveLength(2);
    fireEvent.change(notes(0), { target: { value: "first occurrence" } });
    expect(notes(1)).toHaveValue("");
    submit(); await screen.findByText("2 documenti caricati manualmente e associati al soggetto.");
    expect(api.uploadUtenzeSubjectDocument.mock.calls).toEqual([
      [token, "subject-1", file, "altro", "first occurrence"],
      [token, "subject-1", file, "altro", undefined],
    ]);
    expect(api.uploadUtenzeSubjectDocument.mock.calls[0][2]).toBe(file);
    expect(api.uploadUtenzeSubjectDocument.mock.calls[1][2]).toBe(file);
  });
  test("same filename/lastModified from selection and drop retain separate editable occurrences", async () => {
    await ready(); openManual(); const first = fileFixture("same.pdf"); const second = fileFixture("same.pdf", ["different bytes"]);
    selectFiles([first]); fireEvent.drop(dropTarget(), { dataTransfer: { files: [second] } });
    expect(rows()).toHaveLength(2);
    fireEvent.change(category(1), { target: { value: "contratto" } });
    fireEvent.click(within(rows()[0]).getByRole("button", { name: "Rimuovi" }));
    expect(rows()).toHaveLength(1); expect(category(0)).toHaveValue("contratto");
    submit(); await screen.findByText(singularSuccess);
    expect(api.uploadUtenzeSubjectDocument).toHaveBeenCalledWith(token, "subject-1", second, "contratto", undefined);
    expect(api.uploadUtenzeSubjectDocument.mock.calls[0][2]).toBe(second);
  });
  test.each([{ files: null }, { files: [] }])("native canceled/empty selection $files leaves current list intact", async ({ files }) => {
    await ready(); openManual(); selectFiles([fileFixture()]);
    fireEvent.change(notes(0), { target: { value: "retained" } });
    selectFiles(files); expect(rows()).toHaveLength(1); expect(notes(0)).toHaveValue("retained");
    expect(input()).toHaveValue("");
  });
  test.each(["click", "Enter", " "])("%s activates real native chooser input", async (action) => {
    await ready(); openManual(); const chosen = vi.fn(); input().addEventListener("click", chosen);
    if (action === "click") fireEvent.click(dropTarget());
    else { dropTarget().focus(); fireEvent.keyDown(dropTarget(), { key: action }); }
    expect(chosen).toHaveBeenCalledTimes(1); expect(rows()).toHaveLength(0);
  });
  test("nonactivation key leaves chooser and list unchanged", async () => {
    await ready(); openManual(); const chosen = vi.fn(); input().addEventListener("click", chosen);
    dropTarget().focus(); fireEvent.keyDown(dropTarget(), { key: "ArrowDown" });
    expect(chosen).not.toHaveBeenCalled(); expect(rows()).toHaveLength(0);
  });
  test("drag lifecycle prevents propagation and drop appends in transfer order", async () => {
    await ready(); openManual(); selectFiles([fileFixture("before.pdf")]);
    const outer = vi.fn(); window.addEventListener("dragenter", outer); window.addEventListener("drop", outer);
    const enter = createEvent.dragEnter(dropTarget(), { bubbles: true, cancelable: true });
    fireEvent(dropTarget(), enter); expect(enter.defaultPrevented).toBe(true);
    expect(dropTarget()).toHaveClass("border-[#1D4E35]");
    fireEvent.dragLeave(dropTarget()); expect(dropTarget()).toHaveClass("border-gray-200");
    fireEvent.dragOver(dropTarget()); expect(dropTarget()).toHaveClass("border-[#1D4E35]");
    const drop = createEvent.drop(dropTarget(), { bubbles: true, cancelable: true, dataTransfer: { files: [fileFixture("drop-a.pdf"), fileFixture("drop-b.pdf")] } });
    fireEvent(dropTarget(), drop); expect(drop.defaultPrevented).toBe(true); expect(outer).not.toHaveBeenCalled();
    expect(dropTarget()).toHaveClass("border-gray-200"); expect(rows()).toHaveLength(3);
    for (const [index, name] of ["before.pdf", "drop-a.pdf", "drop-b.pdf"].entries()) expect(within(rows()[index]).getByText(name)).toBeInTheDocument();
    window.removeEventListener("dragenter", outer); window.removeEventListener("drop", outer);
  });
  test("drop with no transfer files preserves selection and clears highlight", async () => {
    await ready(); openManual(); selectFiles([fileFixture()]);
    fireEvent.dragEnter(dropTarget()); fireEvent.drop(dropTarget());
    expect(rows()).toHaveLength(1); expect(dropTarget()).toHaveClass("border-gray-200");
  });
  test("category and notes update only chosen row and expose all real category options", async () => {
    await ready(); openManual(); selectFiles([fileFixture("a.pdf"), fileFixture("b.pdf")]);
    expect(within(rows()[0]).getAllByRole("option").map((option) => option.getAttribute("value"))).toEqual([
      "ingiunzione", "notifica", "estratto_debito", "pratica_interna", "visura", "corrispondenza", "contratto", "altro",
    ]);
    fireEvent.change(category(0), { target: { value: "ingiunzione" } });
    fireEvent.change(notes(0), { target: { value: "  note verbatim  " } });
    expect(category(0)).toHaveValue("ingiunzione"); expect(notes(0)).toHaveValue("  note verbatim  ");
    expect(category(1)).toHaveValue("altro"); expect(notes(1)).toHaveValue("");
  });
  test("removing middle and last item renumbers surviving list without upload", async () => {
    await ready(); openManual(); selectFiles([fileFixture("a.pdf"), fileFixture("b.pdf"), fileFixture("c.pdf")]);
    fireEvent.click(within(rows()[1]).getByRole("button", { name: "Rimuovi" }));
    expect(rows()).toHaveLength(2); expect(within(rows()[1]).getByText("c.pdf")).toBeInTheDocument();
    expect(within(rows()[1]).getByText(/File 2 ·/)).toBeInTheDocument();
    fireEvent.click(within(rows()[1]).getByRole("button", { name: "Rimuovi" }));
    fireEvent.click(within(rows()[0]).getByRole("button", { name: "Rimuovi" }));
    expect(within(panel()).getByText(emptyList)).toBeInTheDocument();
    expect(api.uploadUtenzeSubjectDocument).not.toHaveBeenCalled();
  });
  test("empty and binary arbitrary-extension files are accepted with real byte-size display", async () => {
    await ready(); openManual();
    const empty = fileFixture("empty.unlisted", []); const binary = fileFixture("binary.xyz", [new Uint8Array(1024 * 1024)]);
    selectFiles([empty, binary]);
    expect(within(rows()[0]).getByText("File 1 · 0.00 MB")).toBeInTheDocument();
    expect(within(rows()[1]).getByText("File 2 · 1.00 MB")).toBeInTheDocument();
    submit(); await screen.findByText("2 documenti caricati manualmente e associati al soggetto.");
    expect(api.uploadUtenzeSubjectDocument.mock.calls.map((call) => call[2])).toEqual([empty, binary]);
  });
});

describe("R26 sequential uploads and actual async boundaries", () => {
  test("single upload sends exact captured boundary arguments and ignores returned document metadata", async () => {
    await ready(); openManual(); const file = fileFixture(); selectFiles([file]);
    fireEvent.change(category(0), { target: { value: "visura" } });
    api.uploadUtenzeSubjectDocument.mockResolvedValueOnce(documentFixture({ filename: "server-name.pdf", doc_type: "contratto" }));
    submit(); await screen.findByText(singularSuccess); expectNoModal();
    expect(api.uploadUtenzeSubjectDocument.mock.calls).toEqual([[token, "subject-1", file, "visura", undefined]]);
    expect(api.uploadUtenzeSubjectDocument.mock.calls[0][2]).toBe(file);
    expect(screen.queryByText("server-name.pdf")).not.toBeInTheDocument();
  });
  test.each(["kept note", "   "])("nonempty notes %s are passed verbatim, not trimmed", async (value) => {
    await ready(); openManual(); const file = fileFixture(); selectFiles([file]);
    fireEvent.change(notes(0), { target: { value } }); submit(); await screen.findByText(singularSuccess);
    expect(api.uploadUtenzeSubjectDocument).toHaveBeenCalledWith(token, "subject-1", file, "altro", value);
  });
  test("deferred uploads are strictly sequential and reload begins only after last completion", async () => {
    await ready(); openManual(); const first = fileFixture("first.pdf"); const second = fileFixture("second.pdf");
    selectFiles([first, second]); const requests = [deferred<AnagraficaDocument>(), deferred<AnagraficaDocument>()];
    const reloading = deferred<AnagraficaSubjectDetail>(); const trace: string[] = [];
    api.uploadUtenzeSubjectDocument
      .mockImplementationOnce(() => { trace.push("upload:first"); return requests[0].promise; })
      .mockImplementationOnce(() => { trace.push("upload:second"); return requests[1].promise; });
    api.getUtenzeSubject.mockImplementationOnce(() => { trace.push("reload"); return reloading.promise; });
    submit(); expect(trace).toEqual(["upload:first"]); expectBusy();
    await resolveRequest(requests[0], documentFixture()); expect(trace).toEqual(["upload:first", "upload:second"]);
    expect(api.uploadUtenzeSubjectDocument.mock.calls.map((call) => call[2])).toEqual([first, second]);
    expect(api.uploadUtenzeSubjectDocument.mock.calls[0][2]).toBe(first);
    expect(api.uploadUtenzeSubjectDocument.mock.calls[1][2]).toBe(second);
    await resolveRequest(requests[1], documentFixture()); expect(trace).toEqual(["upload:first", "upload:second", "reload"]); expectBusy();
    await resolveRequest(reloading, subjectFixture());
    await screen.findByText("2 documenti caricati manualmente e associati al soggetto.");
    console.info("R26_UPLOAD_TRACE", JSON.stringify({ scenario: "sequential", events: trace }));
  });
  test("busy native controls reject duplicate submit, cancel and remove", async () => {
    await ready(); openManual(); const file = fileFixture(); selectFiles([file]);
    const uploading = deferred<AnagraficaDocument>(); api.uploadUtenzeSubjectDocument.mockReturnValueOnce(uploading.promise);
    submit(); expectBusy();
    fireEvent.click(within(panel()).getByRole("button", { name: "Caricamento..." })); cancel();
    fireEvent.click(within(rows()[0]).getByRole("button", { name: "Rimuovi" }));
    expect(rows()).toHaveLength(1); expect(api.uploadUtenzeSubjectDocument).toHaveBeenCalledTimes(1);
    await resolveRequest(uploading, documentFixture()); await screen.findByText(singularSuccess);
  });
  test("focused chooser keyboard stays reachable while busy but captured upload excludes later selection", async () => {
    await ready(); openManual(); const first = fileFixture("captured.pdf"); const later = fileFixture("later.pdf"); selectFiles([first]);
    const uploading = deferred<AnagraficaDocument>(); api.uploadUtenzeSubjectDocument.mockReturnValueOnce(uploading.promise);
    const target = dropTarget(); target.focus(); submit(); expectBusy();
    const chosen = vi.fn(); input().addEventListener("click", chosen);
    target.focus(); fireEvent.keyDown(target, { key: "Enter" });
    expect(chosen).toHaveBeenCalledTimes(1); expect(input()).not.toBeDisabled(); expect(target).toHaveClass("pointer-events-none");
    selectFiles([later]); expect(rows()).toHaveLength(2);
    await resolveRequest(uploading, documentFixture()); await screen.findByText(singularSuccess);
    expect(api.uploadUtenzeSubjectDocument.mock.calls).toEqual([[token, "subject-1", first, "altro", undefined]]);
    expectNoModal(); openManual(); expect(rows()).toHaveLength(0);
  });
  test("upload→reload→explicit/effect statuses preserve actual ordering and late status overwrite", async () => {
    await ready(); openManual(); selectFiles([fileFixture()]); const trace: string[] = [];
    const uploading = deferred<AnagraficaDocument>(); const reloading = deferred<AnagraficaSubjectDetail>();
    const explicit = deferred<AnagraficaSubjectNasImportStatus>(); const effect = deferred<AnagraficaSubjectNasImportStatus>();
    api.uploadUtenzeSubjectDocument.mockImplementationOnce(() => { trace.push("upload"); return uploading.promise; });
    api.getUtenzeSubject.mockImplementationOnce(() => { trace.push("reload"); return reloading.promise; });
    api.getUtenzeSubjectNasImportStatus
      .mockImplementationOnce(() => { trace.push("explicit"); return explicit.promise; })
      .mockImplementationOnce(() => { trace.push("effect"); return effect.promise; });
    submit(); expect(trace).toEqual(["upload"]);
    await resolveRequest(uploading, documentFixture()); expect(trace).toEqual(["upload", "reload"]);
    await resolveRequest(reloading, subjectFixture({ nas_folder_path: "/refreshed/path" }));
    expect(trace).toEqual(["upload", "reload", "explicit", "effect"]); expectBusy();
    await resolveRequest(explicit, statusFixture({ message: "Explicit status finished" }));
    await screen.findByText(singularSuccess); expectNoModal(); expect(screen.getByText("Explicit status finished")).toBeInTheDocument();
    await resolveRequest(effect, statusFixture({ message: "Late effect status overwrites" }));
    expect(screen.getByText("Late effect status overwrites")).toBeInTheDocument();
    expect(screen.queryByText("Explicit status finished")).not.toBeInTheDocument();
    console.info("R26_UPLOAD_TRACE", JSON.stringify({ scenario: "dual-status", events: trace }));
  });
  test("same-object reload runs only explicitly awaited status", async () => {
    const original = subjectFixture(); await ready(original); openManual(); selectFiles([fileFixture()]);
    const initialCount = api.getUtenzeSubjectNasImportStatus.mock.calls.length;
    api.getUtenzeSubject.mockResolvedValueOnce(original); submit(); await screen.findByText(singularSuccess);
    expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledTimes(initialCount + 1);
  });
  test("plural success closes and reopens with a clean list and exact captured count", async () => {
    await ready(); openManual(); selectFiles([fileFixture("a.pdf"), fileFixture("b.pdf"), fileFixture("c.pdf")]);
    submit(); await screen.findByText("3 documenti caricati manualmente e associati al soggetto."); expectNoModal();
    openManual(); expect(within(panel()).getByText(emptyList)).toBeInTheDocument();
    expect(within(panel()).getByRole("button", { name: "Carica documento" })).toBeEnabled();
  });
});

describe("R26 error boundaries and retained partial work", () => {
  test.each([{ error: new Error("Upload rejected"), message: "Upload rejected" }, { error: "opaque upload rejection", message: uploadFallback }])(
    "first upload rejection $message retains modal/list and prevents reload/status", async ({ error, message }) => {
      await ready(); openManual(); const first = fileFixture("first.pdf"); selectFiles([first, fileFixture("second.pdf")]);
      const subjectCount = api.getUtenzeSubject.mock.calls.length; const statusCount = api.getUtenzeSubjectNasImportStatus.mock.calls.length;
      api.uploadUtenzeSubjectDocument.mockRejectedValueOnce(error); submit(); await screen.findByText(message);
      expect(rows()).toHaveLength(2); expect(api.uploadUtenzeSubjectDocument).toHaveBeenCalledTimes(1);
      expect(api.getUtenzeSubject).toHaveBeenCalledTimes(subjectCount); expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledTimes(statusCount);
      expect(within(panel()).getByRole("button", { name: "Carica 2 documenti" })).toBeEnabled();
    },
  );
  test.each([{ error: new Error("Second rejected"), message: "Second rejected" }, { error: "opaque second rejection", message: uploadFallback }])(
    "second rejection $message stops third and retry repeats earlier successful file", async ({ error, message }) => {
      await ready(); openManual(); const files = [fileFixture("a.pdf"), fileFixture("b.pdf"), fileFixture("c.pdf")]; selectFiles(files);
      const subjectCount = api.getUtenzeSubject.mock.calls.length; const statusCount = api.getUtenzeSubjectNasImportStatus.mock.calls.length;
      api.uploadUtenzeSubjectDocument.mockResolvedValueOnce(documentFixture()).mockRejectedValueOnce(error);
      submit(); await screen.findByText(message); expect(rows()).toHaveLength(3);
      expect(api.uploadUtenzeSubjectDocument.mock.calls.map((call) => call[2])).toEqual(files.slice(0, 2));
      expect(api.getUtenzeSubject).toHaveBeenCalledTimes(subjectCount); expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledTimes(statusCount);
      submit(); await screen.findByText("3 documenti caricati manualmente e associati al soggetto.");
      expect(api.uploadUtenzeSubjectDocument.mock.calls.map((call) => call[2])).toEqual([files[0], files[1], ...files]);
      console.info("R26_UPLOAD_TRACE", JSON.stringify({ scenario: "partial-retry", names: api.uploadUtenzeSubjectDocument.mock.calls.map((call) => call[2].name) }));
    },
  );
  test.each([{ error: new Error("Reload rejected"), message: "Reload rejected" }, { error: "opaque reload rejection", message: uploadFallback }])(
    "reload rejection $message retains list after uploads and prevents explicit status", async ({ error, message }) => {
      await ready(); openManual(); const file = fileFixture(); selectFiles([file]);
      const statusCount = api.getUtenzeSubjectNasImportStatus.mock.calls.length;
      api.getUtenzeSubject.mockRejectedValueOnce(error); submit(); await screen.findByText(message);
      expect(api.uploadUtenzeSubjectDocument).toHaveBeenCalledWith(token, "subject-1", file, "altro", undefined);
      expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledTimes(statusCount); expect(rows()).toHaveLength(1);
      expect(within(panel()).getByRole("button", { name: "Carica documento" })).toBeEnabled();
    },
  );
  test.each([{ error: new Error("NAS rejected"), message: "NAS rejected" }, { error: "opaque NAS rejection", message: "Verifica NAS non disponibile" }])(
    "both status failures $message are absorbed without rejecting successful manual upload", async ({ error, message }) => {
      await ready(); openManual(); selectFiles([fileFixture()]);
      const statusCount = api.getUtenzeSubjectNasImportStatus.mock.calls.length;
      api.getUtenzeSubjectNasImportStatus.mockRejectedValueOnce(error).mockRejectedValueOnce(error);
      submit(); await screen.findByText(singularSuccess); expectNoModal();
      expect(screen.getByText(message)).toBeInTheDocument();
      expect(api.getUtenzeSubjectNasImportStatus).toHaveBeenCalledTimes(statusCount + 2);
      expect(screen.queryByText(uploadFallback)).not.toBeInTheDocument();
    },
  );
  test("nonempty retry clears prior error immediately and releases busy after success", async () => {
    await ready(); openManual(); selectFiles([fileFixture()]);
    api.uploadUtenzeSubjectDocument.mockRejectedValueOnce(new Error("Previous error")); submit(); await screen.findByText("Previous error");
    const retry = deferred<AnagraficaDocument>(); api.uploadUtenzeSubjectDocument.mockReturnValueOnce(retry.promise);
    submit(); expect(screen.queryByText("Previous error")).not.toBeInTheDocument(); expectBusy();
    await resolveRequest(retry, documentFixture()); await screen.findByText(singularSuccess);
  });
  test("empty validation preserves prior success but next nonempty command clears both messages", async () => {
    await ready(); openManual(); selectFiles([fileFixture()]); submit(); await screen.findByText(singularSuccess);
    openManual(); submit(); expect(screen.getByText(emptyError)).toBeInTheDocument(); expect(screen.getByText(singularSuccess)).toBeInTheDocument();
    selectFiles([fileFixture("next.pdf")]); const uploading = deferred<AnagraficaDocument>(); api.uploadUtenzeSubjectDocument.mockReturnValueOnce(uploading.promise);
    submit(); expect(screen.queryByText(emptyError)).not.toBeInTheDocument(); expect(screen.queryByText(singularSuccess)).not.toBeInTheDocument(); expectBusy();
    await resolveRequest(uploading, documentFixture()); await screen.findByText(singularSuccess);
  });
});

describe("R26 manual-modal cleanup and captured closures", () => {
  test.each(["Annulla", "Escape"])("%s closes/reset and reopening starts empty", async (action) => {
    await ready(); openManual(); selectFiles([fileFixture()]); fireEvent.change(notes(0), { target: { value: "discarded" } });
    if (action === "Annulla") cancel(); else fireEvent.keyDown(window, { key: "Escape" });
    expectNoModal(); openManual(); expect(rows()).toHaveLength(0); expect(api.uploadUtenzeSubjectDocument).not.toHaveBeenCalled();
  });
  test("backdrop and unrelated key keep manual modal and selected files", async () => {
    await ready(); openManual(); selectFiles([fileFixture()]); const backdrop = panel().parentElement;
    if (!backdrop) throw new Error("Missing manual backdrop");
    fireEvent.click(backdrop); fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(rows()).toHaveLength(1); expect(api.uploadUtenzeSubjectDocument).not.toHaveBeenCalled();
  });
  test("Escape during upload does not cancel and late success clears reopened selection", async () => {
    await ready(); openManual(); const files = [fileFixture("captured-a.pdf"), fileFixture("captured-b.pdf")]; selectFiles(files);
    const first = deferred<AnagraficaDocument>(); const second = deferred<AnagraficaDocument>();
    api.uploadUtenzeSubjectDocument.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    submit(); expectBusy(); fireEvent.keyDown(window, { key: "Escape" }); expectNoModal();
    openManual(); expect(rows()).toHaveLength(0); expectBusy();
    dropTarget().focus(); fireEvent.keyDown(dropTarget(), { key: "Enter" }); selectFiles([fileFixture("reopened.pdf")]); expect(rows()).toHaveLength(1);
    await resolveRequest(first, documentFixture());
    expect(api.uploadUtenzeSubjectDocument.mock.calls.map((call) => call[2])).toEqual(files);
    await resolveRequest(second, documentFixture()); await screen.findByText("2 documenti caricati manualmente e associati al soggetto.");
    expectNoModal(); openManual(); expect(rows()).toHaveLength(0);
  });
  test("Escape during pending upload followed by late failure never reopens modal", async () => {
    await ready(); openManual(); selectFiles([fileFixture()]);
    const uploading = deferred<AnagraficaDocument>(); api.uploadUtenzeSubjectDocument.mockReturnValueOnce(uploading.promise);
    submit(); fireEvent.keyDown(window, { key: "Escape" }); expectNoModal();
    await rejectRequest(uploading, new Error("Late rejection")); await screen.findByText("Late rejection"); expectNoModal();
    openManual(); expect(rows()).toHaveLength(0); expect(within(panel()).getByRole("button", { name: "Carica documento" })).toBeEnabled();
  });
  test("same mounted route change retains original upload token/id/list and old reload closure", async () => {
    const view = await ready(); openManual(); const first = fileFixture("old-a.pdf"); const second = fileFixture("old-b.pdf"); selectFiles([first, second]);
    const uploading = deferred<AnagraficaDocument>(); api.uploadUtenzeSubjectDocument.mockReturnValueOnce(uploading.promise);
    submit(); api.subjectId = "subject-2"; api.getStoredAccessToken.mockReturnValue("changed-storage-token");
    window.history.replaceState(null, "", "/utenze/subject-2?embedded=1"); view.rerender(<UtenzeSubjectDetailPage />);
    await screen.findByText("Azienda R26 subject-2");
    expect(api.getUtenzeSubject).toHaveBeenLastCalledWith(token, "subject-2");
    await resolveRequest(uploading, documentFixture()); await screen.findByText("2 documenti caricati manualmente e associati al soggetto.");
    expect(api.uploadUtenzeSubjectDocument.mock.calls).toEqual([
      [token, "subject-1", first, "altro", undefined], [token, "subject-1", second, "altro", undefined],
    ]);
    expect(api.getUtenzeSubject).toHaveBeenLastCalledWith(token, "subject-1");
    expect(screen.getByText("Azienda R26 subject-1")).toBeInTheDocument();
    expect(api.getUtenzeSubjectNasImportStatus.mock.calls.some((call) => call[0] === token && call[1] === "subject-1")).toBe(true);
    console.info("R26_UPLOAD_TRACE", JSON.stringify({ scenario: "captured-route", uploadIds: api.uploadUtenzeSubjectDocument.mock.calls.map((call) => call[1]), reloadIds: api.getUtenzeSubject.mock.calls.map((call) => call[1]) }));
  });
  test("manual key listener is removed by same callback identity on close and unmount", async () => {
    const view = await ready(); const added = vi.spyOn(window, "addEventListener"); const removed = vi.spyOn(window, "removeEventListener");
    openManual();
    const first = added.mock.calls.filter((call) => call[0] === "keydown").at(-1)?.[1]; expect(first).toBeDefined();
    fireEvent.keyDown(window, { key: "Escape" }); expectNoModal();
    expect(removed.mock.calls.some((call) => call[0] === "keydown" && call[1] === first)).toBe(true);
    openManual(); const second = added.mock.calls.filter((call) => call[0] === "keydown").at(-1)?.[1]; expect(second).toBeDefined(); expect(second).not.toBe(first);
    view.unmount(); expect(removed.mock.calls.some((call) => call[0] === "keydown" && call[1] === second)).toBe(true);
  });
});
