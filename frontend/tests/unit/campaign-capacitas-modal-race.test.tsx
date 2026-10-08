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

function anomaly(id: string, nomeComune: string, foglio: string, particella: string, frazioneId: string): CapacitasParticellaAnomalia {
  return {
    id,
    comune_id: "00000000-0000-4000-8000-000000000010",
    nome_comune: nomeComune,
    foglio,
    particella,
    subalterno: null,
    anomaly_type: "multiple_fractions",
    candidates: [{ frazione_id: frazioneId, n_rows: 2, ccos: ["100"], stati: ["attivo"] }],
    capacitas_last_sync_at: null,
    capacitas_last_sync_error: null,
  };
}

const original = anomaly("00000000-0000-4000-8000-000000000001", "Uras", "01", "680", "FRA-A");
const replacement = anomaly("00000000-0000-4000-8000-000000000002", "Terralba", "02", "700", "FRA-C");
type Outcome = "success" | "unsuccessful result" | "rejection";
const outcomes: Outcome[] = ["success", "unsuccessful result", "rejection"];

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<Value>((fulfill, fail) => {
    resolve = fulfill;
    reject = fail;
  });
  return { promise, resolve, reject };
}

async function startOriginalAndReplaceModal() {
  const pending = deferred<CapacitasResolveFragioneResult>();
  mocks.resolve.mockReturnValueOnce(pending.promise);
  render(<ElaborazioniCapacitasWorkspace embedded initialSection="anomalie" />);
  await waitFor(() => expect(mocks.incassJobs).toHaveBeenCalledExactlyOnceWith("session-token", { limit: 300 }));
  fireEvent.click(screen.getByRole("button", { name: "Aggiorna lista" }));
  await screen.findByRole("row", { name: /Uras/ });
  fireEvent.click(within(screen.getByRole("row", { name: /Uras/ })).getByRole("button", { name: "Risolvi" }));
  expect(screen.getByText("Uras — foglio 01/680")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Sincronizza" }));
  expect(screen.getByRole("button", { name: "Chiudi" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Sincronizzazione..." })).toBeDisabled();
  expect(mocks.resolve).toHaveBeenCalledExactlyOnceWith("session-token", original.id, { frazione_id: "FRA-A", fetch_certificati: true });
  const backgroundAction = within(screen.getByRole("row", { name: /Terralba/ })).getByRole("button", { name: "Risolvi" });
  expect(backgroundAction).toBeEnabled();
  backgroundAction.focus();
  expect(backgroundAction).toHaveFocus();
  fireEvent.click(backgroundAction);
  expect(screen.getByText("Terralba — foglio 02/700")).toBeInTheDocument();
  expect(screen.queryByText("Uras — foglio 01/680")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Chiudi" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "Sincronizza" })).toBeEnabled();
  expect(screen.getByRole("radio")).toHaveAttribute("value", "FRA-C");
  expect(screen.getByRole("radio")).toBeChecked();
  expect(mocks.resolve).toHaveBeenCalledTimes(1);
  return pending;
}

async function settleOriginal(pending: ReturnType<typeof deferred<CapacitasResolveFragioneResult>>, outcome: Outcome) {
  await act(async () => {
    if (outcome === "rejection") {
      pending.reject(new Error("Timeout Capacitas"));
    } else {
      pending.resolve({
        ok: outcome === "success",
        total_rows: outcome === "success" ? 2 : 0,
        imported_certificati: outcome === "success" ? 1 : 0,
        error: outcome === "success" ? null : "Portale indisponibile",
      });
    }
  });
}

function expectOriginalRowOutcome(outcome: Outcome) {
  if (outcome === "success") {
    expect(screen.queryByRole("row", { name: /Uras/ })).not.toBeInTheDocument();
    expect(screen.getByText("1 particella con anomalia")).toBeInTheDocument();
  } else {
    expect(screen.getByRole("row", { name: /Uras/ })).toBeInTheDocument();
    expect(screen.getByText("2 particellae con anomalia")).toBeInTheDocument();
  }
  expect(screen.getByRole("row", { name: /Terralba/ })).toBeInTheDocument();
  expect(mocks.resolve).toHaveBeenCalledExactlyOnceWith("session-token", original.id, { frazione_id: "FRA-A", fetch_certificati: true });
  expect(mocks.anomalie).toHaveBeenCalledExactlyOnceWith("session-token");
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.token.mockReturnValue("session-token");
  for (const list of [mocks.credentials, mocks.terreniJobs, mocks.particelleJobs, mocks.historyJobs, mocks.incassJobs]) {
    list.mockResolvedValue([]);
  }
  mocks.anomalie.mockResolvedValue([original, replacement]);
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("Capacitas late anomaly-resolution modal responses", () => {
  test.each(outcomes)("retains null after public replacement and close before late %s", async (outcome) => {
    const pending = await startOriginalAndReplaceModal();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    expect(screen.queryByText("Risolvi frazione ambigua")).not.toBeInTheDocument();
    await settleOriginal(pending, outcome);
    expect(screen.queryByText("Risolvi frazione ambigua")).not.toBeInTheDocument();
    expect(screen.queryByText("Sincronizzato")).not.toBeInTheDocument();
    expect(screen.queryByText("Portale indisponibile")).not.toBeInTheDocument();
    expect(screen.queryByText("Timeout Capacitas")).not.toBeInTheDocument();
    expectOriginalRowOutcome(outcome);
    fireEvent.click(within(screen.getByRole("row", { name: /Terralba/ })).getByRole("button", { name: "Risolvi" }));
    expect(screen.getByText("Terralba — foglio 02/700")).toBeInTheDocument();
    expect(screen.getByRole("radio")).toBeChecked();
    expect(screen.getByRole("button", { name: "Sincronizza" })).toBeEnabled();
    expect(screen.queryByText("Sincronizzato")).not.toBeInTheDocument();
    expect(screen.queryByText("Portale indisponibile")).not.toBeInTheDocument();
    expect(screen.queryByText("Timeout Capacitas")).not.toBeInTheDocument();
  });

  test.each(outcomes)("characterizes the existing replacement-modal update from late %s", async (outcome) => {
    const pending = await startOriginalAndReplaceModal();
    await settleOriginal(pending, outcome);
    expect(screen.getByText("Terralba — foglio 02/700")).toBeInTheDocument();
    expect(screen.getByRole("radio")).toHaveAttribute("value", "FRA-C");
    expect(screen.getByRole("radio")).toBeChecked();
    expect(screen.getByRole("button", { name: "Chiudi" })).toBeEnabled();
    if (outcome === "success") {
      expect(screen.getByText("La particella è stata sincronizzata con la frazione selezionata.")).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Sincronizza" })).not.toBeInTheDocument();
    } else {
      expect(screen.getByText(outcome === "rejection" ? "Timeout Capacitas" : "Portale indisponibile")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Sincronizza" })).toBeEnabled();
      expect(screen.queryByText("Sincronizzato")).not.toBeInTheDocument();
    }
    expectOriginalRowOutcome(outcome);
  });
});
