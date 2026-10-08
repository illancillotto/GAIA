import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import * as XLSX from "xlsx";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import { ApiError } from "@/lib/api/core";
import type { CapacitasAnagraficaHistoryImportInput, CapacitasAnagraficaHistoryImportJob, CapacitasCredential } from "@/types/api";

const mocks = vi.hoisted(() => ({
  token: vi.fn<() => string | null>(),
  credentials: vi.fn<() => Promise<CapacitasCredential[]>>(),
  terreniJobs: vi.fn(),
  particelleJobs: vi.fn(),
  historyJobs: vi.fn<() => Promise<CapacitasAnagraficaHistoryImportJob[]>>(),
  incassJobs: vi.fn(),
  createHistory: vi.fn<(token: string, payload: CapacitasAnagraficaHistoryImportInput) => Promise<CapacitasAnagraficaHistoryImportJob>>(),
  authError: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", () => ({
  listCapacitasCredentials: mocks.credentials,
  listCapacitasTerreniJobs: mocks.terreniJobs,
  listCapacitasParticelleSyncJobs: mocks.particelleJobs,
  listCapacitasAnagraficaHistoryJobs: mocks.historyJobs,
  listCapacitasInCassSyncJobs: mocks.incassJobs,
  createCapacitasAnagraficaHistoryJob: mocks.createHistory,
  isAuthError: mocks.authError,
}));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({
  ElaborazioneWorkspaceModal: () => null,
}));

const SUBJECT_FIRST = "00000000-0000-4000-8000-000000000001";
const SUBJECT_SECOND = "00000000-0000-4000-8000-000000000002";
const IDXANA_FIRST = "48A9749E-96BF-4617-A019-046BF4CECA2B";
const IDXANA_SECOND = "48A9749E-96BF-4617-A019-046BF4CECA2C";

function job(): CapacitasAnagraficaHistoryImportJob {
  return {
    id: 83, credential_id: null, requested_by_user_id: null, status: "succeeded", mode: "batch",
    payload_json: null, result_json: null, error_detail: null, started_at: null, completed_at: null,
    created_at: "2026-05-18T10:00:00Z", updated_at: "2026-05-18T10:00:00Z",
  };
}

function credential(id: number): CapacitasCredential {
  return {
    id, label: `Account ${id}`, username: `user-${id}`, active: true, allowed_hours_start: 0, allowed_hours_end: 24,
    last_used_at: null, last_error: null, consecutive_failures: 0,
    created_at: "2026-05-18T10:00:00Z", updated_at: "2026-05-18T10:00:00Z",
  };
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<Value>((fulfill, fail) => { resolve = fulfill; reject = fail; });
  return { promise, resolve, reject };
}

function inputPanel() {
  return screen.getByText("Import storico anagrafiche Capacitas").closest("article")!;
}

async function mountStorico() {
  const view = render(<ElaborazioniCapacitasWorkspace embedded initialSection="storico" />);
  await waitFor(() => expect(mocks.historyJobs).toHaveBeenCalledExactlyOnceWith("session-token"));
  await waitFor(() => expect(within(inputPanel()).getByRole("button", { name: "Aggiorna job" })).toBeEnabled());
  return view;
}

function enterManual(subjects = SUBJECT_FIRST, idxana = "") {
  fireEvent.change(screen.getByLabelText("Lista subject_id"), { target: { value: subjects } });
  fireEvent.change(screen.getByLabelText("Lista IDXANA"), { target: { value: idxana } });
}

function csvFile(contents: string, name = "storico.csv") {
  const file = new File([contents], name, { type: "text/csv" });
  Object.defineProperty(file, "text", { value: vi.fn().mockResolvedValue(contents) });
  return file;
}

function workbookFile(rows: unknown[][], name = "storico.XLSX", laterRows?: unknown[][]) {
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(rows), "first");
  if (laterRows) XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(laterRows), "ignored");
  const file = new File([], name);
  Object.defineProperty(file, "arrayBuffer", {
    value: vi.fn().mockResolvedValue(XLSX.write(workbook, { type: "array", bookType: name.endsWith(".xls") ? "biff8" : "xlsx" })),
  });
  return file;
}

function chooseFile(file: File | null) {
  fireEvent.change(screen.getByLabelText("File batch"), { target: { files: file ? [file] : [] } });
}

async function upload(file = csvFile(`subject_id,idxana\n${SUBJECT_FIRST},\n,${IDXANA_FIRST}`), count = 2) {
  fireEvent.click(screen.getByRole("button", { name: "Batch da file" }));
  chooseFile(file);
  await screen.findByText(`File storico caricato: ${count} righe pronte per l'import.`);
  expect(screen.getByRole("button", { name: "Avvia import storico" })).toBeEnabled();
}

async function submit() {
  fireEvent.click(screen.getByRole("button", { name: "Avvia import storico" }));
  await waitFor(() => expect(mocks.createHistory).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(screen.getByRole("button", { name: "Avvia import storico" })).toBeEnabled());
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.token.mockReturnValue("session-token");
  for (const list of [mocks.credentials, mocks.terreniJobs, mocks.particelleJobs, mocks.historyJobs, mocks.incassJobs]) list.mockResolvedValue([]);
  mocks.createHistory.mockResolvedValue(job());
  mocks.authError.mockReturnValue(false);
});

afterEach(() => { cleanup(); vi.useRealTimers(); });

describe("Capacitas Storico input and submission characterization", () => {
  test("requires manual nonempty tokens and excludes delimiter-only input", async () => {
    await mountStorico();
    expect(screen.getByText("0 righe pronte")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Avvia import storico" })).toBeDisabled();
    enterManual(" , ; \t\n ", " ;,, \n");
    expect(screen.getByText("0 righe pronte")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Avvia import storico" }));
    expect(mocks.createHistory).not.toHaveBeenCalled();
    expect(mocks.historyJobs).toHaveBeenCalledTimes(1);
  });

  test("splits every manual delimiter, keeps duplicates and dispatches subjects before IDXANA with the default payload", async () => {
    await mountStorico();
    enterManual(` ${SUBJECT_SECOND},${SUBJECT_FIRST};${SUBJECT_SECOND}\t${SUBJECT_FIRST} ${SUBJECT_SECOND}\n${SUBJECT_FIRST} `,
      ` ${IDXANA_SECOND};${IDXANA_FIRST},${IDXANA_SECOND}\t${IDXANA_FIRST} ${IDXANA_SECOND}\n${IDXANA_FIRST} `);
    expect(screen.getByText("12 righe pronte")).toBeInTheDocument();
    await submit();
    expect(mocks.createHistory).toHaveBeenCalledExactlyOnceWith("session-token", {
      credential_id: undefined, continue_on_error: true, auto_resume: true,
      items: [
        ...[SUBJECT_SECOND, SUBJECT_FIRST, SUBJECT_SECOND, SUBJECT_FIRST, SUBJECT_SECOND, SUBJECT_FIRST].map(subject_id => ({ subject_id, idxana: null })),
        ...[IDXANA_SECOND, IDXANA_FIRST, IDXANA_SECOND, IDXANA_FIRST, IDXANA_SECOND, IDXANA_FIRST].map(idxana => ({ subject_id: null, idxana })),
      ],
    });
    expect(screen.getByText("Job storico #83 creato con 12 righe e avviato in background.")).toBeInTheDocument();
    expect(mocks.historyJobs).toHaveBeenCalledTimes(2);
    expect(screen.getByLabelText("Lista subject_id")).toHaveValue(` ${SUBJECT_SECOND},${SUBJECT_FIRST};${SUBJECT_SECOND}\t${SUBJECT_FIRST} ${SUBJECT_SECOND}\n${SUBJECT_FIRST} `);
  });

  test("selects numeric credentials and preserves continue-on-error false for IDXANA-only manual submissions", async () => {
    mocks.credentials.mockResolvedValue([credential(7), credential(9)]);
    await mountStorico();
    fireEvent.change(within(inputPanel()).getByLabelText("Credenziale"), { target: { value: "9" } });
    fireEvent.click(screen.getByLabelText("Continua se una riga fallisce"));
    enterManual("", `${IDXANA_SECOND}\n${IDXANA_FIRST}`);
    await submit();
    expect(mocks.createHistory).toHaveBeenCalledExactlyOnceWith("session-token", {
      credential_id: 9, continue_on_error: false, auto_resume: true,
      items: [{ subject_id: null, idxana: IDXANA_SECOND }, { subject_id: null, idxana: IDXANA_FIRST }],
    });
  });

  test("uses the single loaded credential automatically but allows the user to select the backend default", async () => {
    mocks.credentials.mockResolvedValue([credential(7)]);
    await mountStorico();
    expect(within(inputPanel()).getByLabelText("Credenziale")).toHaveValue("7");
    fireEvent.change(within(inputPanel()).getByLabelText("Credenziale"), { target: { value: "" } });
    enterManual();
    await submit();
    expect(mocks.createHistory).toHaveBeenCalledWith("session-token", expect.objectContaining({ credential_id: undefined }));
  });

  test.each([",", ";", "\t"])("parses real CSV delimiter %s with normalized headers and preserves row pairs/order", async delimiter => {
    await mountStorico();
    const contents = [
      [" SUBJECT ID ", " IDXANA ", "extra"].join(delimiter),
      [` ${SUBJECT_SECOND} `, ` ${IDXANA_SECOND} `, "a"].join(delimiter),
      ["", IDXANA_FIRST, "b"].join(delimiter),
      [SUBJECT_FIRST, "", "c"].join(delimiter),
    ].join("\n");
    await upload(csvFile(contents, "Storico.CSV"), 3);
    await submit();
    expect(mocks.createHistory).toHaveBeenCalledExactlyOnceWith("session-token", {
      credential_id: undefined, continue_on_error: true, auto_resume: true,
      items: [
        { subject_id: SUBJECT_SECOND, idxana: IDXANA_SECOND },
        { subject_id: null, idxana: IDXANA_FIRST },
        { subject_id: SUBJECT_FIRST, idxana: null },
      ],
    });
  });

  test.each(["subject_id", "idxana"])("accepts only the %s required column without inventing the other identifier", async column => {
    await mountStorico();
    const value = column === "subject_id" ? SUBJECT_FIRST : IDXANA_FIRST;
    await upload(csvFile(`${column}\n${value}`), 1);
    await submit();
    expect(mocks.createHistory).toHaveBeenCalledWith("session-token", expect.objectContaining({
      items: [{ subject_id: column === "subject_id" ? value : null, idxana: column === "idxana" ? value : null }],
    }));
  });

  test.each(["storico.XLSX", "storico.xls"])("reads actual %s workbook's first sheet, preserving cell formatting and ignoring later sheets", async filename => {
    await mountStorico();
    await upload(workbookFile([
      ["Subject-ID", "IDXANA", "extra"], [SUBJECT_SECOND, IDXANA_SECOND, "row"], [null, IDXANA_FIRST, "row"],
    ], filename, [["subject_id"], ["ignored-later-sheet"]]), 2);
    await submit();
    expect(mocks.createHistory).toHaveBeenCalledWith("session-token", expect.objectContaining({
      items: [{ subject_id: SUBJECT_SECOND, idxana: IDXANA_SECOND }, { subject_id: null, idxana: IDXANA_FIRST }],
    }));
  });

  test("skips whitespace-only required cells and blank rows without dropping valid later identifiers", async () => {
    await mountStorico();
    await upload(csvFile(`subject_id,idxana,extra\n${SUBJECT_FIRST},,valid\n  , \t ,ignored\n,,ignored\n,${IDXANA_SECOND},valid\n\n`), 2);
    expect(screen.getByText("2 righe pronte · 2 vuote saltate")).toBeInTheDocument();
    await submit();
    expect(mocks.createHistory).toHaveBeenCalledWith("session-token", expect.objectContaining({
      items: [{ subject_id: SUBJECT_FIRST, idxana: null }, { subject_id: null, idxana: IDXANA_SECOND }],
    }));
  });

  test.each([
    ["other,code\nanything,1", "Colonne minime mancanti. Richieste: subject_id e/o idxana."],
    ["subject_id,idxana", "File vuoto o senza righe valide per lo storico anagrafico."],
    ["subject_id,idxana,extra\n,,only-extra", "File vuoto o senza righe valide per lo storico anagrafico."],
  ])("rejects unusable CSV %s and clears prior parsed rows instead of submitting stale input", async (contents, message) => {
    await mountStorico();
    await upload();
    chooseFile(csvFile(contents, "invalid.csv"));
    expect(await within(inputPanel()).findByText(message)).toBeInTheDocument();
    expect(screen.getByText("0 righe pronte")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Avvia import storico" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Reset" })).toBeDisabled();
    expect(mocks.createHistory).not.toHaveBeenCalled();
  });

  test("rejects an actual empty first worksheet even when the second sheet has identifiers", async () => {
    await mountStorico();
    fireEvent.click(screen.getByRole("button", { name: "Batch da file" }));
    chooseFile(workbookFile([], "empty.xlsx", [["subject_id"], [SUBJECT_FIRST]]));
    expect(await within(inputPanel()).findByText("File vuoto o senza righe valide per lo storico anagrafico.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Avvia import storico" })).toBeDisabled();
    expect(mocks.createHistory).not.toHaveBeenCalled();
  });

  test.each([
    ["csv", new Error("Disk read failed"), "Disk read failed"],
    ["csv", "file rejection", "Errore parsing file storico anagrafico"],
    ["xlsx", new Error("Workbook read failed"), "Workbook read failed"],
    ["xlsx", { failure: "file read" }, "Errore parsing file storico anagrafico"],
  ])("restores file controls after %s I/O rejection %s and allows valid retry", async (extension, failure, message) => {
    await mountStorico();
    await upload();
    const file = extension === "csv" ? csvFile("") : workbookFile([["subject_id"], [SUBJECT_FIRST]]);
    vi.mocked(extension === "csv" ? file.text : file.arrayBuffer).mockRejectedValue(failure);
    chooseFile(file);
    await within(inputPanel()).findByText(message);
    expect(screen.getByLabelText("File batch")).toBeEnabled();
    expect(screen.getByRole("button", { name: "Avvia import storico" })).toBeDisabled();
    expect(screen.getByText("0 righe pronte")).toBeInTheDocument();
    await upload(csvFile(`idxana\n${IDXANA_FIRST}`), 1);
    expect(within(inputPanel()).queryByText(message)).not.toBeInTheDocument();
    await submit();
    expect(mocks.createHistory).toHaveBeenCalledWith("session-token", expect.objectContaining({ items: [{ subject_id: null, idxana: IDXANA_FIRST }] }));
  });

  test("preserves independent manual/file input on mode switches and resets file data without erasing manual identifiers", async () => {
    await mountStorico();
    enterManual(SUBJECT_SECOND, IDXANA_SECOND);
    await upload();
    fireEvent.click(screen.getByRole("button", { name: "Manuale" }));
    expect(screen.getByLabelText("Lista subject_id")).toHaveValue(SUBJECT_SECOND);
    expect(screen.getByLabelText("Lista IDXANA")).toHaveValue(IDXANA_SECOND);
    fireEvent.click(screen.getByRole("button", { name: "Batch da file" }));
    expect(screen.getByText("2 righe pronte")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Reset" }));
    expect(screen.getByText("Nessun file selezionato")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reset" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Avvia import storico" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Manuale" }));
    await submit();
    expect(mocks.createHistory).toHaveBeenCalledWith("session-token", expect.objectContaining({ items: [
      { subject_id: SUBJECT_SECOND, idxana: null }, { subject_id: null, idxana: IDXANA_SECOND },
    ] }));
  });

  test("clears file selection, rows, skipped counter and parse error through an actual empty file-input change", async () => {
    await mountStorico();
    await upload(csvFile(`subject_id,extra\n${SUBJECT_FIRST},valid\n,ignored`), 1);
    expect(screen.getByText("1 righe pronte · 1 vuote saltate")).toBeInTheDocument();
    chooseFile(csvFile("other\nwrong", "invalid.csv"));
    await within(inputPanel()).findByText("Colonne minime mancanti. Richieste: subject_id e/o idxana.");
    chooseFile(null);
    expect(screen.getByText("Nessun file selezionato")).toBeInTheDocument();
    expect(within(inputPanel()).queryByText("Colonne minime mancanti. Richieste: subject_id e/o idxana.")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Avvia import storico" })).toBeDisabled();
    expect(screen.queryByText(/vuote saltate/)).not.toBeInTheDocument();
  });

  test("keeps parsing busy controls disabled until a deferred real CSV read finishes", async () => {
    await mountStorico();
    fireEvent.click(screen.getByRole("button", { name: "Batch da file" }));
    const pending = deferred<string>();
    const file = csvFile("");
    vi.mocked(file.text).mockReturnValue(pending.promise);
    chooseFile(file);
    expect(screen.getByLabelText("File batch")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Reset" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Avvia import storico" })).toBeDisabled();
    await act(async () => pending.resolve(`subject_id\n${SUBJECT_FIRST}`));
    expect(screen.getByText("1 righe pronte")).toBeInTheDocument();
    expect(screen.getByLabelText("File batch")).toBeEnabled();
    expect(screen.getByRole("button", { name: "Reset" })).toBeEnabled();
    await submit();
    expect(mocks.createHistory).toHaveBeenCalledWith("session-token", expect.objectContaining({ items: [{ subject_id: SUBJECT_FIRST, idxana: null }] }));
  });

  test("captures the dispatched input and stays busy through create then refresh before allowing another import", async () => {
    await mountStorico();
    const created = deferred<CapacitasAnagraficaHistoryImportJob>();
    const refreshed = deferred<CapacitasAnagraficaHistoryImportJob[]>();
    mocks.createHistory.mockReturnValueOnce(created.promise);
    mocks.historyJobs.mockReturnValueOnce(refreshed.promise);
    enterManual();
    fireEvent.click(screen.getByRole("button", { name: "Avvia import storico" }));
    expect(screen.getByRole("button", { name: "Import in corso..." })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Import in corso..." }));
    expect(mocks.historyJobs).toHaveBeenCalledTimes(1);
    expect(mocks.createHistory).toHaveBeenCalledExactlyOnceWith("session-token", {
      credential_id: undefined, continue_on_error: true, auto_resume: true, items: [{ subject_id: SUBJECT_FIRST, idxana: null }],
    });
    enterManual(SUBJECT_SECOND);
    await act(async () => created.resolve(job()));
    expect(mocks.historyJobs).toHaveBeenCalledTimes(2);
    expect(screen.getByText("Job storico #83 creato con 1 righe e avviato in background.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Import in corso..." })).toBeDisabled();
    expect(screen.getByLabelText("Lista subject_id")).toHaveValue(SUBJECT_SECOND);
    await act(async () => refreshed.resolve([]));
    expect(screen.getByRole("button", { name: "Avvia import storico" })).toBeEnabled();
    expect(mocks.createHistory).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText("Lista subject_id")).toHaveValue(SUBJECT_SECOND);
  });

  test.each([
    [new Error("Create rejected"), "Create rejected"],
    ["unknown create failure", "Errore import storico anagrafico"],
    [new ApiError("Accesso negato", null, 401), "Accesso negato"],
  ])("retains prepared input after create rejection %s and permits retry", async (failure, message) => {
    await mountStorico();
    enterManual();
    mocks.createHistory.mockRejectedValueOnce(failure);
    fireEvent.click(screen.getByRole("button", { name: "Avvia import storico" }));
    await within(inputPanel()).findByText(message);
    expect(screen.getByRole("button", { name: "Avvia import storico" })).toBeEnabled();
    expect(screen.getByLabelText("Lista subject_id")).toHaveValue(SUBJECT_FIRST);
    expect(mocks.historyJobs).toHaveBeenCalledTimes(1);
    expect(mocks.authError).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Avvia import storico" }));
    await screen.findByText("Job storico #83 creato con 1 righe e avviato in background.");
    await waitFor(() => expect(screen.getByRole("button", { name: "Avvia import storico" })).toBeEnabled());
    expect(within(inputPanel()).queryByText(message)).not.toBeInTheDocument();
    expect(mocks.createHistory).toHaveBeenCalledTimes(2);
    expect(mocks.historyJobs).toHaveBeenCalledTimes(2);
  });

  test("releases import busy state when its post-create refresh fails while retaining successful-create feedback", async () => {
    await mountStorico();
    enterManual();
    mocks.historyJobs.mockRejectedValueOnce(new Error("Refresh unavailable"));
    await submit();
    expect(within(inputPanel()).getByText("Refresh unavailable")).toBeInTheDocument();
    expect(screen.getByText("Job storico #83 creato con 1 righe e avviato in background.")).toBeInTheDocument();
    expect(screen.getByLabelText("Lista subject_id")).toHaveValue(SUBJECT_FIRST);
    expect(mocks.createHistory).toHaveBeenCalledTimes(1);
  });

  test("does not create when the token disappears after preparing input and resumes with the restored token", async () => {
    await mountStorico();
    enterManual();
    mocks.token.mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: "Avvia import storico" }));
    expect(mocks.createHistory).not.toHaveBeenCalled();
    expect(mocks.historyJobs).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Avvia import storico" })).toBeEnabled();
    expect(screen.getByLabelText("Lista subject_id")).toHaveValue(SUBJECT_FIRST);
    mocks.token.mockReturnValue("restored-token");
    await submit();
    expect(mocks.createHistory).toHaveBeenCalledExactlyOnceWith("restored-token", {
      credential_id: undefined, continue_on_error: true, auto_resume: true, items: [{ subject_id: SUBJECT_FIRST, idxana: null }],
    });
    expect(mocks.historyJobs).toHaveBeenLastCalledWith("restored-token");
  });
});
