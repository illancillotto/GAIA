import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import { ApiError } from "@/lib/api/core";
import type { CapacitasParticellaAnomalia, CapacitasResolveFragioneInput, CapacitasResolveFragioneResult } from "@/types/api";

const mocks = vi.hoisted(() => ({
  token: vi.fn<() => string | null>(),
  credentials: vi.fn(),
  terreniJobs: vi.fn(),
  particelleJobs: vi.fn(),
  historyJobs: vi.fn(),
  incassJobs: vi.fn(),
  anomalie: vi.fn<(token: string) => Promise<CapacitasParticellaAnomalia[]>>(),
  resolve: vi.fn<(token: string, id: string, payload: CapacitasResolveFragioneInput) => Promise<CapacitasResolveFragioneResult>>(),
  authError: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", () => ({
  listCapacitasCredentials: mocks.credentials,
  listCapacitasTerreniJobs: mocks.terreniJobs,
  listCapacitasParticelleSyncJobs: mocks.particelleJobs,
  listCapacitasAnagraficaHistoryJobs: mocks.historyJobs,
  listCapacitasInCassSyncJobs: mocks.incassJobs,
  listCapacitasParticelleAnomalie: mocks.anomalie,
  resolveCapacitasParticellaFrazione: mocks.resolve,
  isAuthError: mocks.authError,
}));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({
  ElaborazioneWorkspaceModal: () => null,
}));

function anomalia(overrides: Partial<CapacitasParticellaAnomalia> = {}): CapacitasParticellaAnomalia {
  return {
    id: "00000000-0000-4000-8000-000000000001",
    comune_id: "00000000-0000-4000-8000-000000000010",
    nome_comune: "Uras",
    foglio: "01",
    particella: "680",
    subalterno: null,
    anomaly_type: "multiple_fractions",
    candidates: [
      { frazione_id: "FRA-A", n_rows: 2, ccos: ["100", "200"], stati: ["attivo", "storico"] },
      { frazione_id: "FRA-B", n_rows: 1, ccos: [], stati: [] },
    ],
    capacitas_last_sync_at: null,
    capacitas_last_sync_error: null,
    ...overrides,
  };
}

function resolution(overrides: Partial<CapacitasResolveFragioneResult> = {}): CapacitasResolveFragioneResult {
  return { ok: true, total_rows: 2, imported_certificati: 1, error: null, ...overrides };
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

async function mountAnomalie() {
  const view = render(<ElaborazioniCapacitasWorkspace embedded initialSection="anomalie" />);
  await waitFor(() => expect(mocks.incassJobs).toHaveBeenCalledExactlyOnceWith("session-token", { limit: 300 }));
  expect(screen.getByText("Anomalie — frazioni ambigue")).toBeInTheDocument();
  return view;
}

async function loadAnomalie(rows = [anomalia()]) {
  mocks.anomalie.mockResolvedValueOnce(rows);
  fireEvent.click(screen.getByRole("button", { name: "Aggiorna lista" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Aggiorna lista" })).toBeEnabled());
  expect(mocks.anomalie).toHaveBeenLastCalledWith("session-token");
}

function openResolution(rowName = "Uras") {
  fireEvent.click(within(screen.getByRole("row", { name: new RegExp(rowName) })).getByRole("button", { name: "Risolvi" }));
  return screen.getByText("Risolvi frazione ambigua").parentElement!;
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.token.mockReturnValue("session-token");
  for (const list of [mocks.credentials, mocks.terreniJobs, mocks.particelleJobs, mocks.historyJobs, mocks.incassJobs]) {
    list.mockResolvedValue([]);
  }
  mocks.anomalie.mockResolvedValue([]);
  mocks.resolve.mockResolvedValue(resolution());
  mocks.authError.mockReturnValue(false);
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("Capacitas anomaly list and fraction resolution", () => {
  test("keeps anomaly loading manual and renders an empty response without a resolution action", async () => {
    await mountAnomalie();
    expect(mocks.anomalie).not.toHaveBeenCalled();
    expect(screen.getByText("Nessuna anomalia in coda")).toBeInTheDocument();
    expect(screen.getByText("Clicca Aggiorna lista per controllare.")).toBeInTheDocument();
    await loadAnomalie([]);
    expect(screen.getByText("Nessuna anomalia")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Risolvi" })).not.toBeInTheDocument();
    expect(mocks.resolve).not.toHaveBeenCalled();
  });

  test("renders a single anomaly with candidates and the first radio selected, retaining empty CCO/status fallbacks", async () => {
    await mountAnomalie();
    await loadAnomalie();
    expect(screen.getByText("1 particella con anomalia")).toBeInTheDocument();
    expect(screen.getByText("FRA-A (2 righe)")).toBeInTheDocument();
    expect(screen.getByText("FRA-B (1 righe)")).toBeInTheDocument();
    const dialog = openResolution();
    expect(within(dialog).getByText("Uras — foglio 01/680")).toBeInTheDocument();
    expect(within(dialog).getByText("2 righe · CCO: 100, 200 · stati: attivo, storico")).toBeInTheDocument();
    expect(within(dialog).getByText("1 righe · CCO: — · stati: —")).toBeInTheDocument();
    const radios = within(dialog).getAllByRole("radio");
    expect(radios[0]).toBeChecked();
    expect(radios[1]).not.toBeChecked();
    expect(within(dialog).getByRole("button", { name: "Sincronizza" })).toBeEnabled();
    fireEvent.click(within(dialog).getByRole("button", { name: "Chiudi" }));
    expect(screen.queryByText("Risolvi frazione ambigua")).not.toBeInTheDocument();
    expect(mocks.resolve).not.toHaveBeenCalled();
  });

  test("renders multiple rows in API order and preserves null names, optional subalterno and timestamp formatting", async () => {
    await mountAnomalie();
    const second = anomalia({
      id: "00000000-0000-4000-8000-000000000002", nome_comune: null, foglio: "14", particella: "1695", subalterno: "3",
      candidates: [], capacitas_last_sync_at: "invalid-date",
    });
    const dated = anomalia({
      id: "00000000-0000-4000-8000-000000000003", nome_comune: "Terralba", foglio: "2", particella: "5", subalterno: "",
      capacitas_last_sync_at: "2026-05-18T10:30:00Z",
    });
    await loadAnomalie([second, anomalia(), dated]);
    expect(screen.getByText("3 particellae con anomalia")).toBeInTheDocument();
    const rows = screen.getAllByRole("row").slice(1);
    expect(within(rows[0]).getByText("—")).toBeInTheDocument();
    expect(within(rows[0]).getByText("14/1695/3")).toBeInTheDocument();
    expect(within(rows[0]).getByText("invalid-date")).toBeInTheDocument();
    expect(within(rows[1]).getByText("01/680")).toBeInTheDocument();
    expect(within(rows[1]).getByText("—")).toBeInTheDocument();
    expect(within(rows[2]).getByText("2/5")).toBeInTheDocument();
    expect(within(rows[2]).getByText(new Date(dated.capacitas_last_sync_at!).toLocaleString("it-IT"))).toBeInTheDocument();
  });

  test("disables synchronization when a valid anomaly has no candidate choices", async () => {
    await mountAnomalie();
    await loadAnomalie([anomalia({ candidates: [] })]);
    const dialog = openResolution();
    expect(within(dialog).queryByRole("radio")).not.toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Sincronizza" })).toBeDisabled();
    fireEvent.click(within(dialog).getByRole("button", { name: "Sincronizza" }));
    expect(mocks.resolve).not.toHaveBeenCalled();
    fireEvent.click(within(dialog).getByRole("button", { name: "Chiudi" }));
    expect(screen.getByRole("button", { name: "Risolvi" })).toBeEnabled();
  });

  test("sends the chosen fraction and fetch flag and removes only the resolved anomaly", async () => {
    await mountAnomalie();
    const selected = anomalia();
    const other = anomalia({ id: "00000000-0000-4000-8000-000000000002", nome_comune: "Terralba" });
    await loadAnomalie([selected, other]);
    const dialog = openResolution();
    fireEvent.click(within(dialog).getAllByRole("radio")[1]);
    expect(within(dialog).getAllByRole("radio")[1]).toBeChecked();
    fireEvent.click(within(dialog).getByRole("button", { name: "Sincronizza" }));
    expect(await within(dialog).findByText("La particella è stata sincronizzata con la frazione selezionata.")).toBeInTheDocument();
    expect(mocks.resolve).toHaveBeenCalledExactlyOnceWith("session-token", selected.id, { frazione_id: "FRA-B", fetch_certificati: true });
    expect(screen.queryByRole("row", { name: /Uras/ })).not.toBeInTheDocument();
    expect(screen.getByRole("row", { name: /Terralba/ })).toBeInTheDocument();
    expect(screen.getByText("1 particella con anomalia")).toBeInTheDocument();
    expect(within(dialog).queryByRole("button", { name: "Sincronizza" })).not.toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Chiudi" })).toBeEnabled();
    expect(mocks.anomalie).toHaveBeenCalledTimes(1);
    fireEvent.click(within(dialog).getByRole("button", { name: "Chiudi" }));
    const nextDialog = openResolution("Terralba");
    expect(within(nextDialog).getAllByRole("radio")[0]).toBeChecked();
    expect(within(nextDialog).queryByText("Sincronizzato")).not.toBeInTheDocument();
  });

  test("returns to the empty queue after resolving its last anomaly", async () => {
    await mountAnomalie();
    await loadAnomalie();
    const dialog = openResolution();
    fireEvent.click(within(dialog).getByRole("button", { name: "Sincronizza" }));
    await within(dialog).findByText("Sincronizzato");
    expect(screen.getByText("Nessuna anomalia in coda")).toBeInTheDocument();
    expect(screen.getByText("Nessuna anomalia")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Risolvi" })).not.toBeInTheDocument();
  });

  test.each([
    ["Portale indisponibile", "Portale indisponibile"],
    [null, "Errore sync"],
    ["", null],
  ])("retains the anomaly on unsuccessful result with error=%s", async (error, message) => {
    mocks.resolve.mockResolvedValueOnce(resolution({ ok: false, error }));
    await mountAnomalie();
    await loadAnomalie();
    const dialog = openResolution();
    fireEvent.click(within(dialog).getByRole("button", { name: "Sincronizza" }));
    await waitFor(() => expect(within(dialog).getByRole("button", { name: "Sincronizza" })).toBeEnabled());
    expect(mocks.resolve).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("row", { name: /Uras/ })).toBeInTheDocument();
    expect(within(dialog).queryByText("Sincronizzato")).not.toBeInTheDocument();
    if (message) expect(within(dialog).getByText(message)).toBeInTheDocument();
    else expect(within(dialog).queryByText("Errore")).not.toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Chiudi" })).toBeEnabled();
    fireEvent.click(within(dialog).getByRole("button", { name: "Chiudi" }));
    const reopened = openResolution();
    expect(within(reopened).queryByText("Errore sync")).not.toBeInTheDocument();
    expect(within(reopened).queryByText("Portale indisponibile")).not.toBeInTheDocument();
  });

  test.each([
    [new Error("Errore del portale"), "Errore del portale"],
    ["unknown failure", "Errore"],
    [new ApiError("Credenziale scaduta", { detail: "expired" }, 401), "Credenziale scaduta"],
  ])("allows a retry after resolution rejection %s without removing a row", async (failure, message) => {
    mocks.resolve.mockRejectedValueOnce(failure).mockResolvedValueOnce(resolution());
    await mountAnomalie();
    await loadAnomalie();
    const dialog = openResolution();
    fireEvent.click(within(dialog).getByRole("button", { name: "Sincronizza" }));
    const errorTexts = await within(dialog).findAllByText(message);
    expect(errorTexts).toHaveLength(message === "Errore" ? 2 : 1);
    expect(screen.getByRole("row", { name: /Uras/ })).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Chiudi" })).toBeEnabled();
    expect(mocks.authError).not.toHaveBeenCalled();
    fireEvent.click(within(dialog).getAllByRole("radio")[1]);
    fireEvent.click(within(dialog).getByRole("button", { name: "Sincronizza" }));
    await within(dialog).findByText("Sincronizzato");
    expect(within(dialog).queryAllByText(message)).toHaveLength(0);
    expect(mocks.resolve).toHaveBeenNthCalledWith(2, "session-token", anomalia().id, { frazione_id: "FRA-B", fetch_certificati: true });
  });

  test.each([
    [new Error("Lista indisponibile"), "Lista indisponibile"],
    [{ reason: "network unavailable" }, "Errore caricamento anomalie"],
    [new ApiError("Accesso scaduto", null, 403), "Accesso scaduto"],
  ])("preserves loaded rows on list failure %s and clears error on the next request", async (failure, message) => {
    await mountAnomalie();
    await loadAnomalie();
    mocks.anomalie.mockRejectedValueOnce(failure);
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna lista" }));
    await screen.findByText(message);
    expect(screen.getByRole("row", { name: /Uras/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aggiorna lista" })).toBeEnabled();
    expect(mocks.authError).not.toHaveBeenCalled();
    const nextList = deferred<CapacitasParticellaAnomalia[]>();
    mocks.anomalie.mockReturnValueOnce(nextList.promise);
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna lista" }));
    expect(screen.queryByText(message)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Caricamento..." })).toBeDisabled();
    await act(async () => nextList.resolve([]));
    expect(screen.queryByRole("row", { name: /Uras/ })).not.toBeInTheDocument();
    expect(screen.getByText("Nessuna anomalia")).toBeInTheDocument();
  });

  test("does not issue a list request after token loss and resumes through a real refresh action", async () => {
    await mountAnomalie();
    mocks.token.mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna lista" }));
    expect(mocks.anomalie).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Aggiorna lista" })).toBeEnabled();
    expect(screen.queryByText("Errore caricamento anomalie")).not.toBeInTheDocument();
    mocks.token.mockReturnValue("session-token");
    await loadAnomalie();
    expect(screen.getByRole("row", { name: /Uras/ })).toBeInTheDocument();
  });

  test("leaves selection and dialog available when the token vanishes before resolution, then submits using the restored token", async () => {
    await mountAnomalie();
    await loadAnomalie();
    const dialog = openResolution();
    fireEvent.click(within(dialog).getAllByRole("radio")[1]);
    mocks.token.mockReturnValue(null);
    fireEvent.click(within(dialog).getByRole("button", { name: "Sincronizza" }));
    expect(mocks.resolve).not.toHaveBeenCalled();
    expect(within(dialog).getByRole("button", { name: "Sincronizza" })).toBeEnabled();
    expect(within(dialog).getByRole("button", { name: "Chiudi" })).toBeEnabled();
    expect(within(dialog).getAllByRole("radio")[1]).toBeChecked();
    mocks.token.mockReturnValue("restored-token");
    fireEvent.click(within(dialog).getByRole("button", { name: "Sincronizza" }));
    await within(dialog).findByText("Sincronizzato");
    expect(mocks.resolve).toHaveBeenCalledExactlyOnceWith("restored-token", anomalia().id, { frazione_id: "FRA-B", fetch_certificati: true });
  });

  test("disables duplicate refreshes during a deferred list request without replacing the previous rows early", async () => {
    await mountAnomalie();
    await loadAnomalie();
    const nextList = deferred<CapacitasParticellaAnomalia[]>();
    mocks.anomalie.mockReturnValueOnce(nextList.promise);
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna lista" }));
    const loading = screen.getByRole("button", { name: "Caricamento..." });
    expect(loading).toBeDisabled();
    fireEvent.click(loading);
    expect(mocks.anomalie).toHaveBeenCalledTimes(2);
    expect(screen.getByRole("row", { name: /Uras/ })).toBeInTheDocument();
    await act(async () => nextList.resolve([anomalia({ nome_comune: "Terralba" })]));
    expect(screen.queryByRole("row", { name: /Uras/ })).not.toBeInTheDocument();
    expect(screen.getByRole("row", { name: /Terralba/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aggiorna lista" })).toBeEnabled();
  });

  test("keeps busy-close disabled and the dispatched fraction stable when an enabled radio changes during a request", async () => {
    await mountAnomalie();
    await loadAnomalie();
    const pending = deferred<CapacitasResolveFragioneResult>();
    mocks.resolve.mockReturnValueOnce(pending.promise);
    const dialog = openResolution();
    fireEvent.click(within(dialog).getByRole("button", { name: "Sincronizza" }));
    const close = within(dialog).getByRole("button", { name: "Chiudi" });
    const busy = within(dialog).getByRole("button", { name: "Sincronizzazione..." });
    expect(close).toBeDisabled();
    expect(busy).toBeDisabled();
    fireEvent.click(close);
    fireEvent.click(busy);
    expect(screen.getByText("Risolvi frazione ambigua")).toBeInTheDocument();
    expect(mocks.resolve).toHaveBeenCalledExactlyOnceWith("session-token", anomalia().id, { frazione_id: "FRA-A", fetch_certificati: true });
    const secondRadio = within(dialog).getAllByRole("radio")[1];
    expect(secondRadio).toBeEnabled();
    fireEvent.click(secondRadio);
    expect(secondRadio).toBeChecked();
    await act(async () => pending.resolve(resolution({ ok: false, error: "Riprova" })));
    expect(within(dialog).getByText("Riprova")).toBeInTheDocument();
    expect(close).toBeEnabled();
    expect(secondRadio).toBeChecked();
    fireEvent.click(within(dialog).getByRole("button", { name: "Sincronizza" }));
    await within(dialog).findByText("Sincronizzato");
    expect(mocks.resolve).toHaveBeenNthCalledWith(2, "session-token", anomalia().id, { frazione_id: "FRA-B", fetch_certificati: true });
  });

  test("allows closing only after a deferred rejection and resets selection and error when reopened", async () => {
    await mountAnomalie();
    await loadAnomalie();
    const pending = deferred<CapacitasResolveFragioneResult>();
    mocks.resolve.mockReturnValueOnce(pending.promise);
    const dialog = openResolution();
    fireEvent.click(within(dialog).getAllByRole("radio")[1]);
    fireEvent.click(within(dialog).getByRole("button", { name: "Sincronizza" }));
    expect(within(dialog).getByRole("button", { name: "Chiudi" })).toBeDisabled();
    await act(async () => pending.reject(new Error("Timeout Capacitas")));
    expect(within(dialog).getByText("Timeout Capacitas")).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Chiudi" }));
    const reopened = openResolution();
    expect(within(reopened).getAllByRole("radio")[0]).toBeChecked();
    expect(within(reopened).queryByText("Timeout Capacitas")).not.toBeInTheDocument();
    expect(within(reopened).getByRole("button", { name: "Sincronizza" })).toBeEnabled();
  });
});
