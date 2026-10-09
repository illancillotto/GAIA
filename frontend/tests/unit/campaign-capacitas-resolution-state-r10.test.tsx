import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
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
  isAuthError: () => false,
}));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({
  ElaborazioneWorkspaceModal: () => null,
}));

function anomaly(id: string, nomeComune: string, fractions: string[]): CapacitasParticellaAnomalia {
  return {
    id,
    comune_id: "00000000-0000-4000-8000-000000000010",
    nome_comune: nomeComune,
    foglio: "01",
    particella: "680",
    subalterno: null,
    anomaly_type: "multiple_fractions",
    candidates: fractions.map((frazione_id) => ({ frazione_id, n_rows: 2, ccos: ["100"], stati: ["attivo"] })),
    capacitas_last_sync_at: null,
    capacitas_last_sync_error: null,
  };
}

const original = anomaly("00000000-0000-4000-8000-000000000001", "Uras", ["FRA-A", "FRA-B"]);
const replacement = anomaly("00000000-0000-4000-8000-000000000002", "Terralba", ["FRA-C", "FRA-D"]);

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<Value>((fulfill, fail) => {
    resolve = fulfill;
    reject = fail;
  });
  return { promise, resolve, reject };
}

function modal() {
  const container = screen.getByText("Risolvi frazione ambigua").parentElement;
  if (!container) throw new Error("Missing rendered resolution modal");
  return within(container);
}

async function mountAnomalies() {
  render(<ElaborazioniCapacitasWorkspace embedded initialSection="anomalie" />);
  await waitFor(() => expect(mocks.incassJobs).toHaveBeenCalledExactlyOnceWith("session-token", { limit: 300 }));
  fireEvent.click(screen.getByRole("button", { name: "Aggiorna lista" }));
  await screen.findByRole("row", { name: /Uras/ });
}

function openRow(nomeComune: string) {
  const action = within(screen.getByRole("row", { name: new RegExp(nomeComune) })).getByRole("button", { name: "Risolvi" });
  expect(action).toBeEnabled();
  action.focus();
  expect(action).toHaveFocus();
  fireEvent.click(action);
  expect(modal().getByText(`${nomeComune} — foglio 01/680`)).toBeInTheDocument();
}

function selectFraction(fraction: string) {
  const radio = modal().getAllByRole("radio").find((element) => element.getAttribute("value") === fraction);
  if (!radio) throw new Error(`Missing rendered fraction ${fraction}`);
  expect(radio).toBeEnabled();
  fireEvent.click(radio);
  expect(radio).toBeChecked();
}

function expectSelection(fraction: string) {
  expect(modal().getAllByRole("radio").find((element) => element.getAttribute("value") === fraction)).toBeChecked();
}

function startSync() {
  fireEvent.click(modal().getByRole("button", { name: "Sincronizza" }));
  expect(modal().getByRole("button", { name: "Sincronizzazione..." })).toBeDisabled();
  expect(modal().getByRole("button", { name: "Chiudi" })).toBeDisabled();
}

function result(ok: boolean, error: string | null = null): CapacitasResolveFragioneResult {
  return { ok, total_rows: ok ? 2 : 0, imported_certificati: ok ? 1 : 0, error };
}

async function resolveRequest(pending: ReturnType<typeof deferred<CapacitasResolveFragioneResult>>, response: CapacitasResolveFragioneResult) {
  await act(async () => pending.resolve(response));
}

type Failure =
  | { name: string; kind: "response"; error: string | null; message: string | null }
  | { name: string; kind: "rejection"; rejection: unknown; message: string };

const failures: Failure[] = [
  { name: "provided response error", kind: "response", error: "Portale indisponibile", message: "Portale indisponibile" },
  { name: "null response error", kind: "response", error: null, message: "Errore sync" },
  { name: "empty response error", kind: "response", error: "", message: null },
  { name: "Error rejection", kind: "rejection", rejection: new Error("Timeout Capacitas"), message: "Timeout Capacitas" },
  { name: "non-Error rejection", kind: "rejection", rejection: "unknown failure", message: "Errore" },
];

async function failRequest(pending: ReturnType<typeof deferred<CapacitasResolveFragioneResult>>, failure: Failure) {
  await act(async () => {
    if (failure.kind === "response") pending.resolve(result(false, failure.error));
    else pending.reject(failure.rejection);
  });
}

function expectFailure(message: string | null) {
  if (message) expect(modal().getAllByText(message)).toHaveLength(message === "Errore" ? 2 : 1);
  else expect(modal().queryByText("Errore")).not.toBeInTheDocument();
}

async function startOverlappingRequests() {
  const first = deferred<CapacitasResolveFragioneResult>();
  const second = deferred<CapacitasResolveFragioneResult>();
  mocks.resolve.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
  await mountAnomalies();
  openRow("Uras");
  selectFraction("FRA-B");
  startSync();
  openRow("Terralba");
  selectFraction("FRA-D");
  startSync();
  selectFraction("FRA-C");
  expect(modal().getByRole("button", { name: "Chiudi" })).toBeDisabled();
  expect(mocks.resolve).toHaveBeenNthCalledWith(1, "session-token", original.id, { frazione_id: "FRA-B", fetch_certificati: true });
  expect(mocks.resolve).toHaveBeenNthCalledWith(2, "session-token", replacement.id, { frazione_id: "FRA-D", fetch_certificati: true });
  return { first, second };
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.token.mockReturnValue("session-token");
  for (const list of [mocks.credentials, mocks.terreniJobs, mocks.particelleJobs, mocks.historyJobs, mocks.incassJobs]) {
    list.mockResolvedValue([]);
  }
  mocks.anomalie.mockResolvedValue([original, replacement]);
});

afterEach(() => cleanup());

describe("R10 original nullable fraction-resolution state contracts", () => {
  test.each(failures.flatMap((failure) => [
    { failure, order: "success first" },
    { failure, order: "failure first" },
  ]))("retains current selection and both terminal fields for $failure.name, $order", async ({ failure, order }) => {
    const { first, second } = await startOverlappingRequests();
    if (order === "success first") {
      await resolveRequest(first, result(true));
      expect(modal().getByText("Sincronizzato")).toBeInTheDocument();
      expect(modal().getByRole("button", { name: "Chiudi" })).toBeEnabled();
      expect(screen.getByRole("row", { name: /Terralba/ })).toBeInTheDocument();
      expect(screen.queryByRole("row", { name: /Uras/ })).not.toBeInTheDocument();
      await failRequest(second, failure);
    } else {
      await failRequest(second, failure);
      expectFailure(failure.message);
      expect(modal().queryByText("Sincronizzato")).not.toBeInTheDocument();
      expect(modal().getByRole("button", { name: "Sincronizza" })).toBeEnabled();
      expect(modal().getByRole("button", { name: "Chiudi" })).toBeEnabled();
      expect(screen.getByRole("row", { name: /Uras/ })).toBeInTheDocument();
      expect(screen.getByRole("row", { name: /Terralba/ })).toBeInTheDocument();
      await resolveRequest(first, result(true));
    }
    expect(modal().getByText("Terralba — foglio 01/680")).toBeInTheDocument();
    expectSelection("FRA-C");
    expect(modal().getByText("Sincronizzato")).toBeInTheDocument();
    expectFailure(failure.message);
    expect(modal().getByRole("button", { name: "Chiudi" })).toBeEnabled();
    expect(modal().queryByRole("button", { name: "Sincronizza" })).not.toBeInTheDocument();
    expect(screen.queryByRole("row", { name: /Uras/ })).not.toBeInTheDocument();
    expect(screen.getByRole("row", { name: /Terralba/ })).toBeInTheDocument();
    selectFraction("FRA-D");
    expect(modal().getByText("Sincronizzato")).toBeInTheDocument();
    expectFailure(failure.message);
    expect(modal().queryByRole("button", { name: "Sincronizza" })).not.toBeInTheDocument();
    expect(mocks.resolve).toHaveBeenCalledTimes(2);
    expect(mocks.anomalie).toHaveBeenCalledExactlyOnceWith("session-token");
    fireEvent.click(modal().getByRole("button", { name: "Chiudi" }));
    openRow("Terralba");
    expectSelection("FRA-C");
    expect(modal().queryByText("Sincronizzato")).not.toBeInTheDocument();
    expect(modal().queryByText("Errore")).not.toBeInTheDocument();
    expect(modal().getByRole("button", { name: "Sincronizza" })).toBeEnabled();
  });

  test("keeps a selection's error through missing-token submit and clears it only when a real request starts", async () => {
    const pending = deferred<CapacitasResolveFragioneResult>();
    mocks.resolve.mockResolvedValueOnce(result(false, "Riprova")).mockReturnValueOnce(pending.promise);
    await mountAnomalies();
    openRow("Uras");
    fireEvent.click(modal().getByRole("button", { name: "Sincronizza" }));
    await modal().findByText("Riprova");
    selectFraction("FRA-B");
    expect(modal().getByText("Riprova")).toBeInTheDocument();
    mocks.token.mockReturnValue(null);
    fireEvent.click(modal().getByRole("button", { name: "Sincronizza" }));
    expectSelection("FRA-B");
    expect(modal().getByText("Riprova")).toBeInTheDocument();
    expect(modal().getByRole("button", { name: "Sincronizza" })).toBeEnabled();
    expect(modal().getByRole("button", { name: "Chiudi" })).toBeEnabled();
    expect(mocks.resolve).toHaveBeenCalledTimes(1);
    mocks.token.mockReturnValue("restored-token");
    startSync();
    expect(modal().queryByText("Riprova")).not.toBeInTheDocument();
    selectFraction("FRA-A");
    expect(modal().getByRole("button", { name: "Chiudi" })).toBeDisabled();
    expect(mocks.resolve).toHaveBeenNthCalledWith(2, "restored-token", original.id, { frazione_id: "FRA-B", fetch_certificati: true });
    await resolveRequest(pending, result(true));
    expectSelection("FRA-A");
    expect(modal().getByText("Sincronizzato")).toBeInTheDocument();
    expect(screen.queryByRole("row", { name: /Uras/ })).not.toBeInTheDocument();
    expect(screen.getByRole("row", { name: /Terralba/ })).toBeInTheDocument();
  });

  test("lets an older request update a freshly reopened replacement while retaining its new identity and selection", async () => {
    const { first, second } = await startOverlappingRequests();
    await resolveRequest(second, result(false, "Riprova Terralba"));
    expect(modal().getByRole("button", { name: "Chiudi" })).toBeEnabled();
    fireEvent.click(modal().getByRole("button", { name: "Chiudi" }));
    expect(screen.queryByText("Risolvi frazione ambigua")).not.toBeInTheDocument();
    openRow("Terralba");
    expectSelection("FRA-C");
    expect(modal().queryByText("Riprova Terralba")).not.toBeInTheDocument();
    expect(modal().queryByText("Sincronizzato")).not.toBeInTheDocument();
    selectFraction("FRA-D");
    await resolveRequest(first, result(true));
    expect(modal().getByText("Terralba — foglio 01/680")).toBeInTheDocument();
    expectSelection("FRA-D");
    expect(modal().getByText("Sincronizzato")).toBeInTheDocument();
    expect(modal().queryByText("Riprova Terralba")).not.toBeInTheDocument();
    expect(modal().queryByRole("button", { name: "Sincronizza" })).not.toBeInTheDocument();
    expect(screen.queryByRole("row", { name: /Uras/ })).not.toBeInTheDocument();
    expect(screen.getByRole("row", { name: /Terralba/ })).toBeInTheDocument();
    expect(mocks.resolve).toHaveBeenCalledTimes(2);
  });
});
