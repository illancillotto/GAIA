import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import UtenzeSubjectDetailPage from "@/app/utenze/[id]/page";
import type { AnagraficaCatastoDocument, AnagraficaDocument, AnagraficaSubjectDetail } from "@/types/api";

const api = vi.hoisted(() => ({
  router: { push: vi.fn(), replace: vi.fn() },
  getStoredAccessToken: vi.fn(), getCurrentUser: vi.fn(), getMyPermissions: vi.fn(),
  getUtenzeSubject: vi.fn(), getUtenzeSubjectPaymentNotices: vi.fn(),
  getUtenzeSubjectNasImportStatus: vi.fn(), downloadUtenzeDocumentBlob: vi.fn(),
  downloadCatastoDocumentBlob: vi.fn(), createElaborazioneRichiesta: vi.fn(),
  convertToHtml: vi.fn(), read: vi.fn(), sheetToJson: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "subject-1" }), useRouter: () => api.router,
  useSearchParams: () => new URLSearchParams(window.location.search),
}));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: api.getStoredAccessToken, clearStoredAccessToken: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getCurrentUser: api.getCurrentUser, getMyPermissions: api.getMyPermissions,
  getUtenzeSubject: api.getUtenzeSubject, getUtenzeSubjectPaymentNotices: api.getUtenzeSubjectPaymentNotices,
  getUtenzeSubjectNasImportStatus: api.getUtenzeSubjectNasImportStatus,
  downloadUtenzeDocumentBlob: api.downloadUtenzeDocumentBlob,
  downloadCatastoDocumentBlob: api.downloadCatastoDocumentBlob,
  createElaborazioneRichiesta: api.createElaborazioneRichiesta,
}));
vi.mock("mammoth", () => ({ convertToHtml: api.convertToHtml }));
vi.mock("xlsx", () => ({ read: api.read, utils: { sheet_to_json: api.sheetToJson } }));
vi.mock("@/components/layout/app-shell", () => ({ AppShell: ({ children }: { children: ReactNode }) => <main>{children}</main> }));
vi.mock("@/components/layout/topbar", () => ({ Topbar: () => <header /> }));
vi.mock("@/components/anagrafica/AnprStatusCard", () => ({ AnprStatusCard: () => null }));
vi.mock("@/components/utenze/utenze-meter-readings-section", () => ({ UtenzeMeterReadingsSection: () => null }));
vi.mock("@/components/utenze/utenze-payment-notices-section", () => ({ UtenzePaymentNoticesSection: () => null }));
vi.mock("@/components/utenze/utenze-terreni-colture-section", () => ({ UtenzeTerreniColtureSection: () => null }));
vi.mock("@/components/utenze/utenze-domande-irrigue-section", () => ({ UtenzeDomandeIrrigueSection: () => null }));

function documentFixture(overrides: Partial<AnagraficaDocument> = {}): AnagraficaDocument {
  return {
    id: "doc-A", filename: "report.PDF", relative_path: "report.PDF", nas_path: "/archive/report.PDF",
    extension: ".PDF", is_pdf: true, doc_type: "visura", classification_source: "archive",
    smart_category: "cadastral", smart_category_label: "Visure e catasto", smart_priority: 60,
    smart_confidence: 0.85, smart_reason: null, content_classification_status: "not_started",
    content_category: null, content_category_label: null, content_confidence: null, content_reason: null,
    content_excerpt: null, content_classification_source: null, content_classified_at: null,
    content_classification_error: null, warnings: [], ...overrides,
  };
}
function catastoFixture(): AnagraficaCatastoDocument {
  return {
    id: "cat-A", request_id: null, comune: "ORISTANO", foglio: "1", particella: "2",
    subalterno: null, catasto: "Terreni", tipo_visura: "Sintetica", filename: "catasto.PDF",
    codice_fiscale: "RSSMRA80A01H501U", created_at: "2026-10-01T00:00:00Z",
  };
}
function subjectFixture(documents: AnagraficaDocument[], catasto: AnagraficaCatastoDocument[] = []): AnagraficaSubjectDetail {
  return {
    id: "subject-1", subject_type: "person", status: "active", source_system: "campaign-r23",
    source_external_id: null, source_name_raw: "Rossi Mario", nas_folder_path: null, nas_folder_letter: null,
    requires_review: false, imported_at: null, created_at: "2026-10-11T00:00:00Z", updated_at: "2026-10-11T00:00:00Z",
    person: {
      subject_id: "subject-1", cognome: "Rossi", nome: "Mario", codice_fiscale: "RSSMRA80A01H501U",
      anpr_id: null, stato_anpr: null, data_decesso: null, luogo_decesso_comune: null,
      last_anpr_check_at: null, last_c030_check_at: null, data_nascita: null, comune_nascita: null,
      indirizzo: null, comune_residenza: null, cap: null, email: null, telefono: null, note: null,
      created_at: "2026-10-11T00:00:00Z", updated_at: "2026-10-11T00:00:00Z",
    },
    company: null, documents, audit_log: [], catasto_documents: catasto,
  };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
async function resolveRequest<T>(request: ReturnType<typeof deferred<T>>, value: T) {
  await act(async () => { request.resolve(value); });
}
async function rejectRequest<T>(request: ReturnType<typeof deferred<T>>, error: unknown) {
  await act(async () => { request.reject(error); });
}

const originalCreate = Object.getOwnPropertyDescriptor(URL, "createObjectURL");
const originalRevoke = Object.getOwnPropertyDescriptor(URL, "revokeObjectURL");
const url = { create: vi.fn<(blob: Blob) => string>(), revoke: vi.fn<(value: string) => void>() };
let trace: string[] = [];
let urlSequence = 0;

async function ready(documents = [documentFixture()], catasto: AnagraficaCatastoDocument[] = []) {
  api.getUtenzeSubject.mockResolvedValue(subjectFixture(documents, catasto));
  const view = render(<UtenzeSubjectDetailPage />);
  await screen.findByText("Preview NAS ready");
  await act(async () => {});
  return view;
}
function row(filename: string, section = "Documenti associati") {
  const article = screen.getByText(section).closest("article");
  if (!article) throw new Error("Missing document article");
  const control = within(article).getByText(filename).closest<HTMLElement>('[role="button"]');
  if (!control) throw new Error("Missing public document row");
  return control;
}
function openDocument(filename = "report.PDF") { fireEvent.click(within(row(filename)).getByRole("button", { name: "Preview" })); }
function modal() {
  const panel = screen.getByText("Anteprima documento").parentElement?.parentElement?.parentElement;
  if (!panel) throw new Error("Missing preview panel");
  return panel;
}
function close() { fireEvent.click(within(modal()).getByRole("button", { name: "Chiudi" })); }
function downloadLink() { return within(modal()).getByRole("link", { name: "Scarica" }); }
async function pdf(filename = "report.PDF") {
  const frame = await screen.findByTitle(filename);
  expect(frame.tagName).toBe("IFRAME");
  await waitFor(() => expect(screen.queryByText("Caricamento anteprima...")).not.toBeInTheDocument());
  return frame;
}
function freezeTrace(scenario: string, extra: object = {}) {
  const boundaries = [
    ["download", api.downloadUtenzeDocumentBlob], ["catasto", api.downloadCatastoDocumentBlob],
    ["create", url.create], ["revoke", url.revoke], ["mammoth", api.convertToHtml], ["xlsx", api.read],
  ] as const;
  const boundaryOrder = boundaries.flatMap(([kind, mock]) => mock.mock.invocationCallOrder.map((order, index) => ({ kind, order, call: index + 1 })))
    .sort((a, b) => a.order - b.order);
  console.info("R23_PREVIEW_TRACE", JSON.stringify({ scenario, events: trace, boundaryOrder, ...extra }));
}

beforeEach(() => {
  vi.resetAllMocks(); trace = []; urlSequence = 0;
  window.history.replaceState(null, "", "/utenze/subject-1");
  Object.defineProperty(URL, "createObjectURL", { configurable: true, writable: true, value: url.create });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, writable: true, value: url.revoke });
  url.create.mockImplementation(() => { const value = `blob:r23-${++urlSequence}`; trace.push(`create:${value}`); return value; });
  url.revoke.mockImplementation((value) => { trace.push(`revoke:${value}`); });
  api.getStoredAccessToken.mockReturnValue("campaign-token");
  api.getCurrentUser.mockResolvedValue({ enabled_modules: ["utenze"], role: "viewer" });
  api.getMyPermissions.mockResolvedValue({ granted_keys: [] });
  api.getUtenzeSubjectPaymentNotices.mockResolvedValue([]);
  api.getUtenzeSubjectNasImportStatus.mockResolvedValue({
    can_import_from_nas: false, missing_in_nas: true, matched_folder_path: null,
    matched_folder_name: null, total_files_in_nas: 0, pending_files_in_nas: 0, message: "Preview NAS ready",
  });
  api.downloadUtenzeDocumentBlob.mockImplementation(async (_token: string, id: string) => {
    trace.push(`download:${id}`); return new Blob(["document bytes"]);
  });
  api.downloadCatastoDocumentBlob.mockImplementation(async (_token: string, id: string) => {
    trace.push(`catasto:${id}`); return new Blob(["catasto bytes"]);
  });
  api.convertToHtml.mockResolvedValue({ value: "<p>Converted document</p>", messages: [] });
  api.read.mockReturnValue({ SheetNames: [], Sheets: {} });
  api.sheetToJson.mockReturnValue([]);
});
afterEach(() => {
  cleanup(); vi.restoreAllMocks();
  if (originalCreate) Object.defineProperty(URL, "createObjectURL", originalCreate);
  else Reflect.deleteProperty(URL, "createObjectURL");
  if (originalRevoke) Object.defineProperty(URL, "revokeObjectURL", originalRevoke);
  else Reflect.deleteProperty(URL, "revokeObjectURL");
});

describe("R23 actual public preview selection", () => {
  test.each(["nested", "row", "Enter", " "])("Utenze %s control downloads exactly once in read-only mode", async (activation) => {
    await ready();
    const control = row("report.PDF");
    if (activation === "nested") openDocument();
    else if (activation === "row") fireEvent.click(control);
    else { control.focus(); fireEvent.keyDown(control, { key: activation }); }
    await pdf();
    expect(api.downloadUtenzeDocumentBlob.mock.calls).toEqual([["campaign-token", "doc-A"]]);
    expect(api.downloadCatastoDocumentBlob).not.toHaveBeenCalled();
    expect(screen.getByText("Sola lettura")).toBeInTheDocument();
  });
  test("nonactivation row key does not download or open", async () => {
    await ready(); const control = row("report.PDF"); control.focus();
    fireEvent.keyDown(control, { key: "ArrowDown" });
    expect(api.downloadUtenzeDocumentBlob).not.toHaveBeenCalled();
    expect(screen.queryByText("Anteprima documento")).not.toBeInTheDocument();
  });
  test("public null-id Preview guard shows literal error without download/modal", async () => {
    await ready([documentFixture({ id: null })]); openDocument();
    expect(screen.getByText("Il documento non ha un identificativo valido per la preview.")).toBeInTheDocument();
    expect(api.downloadUtenzeDocumentBlob).not.toHaveBeenCalled();
    expect(url.create).not.toHaveBeenCalled();
    expect(screen.queryByText("Anteprima documento")).not.toBeInTheDocument();
  });
  test.each(["nested", "row", "Enter", " "])("Catasto %s control routes to Catasto download only", async (activation) => {
    await ready([], [catastoFixture()]);
    const control = row("catasto.PDF", "Correlazioni Catasto");
    if (activation === "nested") fireEvent.click(within(control).getByRole("button", { name: "Preview" }));
    else if (activation === "row") fireEvent.click(control);
    else { control.focus(); fireEvent.keyDown(control, { key: activation }); }
    await pdf("catasto.PDF");
    expect(api.downloadCatastoDocumentBlob.mock.calls).toEqual([["campaign-token", "cat-A"]]);
    expect(api.downloadUtenzeDocumentBlob).not.toHaveBeenCalled();
    expect(api.createElaborazioneRichiesta).not.toHaveBeenCalled();
  });
  test("real latest-visura card previews an existing document without a visura request", async () => {
    await ready([], [catastoFixture()]);
    fireEvent.click(screen.getByRole("button", { name: "Visualizza visura" }));
    await pdf("catasto.PDF");
    expect(api.downloadCatastoDocumentBlob.mock.calls).toEqual([["campaign-token", "cat-A"]]);
    expect(api.createElaborazioneRichiesta).not.toHaveBeenCalled();
  });
  test("pending real Blob keeps close/loading visible and defers URL/download link", async () => {
    const pending = deferred<Blob>(); const blob = new Blob(["pending pdf"]);
    api.downloadUtenzeDocumentBlob.mockReturnValueOnce(pending.promise);
    await ready(); openDocument();
    expect(within(modal()).getByText("report.PDF")).toBeInTheDocument();
    expect(screen.getByText("Caricamento anteprima...")).toBeInTheDocument();
    expect(within(modal()).getByRole("button", { name: "Chiudi" })).toBeEnabled();
    expect(within(modal()).queryByRole("link", { name: "Scarica" })).not.toBeInTheDocument();
    expect(url.create).not.toHaveBeenCalled();
    await resolveRequest(pending, blob);
    expect(await pdf()).toHaveAttribute("src", "blob:r23-1");
    expect(url.create.mock.calls).toEqual([[blob]]);
    expect(downloadLink()).toHaveAttribute("download", "report.PDF");
  });
});

describe("R23 real dispatcher and literal format presentation", () => {
  test.each([
    ["report.PDF", ".PDF", false], ["report.pdf", null, false],
    ["forced.bin", ".bin", true], ["picture.png", ".pdf", false],
  ])("PDF precedence filename=%s extension=%s is_pdf=%s", async (filename, extension, isPdf) => {
    await ready([documentFixture({ filename, extension, is_pdf: isPdf })]); openDocument(filename);
    expect(await pdf(filename)).toHaveAttribute("src", "blob:r23-1");
    expect(downloadLink()).toHaveAttribute("download", filename);
    expect(api.convertToHtml).not.toHaveBeenCalled(); expect(api.read).not.toHaveBeenCalled();
  });
  test.each([
    ["report.pdf", ".PnG"], ["photo.JPG", null],
  ])("image extension overrides filename with is_pdf false: %s/%s", async (filename, extension) => {
    await ready([documentFixture({ filename, extension, is_pdf: false })]); openDocument(filename);
    const image = await screen.findByRole("img", { name: filename });
    expect(image).toHaveAttribute("src", "blob:r23-1");
    expect(within(modal()).queryByTitle(filename)).not.toBeInTheDocument();
    expect(downloadLink()).toHaveAttribute("download", filename);
  });
  test.each(["<p>DOCX <strong>literal emphasis</strong></p>", ""])("DOCX conversion uses exact ArrayBuffer and handles value %s", async (value) => {
    const blob = new Blob(["docx adapter bytes"]); const buffer = new Uint8Array([1, 2, 3]).buffer;
    const read = vi.spyOn(blob, "arrayBuffer").mockResolvedValue(buffer);
    api.downloadUtenzeDocumentBlob.mockResolvedValueOnce(blob);
    api.convertToHtml.mockResolvedValueOnce({ value, messages: [] });
    await ready([documentFixture({ filename: "letter.DOCX", extension: null, is_pdf: false })]); openDocument("letter.DOCX");
    if (value) expect((await screen.findByText("literal emphasis")).tagName).toBe("STRONG");
    else await screen.findByText("Nessun contenuto leggibile disponibile per questo file DOCX.");
    expect(read.mock.calls).toEqual([[]]);
    expect(api.convertToHtml.mock.calls).toEqual([[{ arrayBuffer: buffer }]]);
    expect(downloadLink()).toHaveAttribute("href", "blob:r23-1");
    expect(api.read).not.toHaveBeenCalled();
  });
  test.each([".xlsx", ".xls"])("%s uses first three sheets, 25 rows and literal null/zero/false conversion", async (extension) => {
    const blob = new Blob(["spreadsheet adapter bytes"]); const buffer = new Uint8Array([4, 5]).buffer;
    vi.spyOn(blob, "arrayBuffer").mockResolvedValue(buffer);
    api.downloadUtenzeDocumentBlob.mockResolvedValueOnce(blob);
    const sheetA = { "!ref": "A1:A26" }; const sheetB = {}; const sheetC = { "!ref": "A1:E1" }; const sheetD = {};
    api.read.mockReturnValueOnce({ SheetNames: ["A", "B", "C", "D"], Sheets: { A: sheetA, B: sheetB, C: sheetC, D: sheetD } });
    api.sheetToJson.mockReturnValueOnce(Array.from({ length: 26 }, (_, i) => [`row-${i + 1}`]))
      .mockReturnValueOnce([]).mockReturnValueOnce([["keep", 0, false, null, ""]]);
    const filename = `sheet${extension}`;
    await ready([documentFixture({ filename, extension, is_pdf: false })]); openDocument(filename);
    await screen.findByText("row-25");
    expect(within(modal()).queryByText("row-26")).not.toBeInTheDocument();
    expect(within(modal()).queryByText("D", { exact: true })).not.toBeInTheDocument();
    expect(within(modal()).getByText("Foglio senza celle valorizzate.")).toBeInTheDocument();
    const sections = Array.from(modal().querySelectorAll("section"));
    expect(sections.map((section) => section.querySelector("p")?.textContent)).toEqual(["A", "B", "C"]);
    expect(within(sections[2]).getAllByRole("cell").map((cell) => cell.textContent)).toEqual(["keep", "0", "false", "—", "—"]);
    expect(api.read.mock.calls).toEqual([[buffer, { type: "array" }]]);
    expect(api.sheetToJson.mock.calls).toEqual([
      [sheetA, { header: 1, blankrows: false, defval: "" }],
      [sheetB, { header: 1, blankrows: false, defval: "" }],
      [sheetC, { header: 1, blankrows: false, defval: "" }],
    ]);
  });
  test.each(["no sheets", "empty sheet"])("spreadsheet %s has distinct empty message", async (kind) => {
    if (kind === "empty sheet") api.read.mockReturnValueOnce({ SheetNames: ["Empty"], Sheets: { Empty: {} } });
    await ready([documentFixture({ filename: "empty.xlsx", extension: ".xlsx", is_pdf: false })]); openDocument("empty.xlsx");
    await screen.findByText(kind === "no sheets" ? "Nessun dato tabellare leggibile disponibile per questo file." : "Foglio senza celle valorizzate.");
    expect(within(modal()).queryByRole("table")).not.toBeInTheDocument();
    expect(api.sheetToJson).toHaveBeenCalledTimes(kind === "no sheets" ? 0 : 1);
  });
  test.each([".txt", ".csv", ".eml"])("%s renders exact real Blob text without conversion or interpreting markup", async (extension) => {
    const content = "<tag>& literal\nsecond line"; const blob = new Blob([content]);
    const text = vi.spyOn(blob, "text"); api.downloadUtenzeDocumentBlob.mockResolvedValueOnce(blob);
    const filename = `receipt${extension}`;
    await ready([documentFixture({ filename, extension, is_pdf: false })]); openDocument(filename);
    await waitFor(() => expect(modal().querySelector("pre")?.textContent).toBe(content));
    expect(modal().querySelector("tag")).toBeNull(); expect(text).toHaveBeenCalledTimes(1);
    expect(api.convertToHtml).not.toHaveBeenCalled(); expect(api.read).not.toHaveBeenCalled();
  });
  test.each(["", "   "])("text value %j preserves empty-versus-whitespace behavior", async (content) => {
    api.downloadUtenzeDocumentBlob.mockResolvedValueOnce(new Blob([content]));
    await ready([documentFixture({ filename: "empty.txt", extension: ".txt", is_pdf: false })]); openDocument("empty.txt");
    await waitFor(() => expect(modal().querySelector("pre")?.textContent).toBe(content === "" ? "File di testo vuoto." : "   "));
  });
  test.each([
    ["report.pdf", ""], ["archive.zip", ".zip"], ["no-extension", null],
  ])("unsupported/empty extension download fallback ignores PDF MIME: %s/%s", async (filename, extension) => {
    api.downloadUtenzeDocumentBlob.mockResolvedValueOnce(new Blob(["bytes"], { type: "application/pdf" }));
    await ready([documentFixture({ filename, extension, is_pdf: false })]); openDocument(filename);
    await screen.findByText("Anteprima inline non disponibile per questo formato.");
    expect(downloadLink()).toHaveAttribute("href", "blob:r23-1");
    expect(within(modal()).getByRole("link", { name: "Scarica documento" })).toHaveAttribute("download", filename);
    expect(modal().querySelector("iframe")).toBeNull();
  });
});

describe("R23 preview errors at real boundaries", () => {
  test.each([[new Error("Download offline"), "Download offline"], ["bad download", "Errore caricamento anteprima documento"]])("blob rejection %s releases loading with no link", async (error, message) => {
    api.downloadUtenzeDocumentBlob.mockRejectedValueOnce(error); await ready(); openDocument();
    await screen.findByText(message);
    expect(screen.queryByText("Caricamento anteprima...")).not.toBeInTheDocument();
    expect(within(modal()).queryByRole("link", { name: "Scarica" })).not.toBeInTheDocument();
    expect(url.create).not.toHaveBeenCalled(); close();
    expect(screen.queryByText("Anteprima documento")).not.toBeInTheDocument();
  });
  test.each(["docx Error", "docx primitive", "xlsx read", "xlsx rows", "text read"])("%s adapter failure keeps created URL/download and suppresses body", async (boundary) => {
    const blob = new Blob(["adapter bytes"]); let filename = "letter.docx"; let extension = ".docx";
    let expected = "Adapter failed";
    if (boundary === "docx Error") api.convertToHtml.mockRejectedValueOnce(new Error(expected));
    else if (boundary === "docx primitive") { api.convertToHtml.mockRejectedValueOnce("bad conversion"); expected = "Errore caricamento anteprima documento"; }
    else if (boundary === "xlsx read") { filename = "sheet.xlsx"; extension = ".xlsx"; api.read.mockImplementationOnce(() => { throw new Error(expected); }); }
    else if (boundary === "xlsx rows") {
      filename = "sheet.xlsx"; extension = ".xlsx";
      api.read.mockReturnValueOnce({ SheetNames: ["A"], Sheets: { A: {} } });
      api.sheetToJson.mockImplementationOnce(() => { throw new Error(expected); });
    } else { filename = "note.txt"; extension = ".txt"; vi.spyOn(blob, "text").mockRejectedValueOnce(new Error(expected)); }
    api.downloadUtenzeDocumentBlob.mockResolvedValueOnce(blob);
    await ready([documentFixture({ filename, extension, is_pdf: false })]); openDocument(filename);
    await screen.findByText(expected);
    expect(downloadLink()).toHaveAttribute("href", "blob:r23-1");
    expect(modal().querySelector("iframe, img, pre, table, strong")).toBeNull();
    expect(screen.queryByText("Caricamento anteprima...")).not.toBeInTheDocument();
    expect(api.downloadUtenzeDocumentBlob).toHaveBeenCalledTimes(1);
    close(); expect(url.revoke.mock.calls).toEqual([["blob:r23-1"], ["blob:r23-1"]]);
  });
  test.each([new Error("Buffer unavailable"), "bad buffer"])("arrayBuffer failure %s occurs after URL creation", async (error) => {
    const blob = new Blob(["buffer bytes"]); vi.spyOn(blob, "arrayBuffer").mockRejectedValueOnce(error);
    api.downloadUtenzeDocumentBlob.mockResolvedValueOnce(blob);
    await ready([documentFixture({ filename: "letter.docx", extension: ".docx", is_pdf: false })]); openDocument("letter.docx");
    await screen.findByText(error instanceof Error ? "Buffer unavailable" : "Errore caricamento anteprima documento");
    expect(downloadLink()).toHaveAttribute("href", "blob:r23-1");
    expect(api.convertToHtml).not.toHaveBeenCalled();
  });
  test.each([new Error("URL unavailable"), "bad URL"])("URL creation failure %s has no link and next public open resets error", async (error) => {
    url.create.mockImplementationOnce(() => { throw error; });
    await ready(); openDocument();
    const expected = error instanceof Error ? "URL unavailable" : "Errore caricamento anteprima documento";
    await screen.findByText(expected);
    expect(within(modal()).queryByRole("link", { name: "Scarica" })).not.toBeInTheDocument();
    close(); openDocument(); await pdf();
    expect(screen.queryByText(expected)).not.toBeInTheDocument();
    expect(url.revoke).not.toHaveBeenCalled();
  });
});

describe("R23 URL lifecycle, native focus and listener identities", () => {
  test.each(["Chiudi", "Escape"])("loaded %s preserves duplicate revoke and permits a clean reopen", async (action) => {
    const view = await ready(); openDocument(); await pdf();
    if (action === "Chiudi") close(); else fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByText("Anteprima documento")).not.toBeInTheDocument();
    expect(url.revoke.mock.calls).toEqual([["blob:r23-1"], ["blob:r23-1"]]);
    openDocument(); expect(await pdf()).toHaveAttribute("src", "blob:r23-2");
    view.unmount();
    expect(url.revoke.mock.calls).toEqual([["blob:r23-1"], ["blob:r23-1"], ["blob:r23-2"]]);
    freezeTrace(`loaded-${action}-reopen-unmount`);
  });
  test("loaded unmount revokes once without a close action", async () => {
    const view = await ready(); openDocument(); await pdf(); view.unmount();
    expect(url.revoke.mock.calls).toEqual([["blob:r23-1"]]); freezeTrace("loaded-unmount");
  });
  test.each(["resolve", "reject"])("close-before-blob followed by late %s leaves modal absent", async (outcome) => {
    const pending = deferred<Blob>(); const blob = new Blob(["late bytes"]);
    api.downloadUtenzeDocumentBlob.mockReturnValueOnce(pending.promise);
    const view = await ready(); openDocument(); close();
    expect(url.revoke).not.toHaveBeenCalled();
    if (outcome === "resolve") {
      await resolveRequest(pending, blob);
      expect(url.create.mock.calls).toEqual([[blob]]); expect(url.revoke).not.toHaveBeenCalled();
    } else {
      await rejectRequest(pending, new Error("Late closed failure"));
      expect(url.create).not.toHaveBeenCalled(); expect(screen.queryByText("Late closed failure")).not.toBeInTheDocument();
    }
    expect(screen.queryByText("Anteprima documento")).not.toBeInTheDocument();
    view.unmount(); expect(url.revoke).toHaveBeenCalledTimes(outcome === "resolve" ? 1 : 0);
    freezeTrace(`closed-before-blob-${outcome}`);
  });
  test("close during DOCX conversion revokes twice and late HTML does not reopen", async () => {
    const conversion = deferred<{ value: string; messages: never[] }>();
    api.convertToHtml.mockReturnValueOnce(conversion.promise);
    const view = await ready([documentFixture({ filename: "letter.docx", extension: ".docx", is_pdf: false })]); openDocument("letter.docx");
    await waitFor(() => expect(api.convertToHtml).toHaveBeenCalledTimes(1));
    expect(downloadLink()).toHaveAttribute("href", "blob:r23-1");
    expect(screen.getByText("Caricamento anteprima...")).toBeInTheDocument(); close();
    expect(url.revoke.mock.calls).toEqual([["blob:r23-1"], ["blob:r23-1"]]);
    await resolveRequest(conversion, { value: "<p>Late closed HTML</p>", messages: [] });
    expect(screen.queryByText("Anteprima documento")).not.toBeInTheDocument();
    expect(screen.queryByText("Late closed HTML")).not.toBeInTheDocument();
    view.unmount(); expect(url.revoke).toHaveBeenCalledTimes(2); freezeTrace("closed-during-docx");
  });
  test("focused public row replacement downloads before duplicate revoke without overlay pointer clicks", async () => {
    const view = await ready(); const control = row("report.PDF"); control.focus();
    expect(document.activeElement).toBe(control); fireEvent.keyDown(control, { key: "Enter" }); await pdf();
    expect(document.activeElement).toBe(control);
    const pending = deferred<Blob>();
    api.downloadUtenzeDocumentBlob.mockImplementationOnce(() => { trace.push("download:doc-A"); return pending.promise; });
    const offset = trace.length;
    fireEvent.keyDown(document.activeElement!, { key: "Enter" });
    expect(document.activeElement).toBe(control);
    expect(trace.slice(offset, offset + 2)).toEqual(["download:doc-A", "revoke:blob:r23-1"]);
    expect(url.revoke.mock.calls).toEqual([["blob:r23-1"], ["blob:r23-1"]]);
    await resolveRequest(pending, new Blob(["replacement bytes"]));
    expect(await pdf()).toHaveAttribute("src", "blob:r23-2");
    expect(api.downloadUtenzeDocumentBlob.mock.calls).toEqual([["campaign-token", "doc-A"], ["campaign-token", "doc-A"]]);
    view.unmount(); freezeTrace("focused-row-replacement", { publicFocusProven: true });
  });
  test("keydown listener callback identity is removed/reinstalled with URL and removed on close", async () => {
    const pending = deferred<Blob>(); api.downloadUtenzeDocumentBlob.mockReturnValueOnce(pending.promise);
    const view = await ready();
    const add = vi.spyOn(window, "addEventListener"); const remove = vi.spyOn(window, "removeEventListener");
    openDocument();
    const first = add.mock.calls.filter((call) => call[0] === "keydown");
    expect(first).toHaveLength(1);
    await resolveRequest(pending, new Blob(["listener bytes"])); await pdf();
    const added = add.mock.calls.filter((call) => call[0] === "keydown");
    expect(added).toHaveLength(2);
    expect(remove.mock.calls.filter((call) => call[0] === "keydown").map((call) => call[1])).toEqual([added[0][1]]);
    close();
    expect(remove.mock.calls.filter((call) => call[0] === "keydown").map((call) => call[1])).toEqual([added[0][1], added[1][1]]);
    view.unmount();
    expect(add.mock.calls.filter((call) => call[0] === "keydown")).toHaveLength(2);
    expect(remove.mock.calls.filter((call) => call[0] === "keydown")).toHaveLength(2);
    freezeTrace("listener-identities", { added: added.map((call) => add.mock.invocationCallOrder[add.mock.calls.indexOf(call)]), removed: remove.mock.invocationCallOrder });
  });
  test("non-Escape and backdrop do not close the preview", async () => {
    await ready(); openDocument(); await pdf();
    fireEvent.keyDown(window, { key: "ArrowRight" });
    fireEvent.click(modal().parentElement!);
    expect(screen.getByText("Anteprima documento")).toBeInTheDocument(); expect(url.revoke).not.toHaveBeenCalled();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByText("Anteprima documento")).not.toBeInTheDocument();
  });
});

describe("R23 literal late-response races through close and public reopen", () => {
  const firstDocument = documentFixture({ filename: "first.pdf", nas_path: "/archive/first.pdf" });
  const secondDocument = documentFixture({ id: "doc-B", filename: "second.pdf", nas_path: "/archive/second.pdf" });
  test("late first Blob replaces the newer URL while second filename stays selected", async () => {
    const first = deferred<Blob>(); const firstBlob = new Blob(["first old bytes"]); const secondBlob = new Blob(["second new bytes"]);
    api.downloadUtenzeDocumentBlob.mockReturnValueOnce(first.promise).mockResolvedValueOnce(secondBlob);
    const view = await ready([firstDocument, secondDocument]); openDocument("first.pdf"); close();
    openDocument("second.pdf"); expect(await pdf("second.pdf")).toHaveAttribute("src", "blob:r23-1");
    await resolveRequest(first, firstBlob);
    expect(screen.getByTitle("second.pdf")).toHaveAttribute("src", "blob:r23-2");
    expect(downloadLink()).toHaveAttribute("download", "second.pdf");
    expect(url.create.mock.calls).toEqual([[secondBlob], [firstBlob]]);
    expect(url.revoke.mock.calls).toEqual([["blob:r23-1"]]);
    expect(api.downloadUtenzeDocumentBlob.mock.calls).toEqual([["campaign-token", "doc-A"], ["campaign-token", "doc-B"]]);
    view.unmount(); freezeTrace("late-first-blob-newer-filename");
  });
  test("late old DOCX conversion contaminates second PDF kind/content without replacing its URL", async () => {
    const conversion = deferred<{ value: string; messages: never[] }>(); api.convertToHtml.mockReturnValueOnce(conversion.promise);
    const old = documentFixture({ filename: "first.docx", extension: ".docx", is_pdf: false, nas_path: "/archive/first.docx" });
    const view = await ready([old, secondDocument]); openDocument("first.docx");
    await waitFor(() => expect(api.convertToHtml).toHaveBeenCalledTimes(1)); close();
    openDocument("second.pdf"); await pdf("second.pdf");
    await resolveRequest(conversion, { value: "<p>Old converted content</p>", messages: [] });
    expect(within(modal()).getByText("Old converted content")).toBeInTheDocument();
    expect(within(modal()).getByText("second.pdf")).toBeInTheDocument();
    expect(screen.queryByTitle("second.pdf")).not.toBeInTheDocument();
    expect(downloadLink()).toHaveAttribute("href", "blob:r23-2");
    expect(downloadLink()).toHaveAttribute("download", "second.pdf");
    expect(url.revoke.mock.calls).toEqual([["blob:r23-1"], ["blob:r23-1"]]);
    view.unmount(); freezeTrace("old-conversion-newer-pdf");
  });
  test("old rejection clears newer loading and persists as error after newer Blob succeeds", async () => {
    const first = deferred<Blob>(); const second = deferred<Blob>();
    api.downloadUtenzeDocumentBlob.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const view = await ready([firstDocument, secondDocument]); openDocument("first.pdf"); close(); openDocument("second.pdf");
    expect(screen.getByText("Caricamento anteprima...")).toBeInTheDocument();
    await rejectRequest(first, new Error("Stale first failure"));
    expect(within(modal()).getByText("Stale first failure")).toBeInTheDocument();
    expect(screen.queryByText("Caricamento anteprima...")).not.toBeInTheDocument();
    await resolveRequest(second, new Blob(["newer bytes"]));
    expect(within(modal()).getByText("Stale first failure")).toBeInTheDocument();
    expect(downloadLink()).toHaveAttribute("download", "second.pdf");
    expect(screen.queryByTitle("second.pdf")).not.toBeInTheDocument();
    view.unmount(); freezeTrace("old-error-newer-loading");
  });
});
