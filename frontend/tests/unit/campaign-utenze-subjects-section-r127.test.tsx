import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import JSZip from "jszip";
import * as XLSX from "xlsx";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { UtenzeSubjectsSection } from "@/components/utenze/utenze-subjects-section";
import type {
  UtenzeAuditLog,
  UtenzeCsvImportResult,
  UtenzeDocument,
  UtenzeSubjectDetail,
  UtenzeSubjectListItem,
} from "@/types/api";

const api = vi.hoisted(() => ({
  getUtenzeSubjects: vi.fn(),
  getUtenzeSubject: vi.fn(),
  getUtenzeSubjectAuditLog: vi.fn(),
  importUtenzeSubjectsCsv: vi.fn(),
  downloadUtenzeDocumentBlob: vi.fn(),
  downloadUtenzeExportBlob: vi.fn(),
  createUtenzeSubject: vi.fn(),
  importUtenzeSubjectFromNas: vi.fn(),
  getUtenzeSubjectPaymentNotices: vi.fn(),
  listCapacitasInCassSyncJobs: vi.fn(),
  getAvvisiBySubject: vi.fn(),
  convertToHtml: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getUtenzeSubjects: api.getUtenzeSubjects,
  getUtenzeSubject: api.getUtenzeSubject,
  getUtenzeSubjectAuditLog: api.getUtenzeSubjectAuditLog,
  importUtenzeSubjectsCsv: api.importUtenzeSubjectsCsv,
  downloadUtenzeDocumentBlob: api.downloadUtenzeDocumentBlob,
  downloadUtenzeExportBlob: api.downloadUtenzeExportBlob,
  createUtenzeSubject: api.createUtenzeSubject,
  importUtenzeSubjectFromNas: api.importUtenzeSubjectFromNas,
  getUtenzeSubjectPaymentNotices: api.getUtenzeSubjectPaymentNotices,
  listCapacitasInCassSyncJobs: api.listCapacitasInCassSyncJobs,
}));
vi.mock("@/lib/ruolo-api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/ruolo-api")>()),
  getAvvisiBySubject: api.getAvvisiBySubject,
}));
// mammoth's Node build (resolved by vitest) rejects the `arrayBuffer` option used by the
// browser bundle, so the DOCX converter is replaced at the library boundary.
vi.mock("mammoth", () => ({ convertToHtml: api.convertToHtml }));

type Deferred<T> = { promise: Promise<T>; resolve: (value: T) => void; reject: (reason: unknown) => void };

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function listItem(overrides: Partial<UtenzeSubjectListItem> = {}): UtenzeSubjectListItem {
  return {
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
    document_count: 2,
    created_at: "2026-10-01T08:00:00Z",
    updated_at: "2026-10-02T08:00:00Z",
    ...overrides,
  };
}

function documentFixture(overrides: Partial<UtenzeDocument> = {}): UtenzeDocument {
  return {
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
    ...overrides,
  } as UtenzeDocument;
}

function personDetail(overrides: Partial<UtenzeSubjectDetail> = {}): UtenzeSubjectDetail {
  return {
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
      email: "mario@example.test",
      telefono: "0783000000",
      note: null,
      created_at: "2026-10-01T08:00:00Z",
      updated_at: "2026-10-02T08:00:00Z",
    },
    company: null,
    documents: [],
    audit_log: [],
    catasto_documents: [],
    ...overrides,
  };
}

function companyDetail(overrides: Partial<UtenzeSubjectDetail> = {}): UtenzeSubjectDetail {
  return personDetail({
    id: "subject-2",
    subject_type: "company",
    nas_folder_path: null,
    nas_folder_letter: null,
    person: null,
    company: {
      subject_id: "subject-2",
      ragione_sociale: "Agricola Srl",
      partita_iva: "01234567890",
      codice_fiscale: "01234567890",
      forma_giuridica: null,
      sede_legale: null,
      comune_sede: null,
      cap: null,
      email_pec: "agricola@pec.test",
      telefono: "0783111111",
      note: null,
      created_at: "2026-10-01T08:00:00Z",
      updated_at: "2026-10-02T08:00:00Z",
    },
    ...overrides,
  });
}

function auditEntry(overrides: Partial<UtenzeAuditLog> = {}): UtenzeAuditLog {
  return {
    id: "audit-1",
    subject_id: "subject-1",
    changed_by_user_id: null,
    action: "csv_import_created",
    diff_json: null,
    changed_at: "2026-10-03T08:00:00Z",
    ...overrides,
  };
}

function listResponse(items: UtenzeSubjectListItem[], total = items.length) {
  return { items, total, page: 1, page_size: 20 };
}

// tests/setup-vitest.ts swaps the global Blob for Node's Blob, whose arrayBuffer() returns an
// ArrayBuffer from another realm that xlsx does not recognise. Downloaded spreadsheets are
// therefore served as Blobs whose bytes come back in the page realm, as a browser would do.
function pageRealmBlob(bytes: Uint8Array): Blob {
  const blob = new Blob([bytes]);
  Object.defineProperty(blob, "arrayBuffer", {
    value: async () => {
      const buffer = new ArrayBuffer(bytes.byteLength);
      new Uint8Array(buffer).set(bytes);
      return buffer;
    },
  });
  return blob;
}

async function xlsxBlob(
  sheets: Record<string, unknown[][]>,
  decorate: (workbook: XLSX.WorkBook) => void = () => undefined,
): Promise<Blob> {
  const workbook = XLSX.utils.book_new();
  for (const [name, rows] of Object.entries(sheets)) {
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(rows), name);
  }
  decorate(workbook);
  const buffer = XLSX.write(workbook, { type: "array", bookType: "xlsx" }) as ArrayBuffer;
  return pageRealmBlob(new Uint8Array(buffer));
}

async function xlsxBlobWithoutSheets(): Promise<Blob> {
  const zip = new JSZip();
  zip.file(
    "[Content_Types].xml",
    '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/></Types>',
  );
  zip.file(
    "_rels/.rels",
    '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
  );
  zip.file(
    "xl/workbook.xml",
    '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets></sheets></workbook>',
  );
  return pageRealmBlob(await zip.generateAsync({ type: "uint8array" }));
}

// Preview renderers lazy-load mammoth/xlsx; a cold transform under --no-cache can exceed
// the default 1s findBy window on a slow disk.
const DYNAMIC_IMPORT_WAIT = { timeout: 4000 };

const createObjectURL = vi.fn();
const revokeObjectURL = vi.fn();
let objectUrlCounter = 0;

function renderSection(token = "token") {
  return render(<UtenzeSubjectsSection token={token} />);
}

async function renderLoaded(items: UtenzeSubjectListItem[] = [listItem()], total = items.length, token = "token") {
  api.getUtenzeSubjects.mockResolvedValue(listResponse(items, total));
  const view = renderSection(token);
  await waitFor(() => expect(screen.queryByText("Caricamento utenti in corso.")).not.toBeInTheDocument());
  return view;
}

function pagerButton(name: "Precedente" | "Successiva"): HTMLElement {
  const pager = screen.getByText(/^Pagina \d+ di \d+ · \d+ record$/).parentElement as HTMLElement;
  return within(pager).getByRole("button", { name });
}

function lastListQuery() {
  return api.getUtenzeSubjects.mock.calls.at(-1)?.[1];
}

function detailDialogRegion(): HTMLElement {
  return screen.getByText("Vista rapida del registro").closest("div.relative") as HTMLElement;
}

async function openDetail(name = "Rossi Mario") {
  fireEvent.click(screen.getByText(name));
  await screen.findByText("Vista rapida del registro");
}

async function openDocumentPreview(filename: string) {
  fireEvent.click(await screen.findByText(filename));
  await screen.findByText("Anteprima documento");
}

beforeEach(() => {
  vi.clearAllMocks();
  objectUrlCounter = 0;
  createObjectURL.mockImplementation(() => {
    objectUrlCounter += 1;
    return `blob:preview-${objectUrlCounter}`;
  });
  Object.defineProperty(URL, "createObjectURL", { configurable: true, writable: true, value: createObjectURL });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, writable: true, value: revokeObjectURL });
  api.getUtenzeSubjectPaymentNotices.mockResolvedValue([]);
  api.listCapacitasInCassSyncJobs.mockResolvedValue([]);
  api.getAvvisiBySubject.mockResolvedValue([]);
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("UtenzeSubjectsSection list", () => {
  test("shows the loading state, then the empty table and a single page", async () => {
    const pending = deferred<ReturnType<typeof listResponse>>();
    api.getUtenzeSubjects.mockReturnValue(pending.promise);
    renderSection();

    expect(screen.getByText("Caricamento utenti in corso.")).toBeInTheDocument();
    await act(async () => pending.resolve(listResponse([], 0)));

    expect(await screen.findByText("Nessun utente trovato")).toBeInTheDocument();
    expect(screen.getByText("Pagina 1 di 1 · 0 record")).toBeInTheDocument();
    expect(pagerButton("Precedente")).toBeDisabled();
    expect(pagerButton("Successiva")).toBeDisabled();
    expect(api.getUtenzeSubjects).toHaveBeenCalledWith("token", {
      page: 1,
      pageSize: 20,
      search: undefined,
      subjectType: undefined,
      status: undefined,
      letter: undefined,
      requiresReview: undefined,
    });
  });

  test.each([
    [new Error("Backend non disponibile"), "Backend non disponibile"],
    ["boom", "Errore caricamento utenti"],
  ])("shows list load errors (%s)", async (failure, message) => {
    api.getUtenzeSubjects.mockRejectedValue(failure);
    renderSection();
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.queryByText("Caricamento utenti in corso.")).not.toBeInTheDocument();
  });

  test("renders identifier, archive and status fallbacks for each row", async () => {
    await renderLoaded([
      listItem(),
      listItem({
        id: "subject-2",
        display_name: "Agricola Srl",
        source_name_raw: "Agricola_Srl",
        subject_type: "company",
        codice_fiscale: null,
        partita_iva: "01234567890",
        nas_folder_letter: null,
        document_count: 0,
        requires_review: true,
      }),
      listItem({
        id: "subject-3",
        display_name: "Senza Dati",
        source_name_raw: "Senza_Dati",
        subject_type: "unknown",
        codice_fiscale: null,
        partita_iva: null,
        source_external_id: "ANOMALIA-999",
        updated_at: "",
      }),
    ]);

    const rows = screen.getAllByRole("row").slice(1);
    expect(within(rows[0]).getByText("RSSMRA80A01H501U")).toBeInTheDocument();
    expect(within(rows[0]).getByText("R · 2 doc")).toBeInTheDocument();
    expect(within(rows[0]).getByText("active")).toBeInTheDocument();
    expect(within(rows[1]).getByText("01234567890")).toBeInTheDocument();
    expect(within(rows[1]).getByText("? · 0 doc")).toBeInTheDocument();
    expect(within(rows[1]).getByText("Review")).toHaveClass("bg-amber-50");
    expect(within(rows[2]).getAllByText("—").length).toBeGreaterThanOrEqual(2);
    expect(within(rows[2]).getByText("Anomalia")).toHaveClass("bg-red-50");
  });

  test("forwards filters to the list query and resets to the first page", async () => {
    await renderLoaded([listItem()], 45);
    expect(screen.getByText("Pagina 1 di 3 · 45 record")).toBeInTheDocument();

    fireEvent.click(pagerButton("Successiva"));
    await waitFor(() => expect(lastListQuery()).toMatchObject({ page: 2 }));
    fireEvent.click(pagerButton("Successiva"));
    await waitFor(() => expect(lastListQuery()).toMatchObject({ page: 3 }));
    expect(pagerButton("Successiva")).toBeDisabled();
    fireEvent.click(pagerButton("Precedente"));
    await waitFor(() => expect(lastListQuery()).toMatchObject({ page: 2 }));

    const search = screen.getByPlaceholderText("Cerca per nome, cognome o CF...");
    fireEvent.change(search, { target: { value: "ro" } });
    expect(await screen.findByText("Digita almeno 3 caratteri per avviare la ricerca.")).toBeInTheDocument();
    await waitFor(() => expect(lastListQuery()).toMatchObject({ page: 1, search: undefined }));

    fireEvent.change(search, { target: { value: " ros " } });
    await waitFor(() => expect(lastListQuery()).toMatchObject({ search: "ros" }));
    expect(screen.queryByText("Digita almeno 3 caratteri per avviare la ricerca.")).not.toBeInTheDocument();

    const [typeSelect, statusSelect, reviewSelect] = screen.getAllByRole("combobox");
    fireEvent.change(typeSelect, { target: { value: "company" } });
    fireEvent.change(statusSelect, { target: { value: "inactive" } });
    fireEvent.change(screen.getByPlaceholderText("A-Z"), { target: { value: "bx" } });
    fireEvent.change(reviewSelect, { target: { value: "false" } });
    await waitFor(() =>
      expect(lastListQuery()).toEqual({
        page: 1,
        pageSize: 20,
        search: "ros",
        subjectType: "company",
        status: "inactive",
        letter: "B",
        requiresReview: false,
      }),
    );
    expect(screen.getByPlaceholderText("A-Z")).toHaveValue("B");

    fireEvent.change(reviewSelect, { target: { value: "true" } });
    await waitFor(() => expect(lastListQuery()).toMatchObject({ requiresReview: true }));
  });

  test("toggles the anomalies quick filter on and off", async () => {
    await renderLoaded();
    const toggle = screen.getByRole("button", { name: "Anomalie da completare" });
    expect(toggle).toHaveClass("bg-red-50");

    fireEvent.click(toggle);
    await waitFor(() => expect(lastListQuery()).toMatchObject({ requiresReview: true, subjectType: "unknown" }));
    expect(toggle).toHaveClass("bg-red-600");

    fireEvent.click(toggle);
    await waitFor(() => expect(lastListQuery()).toMatchObject({ requiresReview: undefined, subjectType: undefined }));
    expect(toggle).toHaveClass("bg-red-50");
  });
});

describe("UtenzeSubjectsSection CSV import", () => {
  const csvFile = new File(["Codice Fiscale;Cognome\n"], "anagrafica.csv", { type: "text/csv" });

  function selectCsv(file: File | null) {
    const input = document.getElementById("anagrafica-csv-upload") as HTMLInputElement;
    fireEvent.change(input, { target: { files: file ? [file] : [] } });
  }

  test("keeps the import action disabled until a file is selected", async () => {
    await renderLoaded();
    expect(screen.getByText("Nessun file selezionato")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Importa CSV" })).toBeDisabled();

    selectCsv(csvFile);
    expect(screen.getByText("anagrafica.csv")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Importa CSV" })).toBeEnabled();

    selectCsv(null);
    expect(screen.getByText("Nessun file selezionato")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Importa CSV" })).toBeDisabled();
  });

  test("shows upload progress, then a successful summary and refreshes page one", async () => {
    await renderLoaded([listItem()], 45);
    fireEvent.click(pagerButton("Successiva"));
    await waitFor(() => expect(lastListQuery()).toMatchObject({ page: 2 }));

    const upload = deferred<UtenzeCsvImportResult>();
    let reportProgress: (value: number) => void = () => undefined;
    api.importUtenzeSubjectsCsv.mockImplementation((_token: string, _file: File, onProgress: (value: number) => void) => {
      reportProgress = onProgress;
      return upload.promise;
    });

    selectCsv(csvFile);
    fireEvent.click(screen.getByRole("button", { name: "Importa CSV" }));
    expect(await screen.findByRole("button", { name: "Import in corso..." })).toBeDisabled();
    expect(screen.getByText("Upload CSV in corso")).toBeInTheDocument();
    expect(screen.getByText("0%")).toBeInTheDocument();

    act(() => reportProgress(40));
    expect(screen.getByText("40%")).toBeInTheDocument();
    expect(screen.getByText("Trasferimento file verso il backend.")).toBeInTheDocument();
    act(() => reportProgress(100));
    expect(screen.getByText("Upload completato, elaborazione in corso.")).toBeInTheDocument();

    api.getUtenzeSubjects.mockClear();
    await act(async () =>
      upload.resolve({ total_rows: 3, created_subjects: 2, updated_subjects: 1, skipped_rows: 0, errors: [] }),
    );

    expect(await screen.findByText("Import CSV completato: 2 creati, 1 aggiornati, 0 scartati.")).toBeInTheDocument();
    expect(screen.getByText("Import completato")).toBeInTheDocument();
    expect(screen.getByText("Successo")).toBeInTheDocument();
    expect(screen.queryByText("Righe scartate")).not.toBeInTheDocument();
    expect(screen.queryByText("Upload CSV in corso")).not.toBeInTheDocument();
    expect(screen.getByText("Nessun file selezionato")).toBeInTheDocument();
    expect(api.importUtenzeSubjectsCsv).toHaveBeenCalledWith("token", csvFile, expect.any(Function));
    await waitFor(() => expect(api.getUtenzeSubjects).toHaveBeenCalledWith("token", expect.objectContaining({ page: 1 })));
    expect(screen.getByText("Pagina 1 di 3 · 45 record")).toBeInTheDocument();
  });

  test("shows warning summary with the first 20 skipped rows and the overflow note", async () => {
    await renderLoaded();
    const errors = Array.from({ length: 22 }, (_, index) => ({
      row_number: index + 2,
      message: `Errore riga ${index + 2}`,
      codice_fiscale: index === 0 ? "RSSMRA80A01H501U" : null,
    }));
    api.importUtenzeSubjectsCsv.mockResolvedValue({
      total_rows: 25,
      created_subjects: 2,
      updated_subjects: 1,
      skipped_rows: 22,
      errors,
    });

    selectCsv(csvFile);
    fireEvent.click(screen.getByRole("button", { name: "Importa CSV" }));

    expect(await screen.findByText("Import completato con warning")).toBeInTheDocument();
    expect(screen.getByText("Warning")).toBeInTheDocument();
    expect(screen.getByText("Righe scartate")).toBeInTheDocument();
    expect(screen.getByText(/Sono mostrati i primi 20 casi/)).toBeInTheDocument();
    expect(screen.getByText("Riga 2 · RSSMRA80A01H501U")).toBeInTheDocument();
    expect(screen.getByText("Riga 3")).toBeInTheDocument();
    expect(screen.getByText("Errore riga 21")).toBeInTheDocument();
    expect(screen.queryByText("Errore riga 22")).not.toBeInTheDocument();
    expect(screen.getByText("Altre 2 righe scartate non mostrate in questo riepilogo.")).toBeInTheDocument();
  });

  test("shows few skipped rows without the overflow note", async () => {
    await renderLoaded();
    api.importUtenzeSubjectsCsv.mockResolvedValue({
      total_rows: 2,
      created_subjects: 1,
      updated_subjects: 0,
      skipped_rows: 1,
      errors: [{ row_number: 3, message: "CF non valido", codice_fiscale: null }],
    });
    selectCsv(csvFile);
    fireEvent.click(screen.getByRole("button", { name: "Importa CSV" }));

    expect(await screen.findByText(/Sono mostrati i primi 1 casi/)).toBeInTheDocument();
    expect(screen.queryByText(/righe scartate non mostrate/)).not.toBeInTheDocument();
  });

  test.each([
    [new Error("CSV non valido"), "CSV non valido"],
    [{ detail: "x" }, "Errore import CSV"],
  ])("shows import errors and keeps the selected file (%s)", async (failure, message) => {
    await renderLoaded();
    api.importUtenzeSubjectsCsv.mockRejectedValue(failure);
    selectCsv(csvFile);
    fireEvent.click(screen.getByRole("button", { name: "Importa CSV" }));

    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.getByText("anagrafica.csv")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Importa CSV" })).toBeEnabled();
  });
});

describe("UtenzeSubjectsSection export and creation", () => {
  test.each([
    ["csv", "Export CSV", "Export CSV..."],
    ["xlsx", "Export XLSX", "Export XLSX..."],
  ] as const)("exports %s with the raw filters and triggers a download", async (format, label, busyLabel) => {
    await renderLoaded();
    fireEvent.change(screen.getByPlaceholderText("Cerca per nome, cognome o CF..."), { target: { value: "ro" } });
    fireEvent.change(screen.getAllByRole("combobox")[2], { target: { value: "true" } });

    const exportBlob = new Blob(["export"]);
    const pendingExport = deferred<Blob>();
    api.downloadUtenzeExportBlob.mockReturnValue(pendingExport.promise);
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    const timeoutSpy = vi.spyOn(window, "setTimeout");

    fireEvent.click(screen.getByRole("button", { name: label }));
    expect(screen.getByRole("button", { name: busyLabel })).toBeDisabled();
    await act(async () => pendingExport.resolve(exportBlob));

    expect(await screen.findByRole("button", { name: label })).toBeEnabled();
    expect(api.downloadUtenzeExportBlob).toHaveBeenCalledWith("token", {
      format,
      search: "ro",
      subjectType: undefined,
      status: undefined,
      letter: undefined,
      requiresReview: true,
    });
    expect(createObjectURL).toHaveBeenCalledWith(exportBlob);
    const anchor = clickSpy.mock.instances[0] as unknown as HTMLAnchorElement;
    expect(anchor.download).toBe(`utenze-export.${format}`);
    expect(anchor.href).toBe("blob:preview-1");

    const revokeCall = timeoutSpy.mock.calls.find(([, delay]) => delay === 1000);
    expect(revokeCall).toBeDefined();
    (revokeCall?.[0] as () => void)();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:preview-1");
    clickSpy.mockRestore();
    timeoutSpy.mockRestore();
  });

  test.each([
    [new Error("Export fallito"), "Export fallito"],
    [null, "Errore export utenze"],
  ])("shows export errors (%s)", async (failure, message) => {
    await renderLoaded();
    api.downloadUtenzeExportBlob.mockRejectedValue(failure);
    fireEvent.click(screen.getByRole("button", { name: "Export CSV" }));
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export CSV" })).toBeEnabled();
  });

  test("creates a subject through the trigger and reloads the first page", async () => {
    await renderLoaded([listItem()], 45);
    fireEvent.click(pagerButton("Successiva"));
    await waitFor(() => expect(lastListQuery()).toMatchObject({ page: 2 }));
    api.createUtenzeSubject.mockResolvedValue({ id: "subject-new" });

    fireEvent.click(screen.getByRole("button", { name: "Crea nuovo utente" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Cognome"), { target: { value: "Verdi" } });
    fireEvent.change(within(dialog).getByLabelText("Nome"), { target: { value: "Anna" } });
    api.getUtenzeSubjects.mockClear();
    fireEvent.click(within(dialog).getByRole("button", { name: "Crea utente" }));

    expect(await screen.findByText("Utente creato correttamente.")).toBeInTheDocument();
    expect(api.createUtenzeSubject).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(api.getUtenzeSubjects).toHaveBeenCalledWith("token", expect.objectContaining({ page: 1 })));
    expect(screen.getByText("Pagina 1 di 3 · 45 record")).toBeInTheDocument();
  });
});

describe("UtenzeSubjectsSection detail drawer", () => {
  test("loads a person detail, switches tabs and closes with the button", async () => {
    await renderLoaded();
    const pendingDetail = deferred<UtenzeSubjectDetail>();
    api.getUtenzeSubject.mockReturnValue(pendingDetail.promise);

    await openDetail();
    expect(screen.getByText("Caricamento utente in corso.")).toBeInTheDocument();
    await act(async () => pendingDetail.resolve(personDetail()));

    const region = detailDialogRegion();
    expect(within(region).getByRole("heading", { name: "Rossi Mario" })).toBeInTheDocument();
    expect(within(region).getByRole("link", { name: "Apri pagina completa" })).toHaveAttribute("href", "/utenze/subject-1");
    expect(within(region).getByText("Utenza persona")).toBeInTheDocument();
    expect(within(region).getByText("mario@example.test")).toBeInTheDocument();
    expect(within(region).getByText("Cabras")).toBeInTheDocument();
    expect(within(region).queryByText("Utenza societa")).not.toBeInTheDocument();
    expect(within(region).getByText("Nessun documento associato a questo utente.")).toBeInTheDocument();
    expect(within(region).getByText("Codice fiscale:").parentElement).toHaveTextContent("Codice fiscale: RSSMRA80A01H501U");
    expect(within(region).getByText("Lettera archivio:").parentElement).toHaveTextContent("Lettera archivio: R");
    await waitFor(() => expect(api.getAvvisiBySubject).toHaveBeenCalledWith("token", "subject-1"));
    expect(screen.queryByText("Caricamento utente in corso.")).not.toBeInTheDocument();

    fireEvent.click(within(region).getByRole("button", { name: "Avvisi di pagamento" }));
    await waitFor(() => expect(api.getUtenzeSubjectPaymentNotices).toHaveBeenCalledWith("token", "subject-1"));
    expect(within(region).queryByText("Documenti associati")).not.toBeInTheDocument();
    expect(within(region).getByRole("button", { name: "Avvisi di pagamento" })).toHaveClass("bg-[#1D4E35]");

    fireEvent.click(within(region).getByRole("button", { name: "Scheda soggetto" }));
    expect(within(region).getByText("Documenti associati")).toBeInTheDocument();

    fireEvent.click(within(region).getByRole("button", { name: "Chiudi" }));
    expect(screen.queryByText("Vista rapida del registro")).not.toBeInTheDocument();
  });

  test("renders company fallbacks and closes with the backdrop", async () => {
    await renderLoaded([listItem({ id: "subject-2", display_name: "Agricola Srl" })]);
    api.getUtenzeSubject.mockResolvedValue(
      companyDetail({
        documents: [documentFixture({ id: "doc-9", filename: "contratto.bin", extension: null, is_pdf: false })],
        audit_log: [auditEntry()],
      }),
    );
    await openDetail("Agricola Srl");

    const region = detailDialogRegion();
    expect(await within(region).findByRole("heading", { name: "Agricola Srl" })).toBeInTheDocument();
    expect(within(region).getByText("Utenza societa")).toBeInTheDocument();
    expect(within(region).getByText("agricola@pec.test")).toBeInTheDocument();
    expect(within(region).queryByText("Utenza persona")).not.toBeInTheDocument();
    expect(within(region).getByText("contratto.bin")).toBeInTheDocument();
    expect(within(region).getByText("file")).toBeInTheDocument();
    expect(within(region).getAllByText("n/d").length).toBeGreaterThanOrEqual(2);

    fireEvent.click(screen.getByRole("button", { name: "Chiudi dettaglio utente" }));
    expect(screen.queryByText("Vista rapida del registro")).not.toBeInTheDocument();
  });

  test("renders generic subject fallbacks and hides token-bound sections without a token", async () => {
    await renderLoaded([listItem()], 1, "");
    api.getUtenzeSubject.mockResolvedValue(
      personDetail({
        person: null,
        company: null,
        nas_folder_letter: null,
        nas_folder_path: null,
      }),
    );
    await openDetail();

    const region = detailDialogRegion();
    expect(await within(region).findByRole("heading", { name: "Utente" })).toBeInTheDocument();
    expect(within(region).getAllByText("n/d")).toHaveLength(4);
    expect(within(region).queryByText("Utenza persona")).not.toBeInTheDocument();
    expect(within(region).queryByText("Utenza societa")).not.toBeInTheDocument();

    fireEvent.click(within(region).getByRole("button", { name: "Avvisi di pagamento" }));
    expect(within(region).queryByText("Documenti associati")).not.toBeInTheDocument();
    expect(api.getAvvisiBySubject).not.toHaveBeenCalled();
    expect(api.getUtenzeSubjectPaymentNotices).not.toHaveBeenCalled();
  });

  test.each([
    [
      "person",
      personDetail({
        person: {
          ...(personDetail().person as NonNullable<UtenzeSubjectDetail["person"]>),
          email: null,
          telefono: null,
          comune_nascita: null,
          comune_residenza: null,
        },
      }),
      "Utenza persona",
      ["Email:", "Telefono:", "Comune nascita:", "Comune residenza:"],
    ],
    [
      "company",
      companyDetail({
        company: {
          ...(companyDetail().company as NonNullable<UtenzeSubjectDetail["company"]>),
          email_pec: null,
          telefono: null,
        },
      }),
      "Utenza societa",
      ["PEC:", "Telefono:"],
    ],
  ])("shows n/d for missing %s contacts", async (_kind, detail, sectionTitle, labels) => {
    await renderLoaded();
    api.getUtenzeSubject.mockResolvedValue(detail);
    await openDetail();

    const section = (await screen.findByText(sectionTitle)).closest("section") as HTMLElement;
    for (const label of labels) {
      expect(within(section).getByText(label).parentElement).toHaveTextContent(`${label} n/d`);
    }
  });

  test("refreshes the drawer from the NAS documents action", async () => {
    await renderLoaded();
    api.getUtenzeSubject
      .mockResolvedValueOnce(personDetail())
      .mockResolvedValueOnce(personDetail({ documents: [documentFixture({ filename: "nuovo.pdf" })] }));
    api.importUtenzeSubjectFromNas.mockResolvedValue({
      subject_id: "subject-1",
      matched_folder_path: "/archive/R/Rossi_Mario",
      matched_folder_name: "Rossi_Mario",
      warning_count: 0,
      created_documents: 1,
      updated_documents: 0,
      imported_at: "2026-10-04T08:00:00Z",
    });
    await openDetail();
    await screen.findByText("Nessun documento associato a questo utente.");

    fireEvent.click(screen.getByRole("button", { name: "Aggiorna documenti" }));
    expect(await screen.findByText("nuovo.pdf")).toBeInTheDocument();
  });

  test.each([
    [new Error("Utente non trovato"), "Utente non trovato"],
    [42, "Errore caricamento utente"],
  ])("shows detail load errors (%s)", async (failure, message) => {
    await renderLoaded();
    api.getUtenzeSubject.mockRejectedValue(failure);
    await openDetail();
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.queryByText("Caricamento utente in corso.")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Scheda soggetto" })).not.toBeInTheDocument();
  });

  test("ignores a detail response that arrives after the drawer was closed", async () => {
    await renderLoaded();
    const lateSuccess = deferred<UtenzeSubjectDetail>();
    api.getUtenzeSubject.mockReturnValueOnce(lateSuccess.promise);
    await openDetail();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi dettaglio utente" }));
    await act(async () => lateSuccess.resolve(personDetail()));

    const lateFailure = deferred<UtenzeSubjectDetail>();
    api.getUtenzeSubject.mockReturnValueOnce(lateFailure.promise);
    await openDetail();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi dettaglio utente" }));
    await act(async () => lateFailure.reject(new Error("Risposta tardiva")));

    api.getUtenzeSubject.mockReturnValueOnce(new Promise(() => undefined));
    await openDetail();
    expect(screen.queryByRole("heading", { name: "Rossi Mario" })).not.toBeInTheDocument();
    expect(screen.queryByText("Risposta tardiva")).not.toBeInTheDocument();
    expect(screen.getByText("Caricamento utente in corso.")).toBeInTheDocument();
  });

  test("closes the drawer with Escape and ignores other keys", async () => {
    await renderLoaded();
    api.getUtenzeSubject.mockResolvedValue(personDetail());
    await openDetail();

    fireEvent.keyDown(window, { key: "Enter" });
    expect(screen.getByText("Vista rapida del registro")).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByText("Vista rapida del registro")).not.toBeInTheDocument();
  });
});

describe("UtenzeSubjectsSection document preview", () => {
  async function renderWithDocuments(documents: UtenzeDocument[]) {
    await renderLoaded();
    api.getUtenzeSubject.mockResolvedValue(personDetail({ documents }));
    await openDetail();
  }

  function previewRegion(): HTMLElement {
    return screen.getByText("Anteprima documento").closest("div.relative") as HTMLElement;
  }

  test("previews a PDF in an iframe and closes with the backdrop", async () => {
    await renderWithDocuments([documentFixture()]);
    const pendingBlob = deferred<Blob>();
    api.downloadUtenzeDocumentBlob.mockReturnValue(pendingBlob.promise);
    await openDocumentPreview("report.pdf");
    expect(screen.getByText("Caricamento anteprima...")).toBeInTheDocument();
    await act(async () => pendingBlob.resolve(new Blob(["%PDF"])));

    expect(await screen.findByTitle("report.pdf")).toHaveAttribute("src", "blob:preview-1");
    expect(api.downloadUtenzeDocumentBlob).toHaveBeenCalledWith("token", "doc-1");

    fireEvent.click(screen.getByRole("button", { name: "Chiudi anteprima documento" }));
    expect(screen.queryByText("Anteprima documento")).not.toBeInTheDocument();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:preview-1");
    expect(screen.getByText("Vista rapida del registro")).toBeInTheDocument();
  });

  test("previews an image and closes it with Escape before the drawer", async () => {
    await renderWithDocuments([documentFixture({ filename: "foto.JPG", extension: ".JPG", is_pdf: false })]);
    api.downloadUtenzeDocumentBlob.mockResolvedValue(new Blob(["img"]));
    await openDocumentPreview("foto.JPG");

    expect(await screen.findByRole("img", { name: "foto.JPG" })).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByText("Anteprima documento")).not.toBeInTheDocument();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:preview-1");
    expect(screen.getByText("Vista rapida del registro")).toBeInTheDocument();
  });

  test.each([
    ["<p>Contenuto lettera</p>", "Contenuto lettera"],
    ["", "Nessun contenuto leggibile disponibile per questo file DOCX."],
  ])("previews DOCX content (%s)", async (html, expected) => {
    await renderWithDocuments([documentFixture({ filename: "lettera.docx", extension: ".DOCX", is_pdf: false })]);
    api.downloadUtenzeDocumentBlob.mockResolvedValue(new Blob(["docx"]));
    api.convertToHtml.mockResolvedValue({ value: html, messages: [] });
    await openDocumentPreview("lettera.docx");

    expect(await screen.findByText(expected, undefined, DYNAMIC_IMPORT_WAIT)).toBeInTheDocument();
    expect(api.convertToHtml).toHaveBeenCalledWith({ arrayBuffer: expect.objectContaining({ byteLength: 4 }) });
  });

  test("previews the first three spreadsheet sheets with empty cells and empty sheets", async () => {
    await renderWithDocuments([documentFixture({ filename: "ruolo.xlsx", extension: ".xlsx", is_pdf: false })]);
    const rows = Array.from({ length: 30 }, (_, index) => [`R${index + 1}`, index === 0 ? null : index]);
    api.downloadUtenzeDocumentBlob.mockResolvedValue(
      await xlsxBlob({ Dati: rows, Vuoto: [], Terzo: [["ok"]], Quarto: [["nascosto"]] }, (workbook) => {
        // A #NULL! error cell is returned by sheet_to_json as null even with a defval.
        const sheet = workbook.Sheets.Dati;
        sheet.C2 = { t: "e", v: 0 };
        sheet["!ref"] = "A1:C30";
      }),
    );
    await openDocumentPreview("ruolo.xlsx");

    const region = previewRegion();
    expect(await within(region).findByText("Dati", undefined, DYNAMIC_IMPORT_WAIT)).toBeInTheDocument();
    expect(within(region).getByText("R1")).toBeInTheDocument();
    const row2 = within(region).getByText("R2").closest("tr") as HTMLElement;
    expect(Array.from(row2.querySelectorAll("td"), (cell) => cell.textContent)).toEqual(["R2", "1", "—"]);
    const row1 = within(region).getByText("R1").closest("tr") as HTMLElement;
    expect(Array.from(row1.querySelectorAll("td"), (cell) => cell.textContent)).toEqual(["R1", "—", "—"]);
    expect(within(region).getByText("R25")).toBeInTheDocument();
    expect(within(region).queryByText("R26")).not.toBeInTheDocument();
    expect(within(region).getByText("Foglio senza celle valorizzate.")).toBeInTheDocument();
    expect(within(region).getByText("ok")).toBeInTheDocument();
    expect(within(region).queryByText("Quarto")).not.toBeInTheDocument();
  });

  test("reports spreadsheets without readable sheets", async () => {
    await renderWithDocuments([documentFixture({ filename: "vuoto.xls", extension: ".xls", is_pdf: false })]);
    api.downloadUtenzeDocumentBlob.mockResolvedValue(await xlsxBlobWithoutSheets());
    await openDocumentPreview("vuoto.xls");
    expect(
      await screen.findByText("Nessun dato tabellare leggibile disponibile per questo file.", undefined, DYNAMIC_IMPORT_WAIT),
    ).toBeInTheDocument();
  });

  test.each([
    ["riga uno\nriga due", "riga uno riga due"],
    ["", "File di testo vuoto."],
  ])("previews text files (%j)", async (content, expected) => {
    await renderWithDocuments([documentFixture({ filename: "note.txt", extension: ".TXT", is_pdf: false })]);
    api.downloadUtenzeDocumentBlob.mockResolvedValue(new Blob([content]));
    await openDocumentPreview("note.txt");
    expect(await screen.findByText((_, element) => element?.tagName === "PRE" && element.textContent?.replace(/\n/g, " ") === expected)).toBeInTheDocument();
  });

  test.each([
    [".zip", "archivio.zip"],
    [null, "senza-estensione"],
  ])("offers a download for unsupported formats (%s)", async (extension, filename) => {
    await renderWithDocuments([documentFixture({ filename, extension, is_pdf: false })]);
    api.downloadUtenzeDocumentBlob.mockResolvedValue(new Blob(["bin"]));
    await openDocumentPreview(filename);

    expect(await screen.findByText("Anteprima inline non disponibile per questo formato.")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "Scarica documento" });
    expect(link).toHaveAttribute("href", "blob:preview-1");
    expect(link).toHaveAttribute("download", filename);

    fireEvent.click(within(previewRegion()).getByRole("button", { name: "Chiudi" }));
    expect(screen.queryByText("Anteprima documento")).not.toBeInTheDocument();
  });

  test.each([
    [new Error("Documento non trovato"), "Documento non trovato"],
    ["boom", "Errore caricamento anteprima documento"],
  ])("shows preview errors and closes without revoking (%s)", async (failure, message) => {
    await renderWithDocuments([documentFixture()]);
    api.downloadUtenzeDocumentBlob.mockRejectedValue(failure);
    await openDocumentPreview("report.pdf");

    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.queryByTitle("report.pdf")).not.toBeInTheDocument();
    fireEvent.click(within(previewRegion()).getByRole("button", { name: "Chiudi" }));
    expect(screen.queryByText("Anteprima documento")).not.toBeInTheDocument();
    expect(revokeObjectURL).not.toHaveBeenCalled();
  });

  test("closes a failed preview with Escape without revoking", async () => {
    await renderWithDocuments([documentFixture()]);
    api.downloadUtenzeDocumentBlob.mockRejectedValue(new Error("Documento non trovato"));
    await openDocumentPreview("report.pdf");
    await screen.findByText("Documento non trovato");

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByText("Anteprima documento")).not.toBeInTheDocument();
    expect(revokeObjectURL).not.toHaveBeenCalled();
    expect(screen.getByText("Vista rapida del registro")).toBeInTheDocument();
  });

  test("rejects documents without an identifier", async () => {
    await renderWithDocuments([documentFixture({ id: "", filename: "orfano.pdf" })]);
    fireEvent.click(await screen.findByText("orfano.pdf"));
    expect(await screen.findByText("Il documento selezionato non ha un identificativo valido.")).toBeInTheDocument();
    expect(api.downloadUtenzeDocumentBlob).not.toHaveBeenCalled();
    expect(screen.queryByText("Anteprima documento")).not.toBeInTheDocument();
  });

  // The preview overlay has no focus trap: keyboard users can still activate the
  // drawer controls rendered behind it (document buttons and the drawer close button).
  test("switching to another document revokes the previous preview URL", async () => {
    await renderWithDocuments([
      documentFixture(),
      documentFixture({ id: "doc-2", filename: "secondo.pdf", nas_path: "/archive/R/Rossi_Mario/secondo.pdf" }),
    ]);
    api.downloadUtenzeDocumentBlob.mockResolvedValue(new Blob(["%PDF"]));
    await openDocumentPreview("report.pdf");
    await screen.findByTitle("report.pdf");

    fireEvent.click(within(detailDialogRegion()).getByText("secondo.pdf"));
    expect(await screen.findByTitle("secondo.pdf")).toHaveAttribute("src", "blob:preview-2");
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:preview-1");
  });

  test("closing the drawer behind a loaded preview also clears the preview", async () => {
    await renderWithDocuments([documentFixture()]);
    api.downloadUtenzeDocumentBlob.mockResolvedValue(new Blob(["%PDF"]));
    await openDocumentPreview("report.pdf");
    await screen.findByTitle("report.pdf");

    fireEvent.click(within(detailDialogRegion()).getByRole("button", { name: "Chiudi" }));
    expect(screen.queryByText("Vista rapida del registro")).not.toBeInTheDocument();
    expect(screen.queryByText("Anteprima documento")).not.toBeInTheDocument();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:preview-1");
  });

  test("closing the drawer behind a failed preview clears it without revoking", async () => {
    await renderWithDocuments([documentFixture()]);
    api.downloadUtenzeDocumentBlob.mockRejectedValue(new Error("Documento non trovato"));
    await openDocumentPreview("report.pdf");
    await screen.findByText("Documento non trovato");

    fireEvent.click(within(detailDialogRegion()).getByRole("button", { name: "Chiudi" }));
    expect(screen.queryByText("Anteprima documento")).not.toBeInTheDocument();
    expect(revokeObjectURL).not.toHaveBeenCalled();
  });
});

describe("UtenzeSubjectsSection history modal", () => {
  async function openHistory(entries: Promise<UtenzeAuditLog[]> | { failure: unknown }) {
    await renderLoaded();
    if (entries instanceof Promise) {
      api.getUtenzeSubjectAuditLog.mockReturnValue(entries);
    } else {
      api.getUtenzeSubjectAuditLog.mockRejectedValue(entries.failure);
    }
    fireEvent.click(screen.getByTitle("Visualizza storico modifiche"));
    await screen.findByText("Storico modifiche");
  }

  test("shows loading then the empty state without opening the drawer, and closes", async () => {
    const pending = deferred<UtenzeAuditLog[]>();
    await openHistory(pending.promise);
    expect(screen.getByText("Caricamento storico...")).toBeInTheDocument();
    expect(screen.queryByText("Vista rapida del registro")).not.toBeInTheDocument();
    expect(api.getUtenzeSubjectAuditLog).toHaveBeenCalledWith("token", "subject-1");
    expect(screen.getByRole("heading", { name: "Rossi Mario" })).toBeInTheDocument();

    await act(async () => pending.resolve([]));
    expect(await screen.findByText("Nessuna voce di storico disponibile per questo utente.")).toBeInTheDocument();
    expect(screen.queryByText("Caricamento storico...")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Chiudi storico" }));
    expect(screen.queryByText("Storico modifiche")).not.toBeInTheDocument();
  });

  test.each([
    [new Error("Storico non disponibile"), "Storico non disponibile"],
    [undefined, "Errore caricamento storico"],
  ])("shows history errors (%s)", async (failure, message) => {
    await openHistory({ failure });
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.queryByText("Nessuna voce di storico disponibile per questo utente.")).not.toBeInTheDocument();
  });

  test("renders xlsx diffs, xlsx creations, non-xlsx and unknown actions", async () => {
    const after = {
      cognome: "Rossi",
      nome: "Maria",
      email: null,
      telefono: "0783",
      cap: "09170",
      comune: "Cabras",
      note: "nuova",
      indirizzo: "Via Roma",
      nono_campo: "oltre il limite",
    };
    const before = { cognome: "Rossi", nome: "Mario", email: "old@example.test", cap: null, comune: "Oristano", note: "vecchia", indirizzo: "Via Roma", nono_campo: "x" };
    await openHistory(
      Promise.resolve([
        auditEntry({ id: "a1", action: "xlsx_import_updated", diff_json: { before, after } }),
        auditEntry({
          id: "a2",
          action: "xlsx_import_created",
          diff_json: { before: null, after: { cognome: "Bianchi", nome: "", email: null, telefono: 123, a: 1, b: 2, settimo: "fuori" } },
        }),
        auditEntry({ id: "a3", action: "xlsx_import_anomaly", diff_json: { before: { cognome: "X" }, after: null } }),
        auditEntry({ id: "a4", action: "csv_import_created", diff_json: null }),
        auditEntry({ id: "a5", action: "custom_action", diff_json: { before: { a: 1 }, after: { a: 2 } } }),
      ]),
    );

    const modal = screen.getByText("Storico modifiche").closest("div.relative") as HTMLElement;
    const updated = within(modal).getByText("Aggiornato da import Excel").closest("div.rounded-xl") as HTMLElement;
    expect(updated).toHaveClass("border-sky-100");
    const [prima, dopo] = [
      within(updated).getByText("Prima").parentElement as HTMLElement,
      within(updated).getByText("Dopo").parentElement as HTMLElement,
    ];
    expect(within(prima).getByText("nome:").parentElement).toHaveTextContent("nome: Mario");
    expect(within(prima).getByText("email:").parentElement).toHaveTextContent("email: old@example.test");
    expect(within(prima).getByText("telefono:").parentElement).toHaveTextContent("telefono: —");
    expect(within(prima).getByText("cap:").parentElement).toHaveTextContent("cap: —");
    expect(within(prima).queryByText("cognome:")).not.toBeInTheDocument();
    expect(within(prima).queryByText("indirizzo:")).not.toBeInTheDocument();
    expect(within(prima).queryByText("nono_campo:")).not.toBeInTheDocument();
    expect(within(dopo).getByText("nome:").parentElement).toHaveTextContent("nome: Maria");
    expect(within(dopo).getByText("email:").parentElement).toHaveTextContent("email: —");
    expect(within(dopo).getByText("note:").parentElement).toHaveTextContent("note: nuova");
    expect(within(dopo).queryByText("cognome:")).not.toBeInTheDocument();

    const created = within(modal).getByText("Creato da import Excel").closest("div.rounded-xl") as HTMLElement;
    expect(Array.from(created.querySelectorAll("span.mr-2"), (node) => node.textContent)).toEqual([
      "cognome: Bianchi",
      "telefono: 123",
      "a: 1",
      "b: 2",
    ]);
    expect(within(created).queryByText("Prima")).not.toBeInTheDocument();

    const anomaly = within(modal).getByText("Importato come anomalia").closest("div.rounded-xl") as HTMLElement;
    expect(within(anomaly).queryByText("Prima")).not.toBeInTheDocument();
    expect(anomaly.querySelectorAll("div.mt-2, div.mt-3")).toHaveLength(0);

    const csv = within(modal).getByText("Creato da import CSV").closest("div.rounded-xl") as HTMLElement;
    expect(csv).toHaveClass("border-gray-100");
    expect(within(csv).getByText("Creato da import CSV")).toHaveClass("bg-gray-100");

    const custom = within(modal).getByText("custom_action").closest("div.rounded-xl") as HTMLElement;
    expect(within(custom).queryByText("Prima")).not.toBeInTheDocument();

    fireEvent.click(within(modal).getByRole("button", { name: "Chiudi" }));
    expect(screen.queryByText("Storico modifiche")).not.toBeInTheDocument();
  });
});
