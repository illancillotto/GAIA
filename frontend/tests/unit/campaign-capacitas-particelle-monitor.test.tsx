import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import type { CapacitasParticelleSyncJob, CapacitasParticelleSyncJobResult } from "@/types/api";

const mocks = vi.hoisted(() => ({ token: vi.fn(), credentials: vi.fn(), terreni: vi.fn(), particelle: vi.fn(), history: vi.fn(), incass: vi.fn(), authError: vi.fn() }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", () => ({
  listCapacitasCredentials: mocks.credentials,
  listCapacitasTerreniJobs: mocks.terreni,
  listCapacitasParticelleSyncJobs: mocks.particelle,
  listCapacitasAnagraficaHistoryJobs: mocks.history,
  listCapacitasInCassSyncJobs: mocks.incass,
  isAuthError: mocks.authError,
}));
vi.mock("@/components/app/protected-page", () => ({ ProtectedPage: ({ children }: { children: ReactNode }) => <>{children}</> }));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({ ElaborazioneWorkspaceModal: () => null }));

function result(overrides: Partial<CapacitasParticelleSyncJobResult> = {}): CapacitasParticelleSyncJobResult {
  return {
    mode: "progressive", total_items: 10, processed_items: 2, success_items: 2,
    failed_items: 0, skipped_items: 0, progress_percent: 20, current_label: "Record corrente",
    throttle_ms: 900, aggressive_window: false, recheck_hours: 72,
    recent_items: [], ...overrides,
  };
}

function job(id = 31, overrides: Partial<CapacitasParticelleSyncJob> = {}): CapacitasParticelleSyncJob {
  return {
    id, credential_id: null, requested_by_user_id: null, status: "succeeded", mode: "progressive",
    payload_json: null, result_json: null, error_detail: null,
    started_at: null, completed_at: null, created_at: "2026-10-08T08:00:00Z", updated_at: "2026-10-08T08:00:00Z",
    ...overrides,
  };
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  const promise = new Promise<Value>((fulfill) => { resolve = fulfill; });
  return { promise, resolve };
}

async function mount(jobs: CapacitasParticelleSyncJob[], timers = false) {
  if (timers) vi.useFakeTimers();
  mocks.particelle.mockResolvedValue(jobs);
  const view = render(<ElaborazioniCapacitasWorkspace embedded initialSection="particelle" />);
  await act(async () => {});
  expect(mocks.particelle).toHaveBeenCalledExactlyOnceWith("session-token");
  return view;
}

function refresh() { fireEvent.click(screen.getByRole("button", { name: "Aggiorna job" })); }
async function tick(delay = 15000) { await act(async () => vi.advanceTimersByTimeAsync(delay)); }
async function expectNotices(message: string) {
  const notices = await screen.findAllByText(message);
  expect(notices).toHaveLength(2);
  for (const notice of notices) expect(notice).toBeVisible();
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.token.mockReturnValue("session-token");
  for (const list of [mocks.credentials, mocks.terreni, mocks.particelle, mocks.history, mocks.incass]) list.mockResolvedValue([]);
  mocks.authError.mockReturnValue(false);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.useRealTimers(); });

describe("Capacitas Particelle monitor characterization", () => {
  test.each(["pending", "processing", "queued_resume"])("%s polls at 15s and stops after terminal response", async (status) => {
    await mount([job(31, { status })], true);
    mocks.particelle.mockResolvedValue([job(31)]);
    await tick(14999);
    expect(mocks.particelle).toHaveBeenCalledTimes(1);
    await tick(1);
    expect(mocks.particelle).toHaveBeenCalledTimes(2);
    expect(screen.getByText("Job #31")).toBeVisible();
    expect(screen.getByRole("button", { name: "Rilancia" })).toBeEnabled();
    expect(screen.queryByText("Sync progressiva particelle aggiornata.")).not.toBeInTheDocument();
    await tick(45000);
    expect(mocks.particelle).toHaveBeenCalledTimes(2);
  });

  test.each(["cancelling", "cancelled", "succeeded"])("%s does not enable automatic polling", async (status) => {
    await mount([job(31, { status })], true);
    await tick(45000);
    expect(mocks.particelle).toHaveBeenCalledTimes(1);
    if (status === "cancelling") expect(screen.getByRole("button", { name: "Fermando…" })).toBeDisabled();
    else expect(screen.getByRole("button", { name: "Rilancia" })).toBeEnabled();
  });

  test.each(["succeeded", "completed_with_errors", "failed"])("explicit refresh of active→%s sets completion notice", async (status) => {
    await mount([job(31, { status: "pending" })]);
    mocks.particelle.mockResolvedValue([job(31, { status })]);
    refresh();
    expect(await screen.findByText("Sync progressiva particelle aggiornata.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Rilancia" })).toBeEnabled();
  });

  test("explicit refresh of a different completed ID does not report tracked completion", async () => {
    await mount([job(31, { status: "pending" })]);
    mocks.particelle.mockResolvedValue([job(32)]);
    refresh();
    expect(await screen.findByText("Job #32")).toBeVisible();
    expect(screen.queryByText("Sync progressiva particelle aggiornata.")).not.toBeInTheDocument();
  });

  test.each([
    [new Error("List unavailable"), "List unavailable"],
    ["untyped failure", "Errore caricamento job particelle"],
  ])("initial list rejection preserves error until explicit recovery: %s", async (failure, message) => {
    mocks.particelle.mockRejectedValueOnce(failure);
    render(<ElaborazioniCapacitasWorkspace embedded initialSection="particelle" />);
    await expectNotices(message);
    expect(screen.getByRole("button", { name: "Aggiorna job" })).toBeEnabled();
    mocks.particelle.mockResolvedValue([job()]);
    refresh();
    expect(await screen.findByText("Job #31")).toBeVisible();
    expect(screen.queryByText(message)).not.toBeInTheDocument();
  });

  test("silent network failures preserve a manual error and existing active rows", async () => {
    await mount([job(31, { status: "processing" })], true);
    mocks.particelle.mockRejectedValue(new Error("Manual outage"));
    await act(async () => { refresh(); });
    expect(screen.getAllByText("Manual outage")).toHaveLength(2);
    await tick();
    expect(mocks.particelle).toHaveBeenCalledTimes(3);
    expect(screen.getAllByText("Manual outage")).toHaveLength(2);
    expect(screen.getByText("Job #31")).toBeVisible();
    mocks.particelle.mockResolvedValue([job(31, { status: "processing" })]);
    await tick();
    expect(screen.getAllByText("Manual outage")).toHaveLength(2);
    await act(async () => { refresh(); });
    expect(screen.queryByText("Manual outage")).not.toBeInTheDocument();
  });

  test.each([new Error("Expired session"), { status: 401 }])("auth failure stops polling until explicit recovery: %s", async (failure) => {
    await mount([job(31, { status: "processing" })], true);
    mocks.authError.mockImplementation((error) => error === failure);
    mocks.particelle.mockRejectedValueOnce(failure);
    await tick();
    expect(screen.getAllByText(/Sessione GAIA scaduta: il monitor particelle/)).toHaveLength(2);
    expect(screen.getByText("Rientra in GAIA per riprendere il polling della sync progressiva particelle.")).toBeVisible();
    await tick(45000);
    expect(mocks.particelle).toHaveBeenCalledTimes(2);
    mocks.particelle.mockResolvedValue([job(31, { status: "processing" })]);
    await act(async () => { refresh(); });
    expect(screen.queryByText(/Sessione GAIA scaduta: il monitor particelle/)).not.toBeInTheDocument();
    await tick();
    expect(mocks.particelle).toHaveBeenCalledTimes(4);
  });

  test("token missing at mount can recover by explicit refresh", async () => {
    mocks.token.mockReturnValue(null);
    render(<ElaborazioniCapacitasWorkspace embedded initialSection="particelle" />);
    expect((await screen.findAllByText(/Sessione GAIA scaduta: il monitor particelle/)).length).toBeGreaterThan(0);
    expect(mocks.particelle).not.toHaveBeenCalled();
    mocks.token.mockReturnValue("restored-token");
    mocks.particelle.mockResolvedValue([job()]);
    refresh();
    expect(await screen.findByText("Job #31")).toBeVisible();
    expect(mocks.particelle).toHaveBeenCalledExactlyOnceWith("restored-token");
    expect(screen.queryByText(/Sessione GAIA scaduta: il monitor particelle/)).not.toBeInTheDocument();
  });

  test("token disappearance stops polling without dispatching API and restoration re-enables it", async () => {
    await mount([job(31, { status: "pending" })], true);
    mocks.token.mockReturnValue(null);
    await tick();
    expect(mocks.particelle).toHaveBeenCalledTimes(1);
    expect(screen.getAllByText(/Sessione GAIA scaduta: il monitor particelle/)).toHaveLength(2);
    await tick(45000);
    expect(mocks.particelle).toHaveBeenCalledTimes(1);
    mocks.token.mockReturnValue("restored-token");
    await act(async () => { refresh(); });
    expect(mocks.particelle).toHaveBeenLastCalledWith("restored-token");
    await tick();
    expect(mocks.particelle).toHaveBeenCalledTimes(3);
  });

  test("hidden ticks skip; visibility refresh is single-flight and unmount removes polling/listener", async () => {
    const view = await mount([job(31, { status: "processing" })], true);
    const visibility = vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
    await tick();
    expect(mocks.particelle).toHaveBeenCalledTimes(1);
    const pending = deferred<CapacitasParticelleSyncJob[]>();
    mocks.particelle.mockReturnValueOnce(pending.promise);
    visibility.mockReturnValue("visible");
    await act(async () => document.dispatchEvent(new Event("visibilitychange")));
    expect(mocks.particelle).toHaveBeenCalledTimes(2);
    expect(screen.queryByText("Caricamento job particelle...")).not.toBeInTheDocument();
    await tick(45000);
    expect(mocks.particelle).toHaveBeenCalledTimes(2);
    await act(async () => { pending.resolve([job(31, { status: "processing" })]); });
    await tick();
    expect(mocks.particelle).toHaveBeenCalledTimes(3);
    view.unmount();
    await tick(45000);
    document.dispatchEvent(new Event("visibilitychange"));
    expect(mocks.particelle).toHaveBeenCalledTimes(3);
  });

  test.each([
    [null], [[]], [{}],
    [result({ total_items: "10" as unknown as number })],
    [result({ processed_items: "2" as unknown as number })],
    [result({ progress_percent: "20" as unknown as number })],
  ])("rejects unrecognized result shape %s without showing progress", async (resultJson) => {
    await mount([job(31, { result_json: resultJson, error_detail: "Job diagnostic" })]);
    expect(screen.getByText("Job diagnostic")).toBeVisible();
    expect(screen.queryByText("20%")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Rilancia" })).toBeEnabled();
  });

  test.each(["NOSessione scaduta", "SESSIONE SCADUTA", "ordinary diagnostic"])("portal session warning derives from failed recent item: %s", async (message) => {
    await mount([job(31, { status: "processing", result_json: result({
      recent_items: [{ particella_id: "parcel-1", label: "Parcel one", status: "failed", message }],
    }) })]);
    expect(screen.getByText("Parcel one")).toBeVisible();
    if (message === "ordinary diagnostic") expect(screen.queryByText("Sessione Capacitas scaduta")).not.toBeInTheDocument();
    else expect(screen.getByText("Sessione Capacitas scaduta")).toBeVisible();
    expect(mocks.authError).not.toHaveBeenCalled();
  });

  test("recent rows are reversed and limited to eight without mutating the response", async () => {
    const recent = Array.from({ length: 10 }, (_, index) => ({ particella_id: `parcel-${index}`, label: `Recent ${index}`, status: index === 9 ? "synced" : "skipped", message: "Processed" }));
    const snapshot = structuredClone(recent);
    await mount([job(31, { status: "processing", result_json: result({ recent_items: recent, aggressive_window: true, parallel_workers: 2, speed_multiplier: 2 }) })]);
    const table = screen.getByRole("table");
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(8);
    expect(within(rows[0]).getByText("Recent 9")).toBeVisible();
    expect(within(rows[7]).getByText("Recent 2")).toBeVisible();
    expect(screen.queryByText("Recent 1")).not.toBeInTheDocument();
    expect(recent).toEqual(snapshot);
    expect(screen.getByText("Fascia serale · 900ms · x2 · 2w")).toBeVisible();
  });
});
