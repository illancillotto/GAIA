import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import * as XLSX from "xlsx";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";

const mocks = vi.hoisted(() => ({
  token: vi.fn(),
  credentials: vi.fn(),
  terreniJobs: vi.fn(),
  particelleJobs: vi.fn(),
  historyJobs: vi.fn(),
  incassJobs: vi.fn(),
  createTerreniJob: vi.fn(),
  authError: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", () => ({
  listCapacitasCredentials: mocks.credentials,
  listCapacitasTerreniJobs: mocks.terreniJobs,
  listCapacitasParticelleSyncJobs: mocks.particelleJobs,
  listCapacitasAnagraficaHistoryJobs: mocks.historyJobs,
  listCapacitasInCassSyncJobs: mocks.incassJobs,
  createCapacitasTerreniJob: mocks.createTerreniJob,
  isAuthError: mocks.authError,
}));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({
  ElaborazioneWorkspaceModal: () => null,
}));

function csvFile(contents: string, name = "terreni.csv"): File {
  const file = new File([contents], name, { type: "text/csv" });
  Object.defineProperty(file, "text", { value: vi.fn().mockResolvedValue(contents) });
  return file;
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<Value>((fulfill, fail) => {
    resolve = fulfill;
    reject = fail;
  });
  return { promise, resolve, reject };
}

async function mountTerreni() {
  const view = render(<ElaborazioniCapacitasWorkspace embedded initialSection="terreni" />);
  await waitFor(() => expect(screen.getByText("Nessun job registrato")).toBeInTheDocument());
  return view;
}

function chooseFile(file: File | null) {
  fireEvent.change(screen.getByLabelText("File batch"), { target: { files: file ? [file] : [] } });
}

async function upload(contents = "comune,foglio,particella\nUras,1,680") {
  chooseFile(csvFile(contents));
  await waitFor(() => expect(screen.getByRole("button", { name: "Avvia job batch" })).toBeEnabled());
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.token.mockReturnValue("session-token");
  mocks.credentials.mockResolvedValue([]);
  mocks.terreniJobs.mockResolvedValue([]);
  mocks.particelleJobs.mockResolvedValue([]);
  mocks.historyJobs.mockResolvedValue([]);
  mocks.incassJobs.mockResolvedValue([]);
  mocks.authError.mockReturnValue(false);
  mocks.createTerreniJob.mockResolvedValue({ id: 91 });
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("Capacitas Terreni batch characterization", () => {
  test("loads each monitor once and cannot submit before valid input", async () => {
    await mountTerreni();
    expect(screen.getByRole("button", { name: "Avvia job batch" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Reset" })).toBeDisabled();
    expect(mocks.credentials).toHaveBeenCalledExactlyOnceWith("session-token");
    for (const list of [mocks.terreniJobs, mocks.particelleJobs, mocks.historyJobs]) {
      expect(list).toHaveBeenCalledExactlyOnceWith("session-token");
    }
    expect(mocks.incassJobs).toHaveBeenCalledExactlyOnceWith("session-token", { limit: 300 });
    expect(mocks.createTerreniJob).not.toHaveBeenCalled();
  });

  test("normalizes column aliases and trims values without altering row order", async () => {
    await mountTerreni();
    await upload(" Localita , Foglio , Mappale , Sezione , Subalterno\n Uras , 01 , 0680 , A , 3\nUras,14,1695,,");
    fireEvent.click(screen.getByRole("button", { name: "Avvia job batch" }));
    await waitFor(() => expect(mocks.createTerreniJob).toHaveBeenCalledExactlyOnceWith("session-token", {
      credential_id: undefined,
      continue_on_error: true,
      fetch_certificati: true,
      fetch_details: true,
      double_speed: false,
      parallel_workers: 1,
      throttle_ms: undefined,
      auto_resume: false,
      items: [
        { label: "Uras 01/0680/3", comune: "Uras", foglio: "01", particella: "0680", sezione: "A", sub: "3" },
        { label: "Uras 14/1695", comune: "Uras", foglio: "14", particella: "1695", sezione: "", sub: "" },
      ],
    }));
    expect(await screen.findByText("Job batch #91 creato con 2 righe in velocita standard e 1 worker.")).toBeInTheDocument();
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(2);
  });

  test("maps credential, batch flags and execution controls to the API", async () => {
    mocks.credentials.mockResolvedValue([{ id: 7, label: "Operatore", username: "user", active: true }]);
    await mountTerreni();
    await upload();
    expect(screen.getByLabelText("Credenziale")).toHaveValue("7");
    for (const label of ["Continua se una riga fallisce", "Scarica certificati", "Scarica dettagli terreno"]) {
      fireEvent.click(screen.getByLabelText(label));
    }
    fireEvent.click(screen.getByRole("button", { name: /Doppia velocita/ }));
    fireEvent.click(screen.getByRole("button", { name: /Parallelo x2/ }));
    fireEvent.click(screen.getByRole("button", { name: /Auto-resume/ }));
    fireEvent.change(screen.getByLabelText(/Pausa richieste \(ms\)/), { target: { value: "12a3" } });
    fireEvent.click(screen.getByRole("button", { name: "Avvia job batch" }));
    await waitFor(() => expect(mocks.createTerreniJob).toHaveBeenCalledWith("session-token", expect.objectContaining({
      credential_id: 7,
      continue_on_error: false,
      fetch_certificati: false,
      fetch_details: false,
      double_speed: true,
      parallel_workers: 2,
      throttle_ms: 123,
      auto_resume: true,
    })));
    expect(await screen.findByText(/Job batch #91 creato con 1 righe in doppia velocita e 2 worker · pausa 123ms · auto-resume attivo/)).toBeInTheDocument();
  });

  test("reads the first Excel worksheet and ignores later worksheets", async () => {
    await mountTerreni();
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet([{ comune: "Uras", foglio: "1", particella: "680" }]), "terreni");
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet([{ comune: "ignored", foglio: "2", particella: "3" }]), "other");
    const file = new File([], "Terreni.XLSX");
    Object.defineProperty(file, "arrayBuffer", {
      value: vi.fn().mockResolvedValue(XLSX.write(workbook, { bookType: "xlsx", type: "array" })),
    });
    chooseFile(file);
    await waitFor(() => expect(screen.getByRole("button", { name: "Avvia job batch" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Avvia job batch" }));
    await waitFor(() => expect(mocks.createTerreniJob).toHaveBeenCalledWith("session-token", expect.objectContaining({
      items: [{ label: "Uras 1/680", comune: "Uras", foglio: "1", particella: "680", sezione: "", sub: "" }],
    })));
  });

  test.each([
    ["other\nvalue", "Colonne minime mancanti. Richieste: comune, foglio, particella. Facoltative: sezione, sub."],
    ["comune,foglio,particella\nUras,,680", "Riga 2 non valida: servono comune, foglio e particella."],
    ["comune,foglio,particella", "File vuoto o senza righe valide per il batch Terreni."],
  ])("rejects invalid file %s, clears prior items and never submits", async (contents, message) => {
    await mountTerreni();
    await upload();
    chooseFile(csvFile(contents, "invalid.csv"));
    expect((await screen.findAllByText(message)).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Avvia job batch" })).toBeDisabled();
    expect(screen.getByText("Nessun file batch caricato")).toBeInTheDocument();
    expect(mocks.createTerreniJob).not.toHaveBeenCalled();
  });

  test.each([
    [new Error("Cannot read disk"), "Cannot read disk"],
    ["non-error rejection", "Errore parsing file Terreni"],
  ])("recovers from file read failure %s", async (failure, message) => {
    await mountTerreni();
    const file = csvFile("");
    vi.mocked(file.text).mockRejectedValue(failure);
    chooseFile(file);
    expect((await screen.findAllByText(message)).length).toBeGreaterThan(0);
    expect(screen.getByLabelText("File batch")).toBeEnabled();
    expect(screen.getByRole("button", { name: "Avvia job batch" })).toBeDisabled();
  });

  test("skips blank rows but preserves the original row number for invalid input", async () => {
    await mountTerreni();
    await upload("comune,foglio,particella,sezione\nUras,1,680,\n,,,only-section");
    expect(screen.getByText(/1 vuote saltate/)).toBeInTheDocument();
    chooseFile(csvFile("comune,foglio,particella,sezione\nUras,1,680,\n,,,only-section\nUras,,1695,"));
    expect((await screen.findAllByText("Riga 4 non valida: servono comune, foglio e particella.")).length).toBeGreaterThan(0);
    expect(screen.queryByText(/1 vuote saltate/)).not.toBeInTheDocument();
  });

  test("limits the preview to twenty rows but sends the complete batch", async () => {
    await mountTerreni();
    const rows = Array.from({ length: 21 }, (_, index) => `Uras,1,${index + 1}`);
    await upload(`comune,foglio,particella\n${rows.join("\n")}`);
    expect(screen.getByText("Uras 1/20")).toBeInTheDocument();
    expect(screen.queryByText("Uras 1/21")).not.toBeInTheDocument();
    expect(screen.getByText("Visualizzate 20 di 21 righe. Il job usera comunque tutto il file importato.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Avvia job batch" }));
    await waitFor(() => expect(mocks.createTerreniJob).toHaveBeenCalledTimes(1));
    expect(mocks.createTerreniJob.mock.calls[0][1].items).toHaveLength(21);
  });

  test.each(["reset", "clear"])("%s clears the file model without clearing execution preferences", async (action) => {
    await mountTerreni();
    await upload();
    fireEvent.click(screen.getByLabelText("Scarica dettagli terreno"));
    if (action === "reset") {
      fireEvent.click(screen.getByRole("button", { name: "Reset" }));
    } else {
      chooseFile(null);
    }
    expect(screen.getByText("Nessun file selezionato")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Avvia job batch" })).toBeDisabled();
    expect(screen.getByLabelText("Scarica dettagli terreno")).not.toBeChecked();
    await upload();
    fireEvent.click(screen.getByRole("button", { name: "Avvia job batch" }));
    await waitFor(() => expect(mocks.createTerreniJob).toHaveBeenCalledWith("session-token", expect.objectContaining({ fetch_details: false })));
  });

  test("keeps submit disabled through creation and the subsequent monitor refresh", async () => {
    const creation = deferred<{ id: number }>();
    const refresh = deferred<[]>();
    mocks.createTerreniJob.mockReturnValue(creation.promise);
    await mountTerreni();
    await upload();
    mocks.terreniJobs.mockReturnValueOnce(refresh.promise);
    fireEvent.click(screen.getByRole("button", { name: "Avvia job batch" }));
    expect(screen.getByRole("button", { name: "Avvio..." })).toBeDisabled();
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(1);
    await act(async () => creation.resolve({ id: 42 }));
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(2);
    expect(screen.getByRole("button", { name: "Avvio..." })).toBeDisabled();
    await act(async () => refresh.resolve([]));
    expect(screen.getByRole("button", { name: "Avvia job batch" })).toBeEnabled();
  });

  test.each([
    [new Error("permission denied"), "permission denied"],
    ["non-error rejection", "Errore avvio job batch Terreni"],
  ])("shows create failure %s, preserves rows and permits retry", async (failure, message) => {
    mocks.createTerreniJob.mockRejectedValueOnce(failure);
    await mountTerreni();
    await upload();
    fireEvent.click(screen.getByRole("button", { name: "Avvia job batch" }));
    expect((await screen.findAllByText(message)).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Avvia job batch" })).toBeEnabled();
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Avvia job batch" }));
    expect(await screen.findByText(/Job batch #91 creato/)).toBeInTheDocument();
    expect(screen.queryByText(message)).not.toBeInTheDocument();
    expect(mocks.createTerreniJob).toHaveBeenCalledTimes(2);
  });

  test("does not dispatch a validated batch if the GAIA token disappears", async () => {
    await mountTerreni();
    await upload();
    mocks.token.mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: "Avvia job batch" }));
    expect(mocks.createTerreniJob).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Avvia job batch" })).toBeEnabled();
  });

  test("preserves uploaded rows when changing sections while a file read is pending", async () => {
    const reading = deferred<string>();
    await mountTerreni();
    const file = csvFile("");
    vi.mocked(file.text).mockReturnValueOnce(reading.promise);
    chooseFile(file);
    expect(screen.getByLabelText("File batch")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Avvia job batch" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /^Sync particelle/ }));
    await act(async () => reading.resolve("comune,foglio,particella\nUras,1,680"));
    fireEvent.click(screen.getByRole("button", { name: /^Terreni batch/ }));
    expect(screen.getByRole("button", { name: "Avvia job batch" })).toBeEnabled();
    expect(screen.getByText("Uras 1/680")).toBeInTheDocument();
  });

  test("stops the Terreni monitor timer when unmounted", async () => {
    vi.useFakeTimers();
    mocks.terreniJobs.mockResolvedValue([{
      id: 1,
      status: "pending",
      payload_json: { items: [] },
      result_json: null,
      created_at: "2026-10-08T12:00:00Z",
      started_at: null,
      completed_at: null,
      error_detail: null,
    }]);
    const view = render(<ElaborazioniCapacitasWorkspace embedded initialSection="terreni" />);
    await act(async () => {});
    expect(screen.getByText("#1")).toBeInTheDocument();
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15000);
    });
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(2);
    view.unmount();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(45000);
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(2);
  });
});
