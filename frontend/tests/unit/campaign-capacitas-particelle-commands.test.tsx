import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import type { CapacitasParticelleSyncJob, CapacitasParticelleSyncJobResult } from "@/types/api";

const mocks = vi.hoisted(() => ({
  token: vi.fn(),
  credentials: vi.fn(),
  terreni: vi.fn(),
  particelle: vi.fn(),
  history: vi.fn(),
  incass: vi.fn(),
  create: vi.fn(),
  rerun: vi.fn(),
  remove: vi.fn(),
  speed: vi.fn(),
  stop: vi.fn(),
  authError: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", () => ({
  listCapacitasCredentials: mocks.credentials,
  listCapacitasTerreniJobs: mocks.terreni,
  listCapacitasParticelleSyncJobs: mocks.particelle,
  listCapacitasAnagraficaHistoryJobs: mocks.history,
  listCapacitasInCassSyncJobs: mocks.incass,
  createCapacitasParticelleSyncJob: mocks.create,
  rerunCapacitasParticelleSyncJob: mocks.rerun,
  deleteCapacitasParticelleSyncJob: mocks.remove,
  patchCapacitasParticelleSyncJobSpeed: mocks.speed,
  stopCapacitasParticelleSyncJob: mocks.stop,
  isAuthError: mocks.authError,
}));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({ ElaborazioneWorkspaceModal: () => null }));

function result(overrides: Partial<CapacitasParticelleSyncJobResult> = {}): CapacitasParticelleSyncJobResult {
  return {
    mode: "progressive",
    total_items: 10,
    processed_items: 2,
    success_items: 2,
    failed_items: 0,
    skipped_items: 0,
    progress_percent: 20,
    current_label: "Record corrente",
    throttle_ms: 900,
    aggressive_window: false,
    recheck_hours: 72,
    speed_multiplier: 1,
    parallel_workers: 1,
    recent_items: [],
    ...overrides,
  };
}

function job(id: number, overrides: Partial<CapacitasParticelleSyncJob> = {}): CapacitasParticelleSyncJob {
  return {
    id,
    credential_id: null,
    requested_by_user_id: null,
    status: "succeeded",
    mode: "progressive",
    payload_json: null,
    result_json: null,
    error_detail: null,
    started_at: "2026-10-08T08:00:00Z",
    completed_at: "2026-10-08T08:10:00Z",
    created_at: "2026-10-08T07:59:00Z",
    updated_at: "2026-10-08T08:10:00Z",
    ...overrides,
  };
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  const promise = new Promise<Value>((fulfill) => { resolve = fulfill; });
  return { promise, resolve };
}

function card(id: number): HTMLElement {
  const element = screen.getByText(`Job #${id}`).closest(".rounded-\\[24px\\], .rounded-\\[20px\\]");
  if (!(element instanceof HTMLElement)) throw new Error(`Missing public job card ${id}`);
  return element;
}

async function mount(jobs: CapacitasParticelleSyncJob[] = []) {
  mocks.particelle.mockResolvedValue(jobs);
  const view = render(<ElaborazioniCapacitasWorkspace embedded initialSection="particelle" />);
  if (jobs.length > 0) await screen.findByText(`Job #${jobs[0].id}`);
  else await screen.findByText("Nessun job particelle registrato");
  await waitFor(() => expect(mocks.credentials).toHaveBeenCalledOnce());
  return view;
}

const defaultPayload = {
  credential_id: undefined,
  only_due: true,
  limit: undefined,
  fetch_certificati: true,
  fetch_details: true,
  double_speed: false,
  parallel_workers: 1,
};

beforeEach(() => {
  vi.resetAllMocks();
  mocks.token.mockReturnValue("session-token");
  mocks.credentials.mockResolvedValue([]);
  mocks.terreni.mockResolvedValue([]);
  mocks.particelle.mockResolvedValue([]);
  mocks.history.mockResolvedValue([]);
  mocks.incass.mockResolvedValue([]);
  mocks.authError.mockReturnValue(false);
  mocks.create.mockResolvedValue(job(91, { status: "pending" }));
  mocks.rerun.mockResolvedValue(job(21, { status: "pending" }));
  mocks.remove.mockResolvedValue(undefined);
  mocks.speed.mockResolvedValue(job(31, { status: "processing", result_json: result({ speed_multiplier: 2 }) }));
  mocks.stop.mockResolvedValue(job(31, { status: "cancelling", result_json: result() }));
});

afterEach(() => { cleanup(); });

describe("Capacitas Particelle command characterization", () => {
  test("creates with default flags and refreshes only after the create response", async () => {
    await mount();
    const pending = deferred<CapacitasParticelleSyncJob>();
    mocks.create.mockReturnValue(pending.promise);
    mocks.particelle.mockResolvedValue([job(91, { status: "pending" })]);
    fireEvent.click(screen.getByRole("button", { name: "Avvia sync progressiva" }));
    expect(mocks.create).toHaveBeenCalledExactlyOnceWith("session-token", defaultPayload);
    expect(screen.getByRole("button", { name: "Avvio..." })).toBeDisabled();
    expect(mocks.particelle).toHaveBeenCalledTimes(1);
    await act(async () => { pending.resolve(job(91, { status: "pending" })); });
    expect(await screen.findByText("Job #91")).toBeVisible();
    expect(screen.getByText("Job progressivo particelle #91 creato in velocita standard con 1 worker e avviato in background.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Avvia sync progressiva" })).toBeEnabled();
    expect(mocks.particelle).toHaveBeenCalledTimes(2);
  });

  test("maps chosen credential, integer limit, flags, double speed and parallel workers", async () => {
    mocks.credentials.mockResolvedValue([{ id: 7, label: "Operatore", username: "user", active: true }]);
    await mount();
    await waitFor(() => expect(screen.getByLabelText("Credenziale")).toHaveValue("7"));
    fireEvent.change(screen.getByLabelText("Limite run"), { target: { value: " 12 " } });
    for (const label of ["Solo particelle dovute", "Scarica certificati", "Scarica dettagli"]) {
      fireEvent.click(screen.getByLabelText(label));
    }
    fireEvent.click(screen.getByRole("button", { name: /^Doppia velocita/ }));
    fireEvent.click(screen.getByRole("button", { name: /^Parallelo x2/ }));
    fireEvent.click(screen.getByRole("button", { name: "Avvia sync progressiva" }));
    await waitFor(() => expect(mocks.create).toHaveBeenCalledExactlyOnceWith("session-token", {
      credential_id: 7, only_due: false, limit: 12, fetch_certificati: false,
      fetch_details: false, double_speed: true, parallel_workers: 2,
    }));
    expect(await screen.findByText("Job progressivo particelle #91 creato in doppia velocita con 2 worker e avviato in background.")).toBeVisible();
  });

  test("returns to backend auto-selection and default execution after toggling controls twice", async () => {
    mocks.credentials.mockResolvedValue([{ id: 7, label: "Operatore", username: "user", active: true }]);
    await mount();
    await waitFor(() => expect(screen.getByLabelText("Credenziale")).toHaveValue("7"));
    fireEvent.change(screen.getByLabelText("Credenziale"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("Limite run"), { target: { value: "   " } });
    for (let repeat = 0; repeat < 2; repeat += 1) {
      fireEvent.click(screen.getByRole("button", { name: /^Doppia velocita/ }));
      fireEvent.click(screen.getByRole("button", { name: /^Parallelo x2/ }));
    }
    fireEvent.click(screen.getByRole("button", { name: "Avvia sync progressiva" }));
    await waitFor(() => expect(mocks.create).toHaveBeenCalledExactlyOnceWith("session-token", defaultPayload));
  });

  test("rerun keeps the selected row busy until its ordered refresh completes", async () => {
    await mount([job(21), job(22)]);
    const rerun = deferred<CapacitasParticelleSyncJob>();
    const refresh = deferred<CapacitasParticelleSyncJob[]>();
    mocks.rerun.mockReturnValue(rerun.promise);
    mocks.particelle.mockReturnValue(refresh.promise);
    fireEvent.click(within(card(21)).getByRole("button", { name: "Rilancia" }));
    expect(mocks.rerun).toHaveBeenCalledExactlyOnceWith("session-token", 21);
    expect(within(card(21)).getByRole("button", { name: "Rerun..." })).toBeDisabled();
    expect(within(card(22)).getByRole("button", { name: "Rilancia" })).toBeEnabled();
    expect(mocks.particelle).toHaveBeenCalledTimes(1);
    await act(async () => { rerun.resolve(job(21, { status: "pending" })); });
    expect(screen.getByText("Caricamento job particelle...")).toBeVisible();
    expect(mocks.particelle).toHaveBeenCalledTimes(2);
    await act(async () => { refresh.resolve([job(21), job(22)]); });
    expect(screen.getByText("Job particelle #21 rilanciato.")).toBeVisible();
    expect(within(card(21)).getByRole("button", { name: "Rilancia" })).toBeEnabled();
  });

  test("delete removes only its matching ID after success without another list request", async () => {
    await mount([job(21), job(22)]);
    const pending = deferred<void>();
    mocks.remove.mockReturnValue(pending.promise);
    fireEvent.click(within(card(21)).getByRole("button", { name: "Elimina" }));
    expect(mocks.remove).toHaveBeenCalledExactlyOnceWith("session-token", 21);
    expect(within(card(21)).getByRole("button", { name: "Elimina..." })).toBeDisabled();
    expect(within(card(22)).getByRole("button", { name: "Elimina" })).toBeEnabled();
    await act(async () => { pending.resolve(); });
    expect(screen.queryByText("Job #21")).not.toBeInTheDocument();
    expect(screen.getByText("Job #22")).toBeVisible();
    expect(screen.getByText("Job particelle #21 eliminato.")).toBeVisible();
    expect(mocks.particelle).toHaveBeenCalledTimes(1);
  });

  test.each([false, true])("speed %s maps the returned row by ID and leaves other rows untouched", async (doubleSpeed) => {
    await mount([job(31, { status: "processing", result_json: result() }), job(32, { status: "processing", result_json: result({ current_label: "Altro record" }) })]);
    const pending = deferred<CapacitasParticelleSyncJob>();
    mocks.speed.mockReturnValue(pending.promise);
    fireEvent.click(within(card(31)).getByRole("button", { name: doubleSpeed ? "Doppia velocità" : "Standard" }));
    expect(mocks.speed).toHaveBeenCalledExactlyOnceWith("session-token", 31, doubleSpeed);
    expect(within(card(31)).getByRole("button", { name: "..." })).toBeDisabled();
    expect(within(card(31)).getByRole("button", { name: "Standard" })).toBeDisabled();
    expect(within(card(32)).getByRole("button", { name: "Standard" })).toBeEnabled();
    await act(async () => { pending.resolve(job(31, { status: "processing", result_json: result({ current_label: "Risposta aggiornata", speed_multiplier: doubleSpeed ? 2 : 1 }) })); });
    expect(within(card(31)).getByText(/Risposta aggiornata/)).toBeVisible();
    expect(within(card(32)).getByText(/Altro record/)).toBeVisible();
    expect(within(card(31)).getByRole("button", { name: "Standard" })).toBeEnabled();
    expect(mocks.particelle).toHaveBeenCalledTimes(1);
  });

  test("stop transitions only its row to cancelling and disables repeated stop", async () => {
    await mount([job(31, { status: "processing", result_json: result() }), job(32, { status: "processing" })]);
    const pending = deferred<CapacitasParticelleSyncJob>();
    mocks.stop.mockReturnValue(pending.promise);
    fireEvent.click(within(card(31)).getByRole("button", { name: "Stop" }));
    expect(mocks.stop).toHaveBeenCalledExactlyOnceWith("session-token", 31);
    expect(within(card(31)).getByRole("button", { name: "Stop..." })).toBeDisabled();
    expect(within(card(32)).getByRole("button", { name: "Stop" })).toBeEnabled();
    await act(async () => { pending.resolve(job(31, { status: "cancelling", result_json: result() })); });
    expect(within(card(31)).getByRole("button", { name: "Fermando…" })).toBeDisabled();
    expect(within(card(32)).getByRole("button", { name: "Stop" })).toBeEnabled();
    expect(mocks.particelle).toHaveBeenCalledTimes(1);
  });

  const commands = [
    { command: "create", label: "Avvia sync progressiva", fallback: "Errore avvio job particelle" },
    { command: "rerun", label: "Rilancia", fallback: "Errore rerun job particelle" },
    { command: "remove", label: "Elimina", fallback: "Errore eliminazione job particelle" },
    { command: "speed", label: "Standard", fallback: "Errore cambio velocità job" },
    { command: "stop", label: "Stop", fallback: "Errore stop job" },
  ] as const;

  test.each(commands)("$command is a no-op if the session token disappears after mount", async ({ command, label }) => {
    await mount([job(21), job(31, { status: "processing", result_json: result() })]);
    mocks.token.mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: label }));
    expect(mocks[command]).not.toHaveBeenCalled();
    expect(mocks.particelle).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: label })).toBeEnabled();
    expect(screen.getByText("Job #21")).toBeVisible();
    expect(screen.getByText("Job #31")).toBeVisible();
  });

  for (const failureType of ["Error", "non-Error"] as const) {
    test.each(commands)(`$command retains rows and recovers busy state after ${failureType}`, async ({ command, label, fallback }) => {
      await mount([job(21), job(31, { status: "processing", result_json: result() })]);
      mocks[command].mockRejectedValue(failureType === "Error" ? new Error("Backend denied action") : "rejected");
      fireEvent.click(screen.getByRole("button", { name: label }));
      const notices = await screen.findAllByText(failureType === "Error" ? "Backend denied action" : fallback);
      expect(notices).toHaveLength(2);
      for (const notice of notices) expect(notice).toBeVisible();
      expect(screen.getByRole("button", { name: label })).toBeEnabled();
      expect(screen.getByText("Job #21")).toBeVisible();
      expect(screen.getByText("Job #31")).toBeVisible();
      expect(mocks.particelle).toHaveBeenCalledTimes(1);
    });
  }

  test("a successful create followed by list failure keeps create confirmation and shows refresh error", async () => {
    await mount();
    mocks.particelle.mockRejectedValue(new Error("Refresh unavailable"));
    fireEvent.click(screen.getByRole("button", { name: "Avvia sync progressiva" }));
    const notices = await screen.findAllByText("Refresh unavailable");
    expect(notices).toHaveLength(2);
    for (const notice of notices) expect(notice).toBeVisible();
    expect(screen.getByText("Job progressivo particelle #91 creato in velocita standard con 1 worker e avviato in background.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Avvia sync progressiva" })).toBeEnabled();
    expect(mocks.particelle).toHaveBeenCalledTimes(2);
  });
});
