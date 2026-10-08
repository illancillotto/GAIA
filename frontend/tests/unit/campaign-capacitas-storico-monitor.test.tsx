import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import { ApiError } from "@/lib/api/core";
import type { CapacitasAnagraficaHistoryImportJob, CapacitasAnagraficaHistoryImportResult } from "@/types/api";

const mocks = vi.hoisted(() => ({
  token: vi.fn<() => string | null>(),
  credentials: vi.fn(),
  terreniJobs: vi.fn(),
  particelleJobs: vi.fn(),
  historyJobs: vi.fn<(token: string) => Promise<CapacitasAnagraficaHistoryImportJob[]>>(),
  incassJobs: vi.fn(),
  rerun: vi.fn<(token: string, id: number) => Promise<CapacitasAnagraficaHistoryImportJob>>(),
  remove: vi.fn<(token: string, id: number) => Promise<void>>(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", async () => {
  const actual = await import("@/lib/api/core");
  return {
    listCapacitasCredentials: mocks.credentials,
    listCapacitasTerreniJobs: mocks.terreniJobs,
    listCapacitasParticelleSyncJobs: mocks.particelleJobs,
    listCapacitasAnagraficaHistoryJobs: mocks.historyJobs,
    listCapacitasInCassSyncJobs: mocks.incassJobs,
    rerunCapacitasAnagraficaHistoryJob: mocks.rerun,
    deleteCapacitasAnagraficaHistoryJob: mocks.remove,
    isAuthError: actual.isAuthError,
  };
});
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({
  ElaborazioneWorkspaceModal: () => null,
}));

const EXPIRED = "Sessione GAIA scaduta: il monitor storico si ferma, ma i job backend gia avviati possono continuare.";

function result(overrides: Partial<CapacitasAnagraficaHistoryImportResult> = {}): CapacitasAnagraficaHistoryImportResult {
  return { processed: 2, imported: 1, skipped: 1, failed: 0, snapshot_records_imported: 3, items: [], ...overrides };
}

function job(overrides: Partial<CapacitasAnagraficaHistoryImportJob> = {}): CapacitasAnagraficaHistoryImportJob {
  return {
    id: 83, credential_id: null, requested_by_user_id: null, status: "succeeded", mode: "batch",
    payload_json: null, result_json: null, error_detail: null, started_at: null, completed_at: null,
    created_at: "2026-05-18T10:00:00Z", updated_at: "2026-05-18T10:00:00Z", ...overrides,
  };
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<Value>((fulfill, fail) => { resolve = fulfill; reject = fail; });
  return { promise, resolve, reject };
}

async function mount() {
  const view = render(<ElaborazioniCapacitasWorkspace embedded initialSection="storico" />);
  await act(async () => {});
  return view;
}

function jobCard(id = 83) {
  return screen.getByText(`Job #${id}`).parentElement!.parentElement!.parentElement!.parentElement!;
}

function reportPanel() {
  return screen.getByText("Report aggregato dell'ultima importazione storico anagrafico eseguita dal workspace Capacitas.").closest("article")!;
}

function inputPanel() {
  return screen.getByText("Import storico anagrafiche Capacitas").closest("article")!;
}

function refresh() {
  fireEvent.click(within(inputPanel()).getByRole("button", { name: "Aggiorna job" }));
}

async function tick(milliseconds = 15000) {
  await act(async () => { await vi.advanceTimersByTimeAsync(milliseconds); });
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.token.mockReturnValue("session-token");
  for (const list of [mocks.credentials, mocks.terreniJobs, mocks.particelleJobs, mocks.historyJobs, mocks.incassJobs]) list.mockResolvedValue([]);
  mocks.rerun.mockResolvedValue(job());
  mocks.remove.mockResolvedValue(undefined);
});

afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); });

describe("Capacitas Storico monitor, actions and results", () => {
  test("shows explicit initial loading then the empty monitor and report", async () => {
    const initial = deferred<CapacitasAnagraficaHistoryImportJob[]>();
    mocks.historyJobs.mockReturnValueOnce(initial.promise);
    await mount();
    expect(screen.getByText("Caricamento job storico...")).toBeInTheDocument();
    expect(within(inputPanel()).getByRole("button", { name: "Aggiorna job" })).toBeDisabled();
    await act(async () => initial.resolve([]));
    expect(screen.getByText("Nessun job storico registrato")).toBeInTheDocument();
    expect(within(reportPanel()).getByText("Nessun report disponibile")).toBeInTheDocument();
    expect(within(inputPanel()).getByRole("button", { name: "Aggiorna job" })).toBeEnabled();
    expect(mocks.historyJobs).toHaveBeenCalledExactlyOnceWith("session-token");
  });

  test("renders job order, resume details, dates and terminal errors while disabling deletion for active states", async () => {
    mocks.historyJobs.mockResolvedValue([
      job({ id: 4, status: "queued_resume" }), job({ id: 2, status: "processing" }), job({ id: 7, status: "pending" }),
      job({ id: 9, status: "failed", error_detail: "Remote history failed", started_at: "invalid-date", completed_at: "2026-05-18T11:00:00Z" }),
    ]);
    await mount();
    expect(screen.getAllByText(/^Job #/).map(element => element.textContent)).toEqual(["Job #4", "Job #2", "Job #7", "Job #9"]);
    expect(within(jobCard(4)).getByText("Resume automatico pianificato dopo restart backend.")).toBeInTheDocument();
    for (const id of [4, 2, 7]) expect(within(jobCard(id)).getByRole("button", { name: "Elimina" })).toBeDisabled();
    expect(within(jobCard(9)).getByRole("button", { name: "Elimina" })).toBeEnabled();
    expect(within(jobCard(9)).getByText("Remote history failed")).toBeInTheDocument();
    expect(within(jobCard(9)).getByText(/invalid-date/)).toBeInTheDocument();
    expect(within(jobCard(9)).getByText(new RegExp(new Date("2026-05-18T11:00:00Z").toLocaleString("it-IT").replace(/[.*+?^${}()|[\]\\]/g, "\\$&")))).toBeInTheDocument();
  });

  test.each(["pending", "processing", "queued_resume"])("polls %s until terminal and stops without replacing manual feedback on a silent tick", async status => {
    vi.useFakeTimers();
    mocks.historyJobs.mockResolvedValueOnce([job({ status })]).mockResolvedValue([job({ status: "succeeded", result_json: result() })]);
    await mount();
    await tick(14999);
    expect(mocks.historyJobs).toHaveBeenCalledTimes(1);
    await tick(1);
    expect(mocks.historyJobs).toHaveBeenCalledTimes(2);
    expect(within(reportPanel()).getByText("2 processati · 3 snapshot importati")).toBeInTheDocument();
    expect(screen.queryByText("Storico anagrafico aggiornato.")).not.toBeInTheDocument();
    await tick(45000);
    expect(mocks.historyJobs).toHaveBeenCalledTimes(2);
  });

  test("does not overlap pending ticks, skips hidden ticks and immediately refreshes when the document becomes visible", async () => {
    vi.useFakeTimers();
    let visibility: DocumentVisibilityState = "visible";
    vi.spyOn(document, "visibilityState", "get").mockImplementation(() => visibility);
    mocks.historyJobs.mockResolvedValue([job({ status: "processing" })]);
    await mount();
    visibility = "hidden";
    await tick(30000);
    expect(mocks.historyJobs).toHaveBeenCalledTimes(1);
    const pending = deferred<CapacitasAnagraficaHistoryImportJob[]>();
    mocks.historyJobs.mockReturnValueOnce(pending.promise);
    visibility = "visible";
    await act(async () => document.dispatchEvent(new Event("visibilitychange")));
    expect(mocks.historyJobs).toHaveBeenCalledTimes(2);
    await tick(45000);
    await act(async () => document.dispatchEvent(new Event("visibilitychange")));
    expect(mocks.historyJobs).toHaveBeenCalledTimes(2);
    await act(async () => pending.resolve([job({ status: "processing" })]));
    await tick();
    expect(mocks.historyJobs).toHaveBeenCalledTimes(3);
    expect(screen.queryByText("Caricamento job storico...")).not.toBeInTheDocument();
  });

  test("cancels timers and visibility refresh after unmount, including an already dispatched pending request", async () => {
    vi.useFakeTimers();
    vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
    mocks.historyJobs.mockResolvedValue([job({ status: "processing" })]);
    const view = await mount();
    const pending = deferred<CapacitasAnagraficaHistoryImportJob[]>();
    mocks.historyJobs.mockReturnValueOnce(pending.promise);
    await tick();
    expect(mocks.historyJobs).toHaveBeenCalledTimes(2);
    view.unmount();
    await act(async () => pending.resolve([job({ status: "succeeded", result_json: result() })]));
    await tick(60000);
    await act(async () => document.dispatchEvent(new Event("visibilitychange")));
    expect(mocks.historyJobs).toHaveBeenCalledTimes(2);
  });

  test("stops on missing initial token and resumes through a manual refresh after token restoration", async () => {
    vi.useFakeTimers();
    mocks.token.mockReturnValue(null);
    await mount();
    expect(within(inputPanel()).getByText(EXPIRED)).toBeInTheDocument();
    expect(mocks.historyJobs).not.toHaveBeenCalled();
    await tick(30000);
    expect(mocks.historyJobs).not.toHaveBeenCalled();
    mocks.token.mockReturnValue("restored-token");
    mocks.historyJobs.mockResolvedValue([job({ status: "pending" })]);
    await act(async () => refresh());
    expect(mocks.historyJobs).toHaveBeenCalledExactlyOnceWith("restored-token");
    expect(within(inputPanel()).queryByText(EXPIRED)).not.toBeInTheDocument();
    await tick();
    expect(mocks.historyJobs).toHaveBeenCalledTimes(2);
  });

  test("loses its token during polling without dispatching another API request and preserves backend job rows", async () => {
    vi.useFakeTimers();
    mocks.historyJobs.mockResolvedValue([job({ status: "processing" })]);
    await mount();
    mocks.token.mockReturnValue(null);
    await tick();
    expect(within(inputPanel()).getByText(EXPIRED)).toBeInTheDocument();
    expect(screen.getByText("Job #83")).toBeInTheDocument();
    expect(mocks.historyJobs).toHaveBeenCalledTimes(1);
    await tick(45000);
    expect(mocks.historyJobs).toHaveBeenCalledTimes(1);
    mocks.token.mockReturnValue("session-token");
    await act(async () => refresh());
    expect(within(inputPanel()).queryByText(EXPIRED)).not.toBeInTheDocument();
    expect(mocks.historyJobs).toHaveBeenCalledTimes(2);
  });

  test.each([401, 403])("stops an active monitor on authentic ApiError %s, preserving rows until explicit recovery", async status => {
    vi.useFakeTimers();
    mocks.historyJobs.mockResolvedValueOnce([job({ status: "processing" })]).mockRejectedValueOnce(new ApiError("auth rejection", null, status));
    await mount();
    await tick();
    expect(within(inputPanel()).getByText(EXPIRED)).toBeInTheDocument();
    expect(screen.queryByText("auth rejection")).not.toBeInTheDocument();
    expect(screen.getByText("Job #83")).toBeInTheDocument();
    await tick(45000);
    expect(mocks.historyJobs).toHaveBeenCalledTimes(2);
    mocks.historyJobs.mockResolvedValue([job({ status: "succeeded" })]);
    await act(async () => refresh());
    expect(within(inputPanel()).queryByText(EXPIRED)).not.toBeInTheDocument();
    expect(within(inputPanel()).getByText("Storico anagrafico aggiornato.")).toBeInTheDocument();
    expect(within(inputPanel()).getByRole("button", { name: "Aggiorna job" })).toBeEnabled();
  });

  test.each([
    [new Error("History service offline"), "History service offline"],
    ["unknown rejection", "Errore caricamento job storico anagrafico"],
  ])("displays an explicit refresh error %s but retains it through silent failures/success until manual refresh", async (failure, message) => {
    vi.useFakeTimers();
    mocks.historyJobs.mockResolvedValue([job({ status: "processing" })]);
    await mount();
    mocks.historyJobs.mockRejectedValueOnce(failure);
    await act(async () => refresh());
    expect(within(inputPanel()).getByText(message)).toBeInTheDocument();
    expect(within(inputPanel()).getByRole("button", { name: "Aggiorna job" })).toBeEnabled();
    mocks.historyJobs.mockRejectedValueOnce(new Error("silent rejection"));
    await tick();
    expect(within(inputPanel()).getByText(message)).toBeInTheDocument();
    expect(screen.queryByText("silent rejection")).not.toBeInTheDocument();
    await tick();
    expect(within(inputPanel()).getByText(message)).toBeInTheDocument();
    await act(async () => refresh());
    expect(within(inputPanel()).queryByText(message)).not.toBeInTheDocument();
    expect(mocks.historyJobs).toHaveBeenCalledTimes(5);
  });

  test("reruns only the selected ID and waits for the follow-up refresh before releasing its busy control", async () => {
    mocks.historyJobs.mockResolvedValueOnce([job(), job({ id: 84 })]);
    await mount();
    const rerun = deferred<CapacitasAnagraficaHistoryImportJob>();
    const listed = deferred<CapacitasAnagraficaHistoryImportJob[]>();
    mocks.rerun.mockReturnValueOnce(rerun.promise);
    mocks.historyJobs.mockReturnValueOnce(listed.promise);
    fireEvent.click(within(jobCard()).getByRole("button", { name: "Rilancia" }));
    expect(within(jobCard()).getByRole("button", { name: "Rerun..." })).toBeDisabled();
    expect(within(jobCard(84)).getByRole("button", { name: "Rilancia" })).toBeEnabled();
    expect(mocks.rerun).toHaveBeenCalledExactlyOnceWith("session-token", 83);
    expect(mocks.historyJobs).toHaveBeenCalledTimes(1);
    await act(async () => rerun.resolve(job({ status: "pending" })));
    expect(within(inputPanel()).getByText("Job storico #83 rilanciato.")).toBeInTheDocument();
    expect(screen.getByText("Caricamento job storico...")).toBeInTheDocument();
    expect(mocks.historyJobs).toHaveBeenCalledTimes(2);
    await act(async () => listed.resolve([job(), job({ id: 84 })]));
    expect(within(jobCard()).getByRole("button", { name: "Rilancia" })).toBeEnabled();
    expect(mocks.historyJobs).toHaveBeenLastCalledWith("session-token");
  });

  test.each([
    [new Error("Rerun refused"), "Rerun refused"],
    [{ failure: "rerun" }, "Errore rerun job storico anagrafico"],
  ])("retains rows and releases busy after rerun failure %s without refreshing", async (failure, message) => {
    mocks.historyJobs.mockResolvedValue([job()]);
    mocks.rerun.mockRejectedValueOnce(failure);
    await mount();
    fireEvent.click(within(jobCard()).getByRole("button", { name: "Rilancia" }));
    await within(inputPanel()).findByText(message);
    expect(within(jobCard()).getByRole("button", { name: "Rilancia" })).toBeEnabled();
    expect(mocks.historyJobs).toHaveBeenCalledTimes(1);
    expect(mocks.rerun).toHaveBeenCalledExactlyOnceWith("session-token", 83);
    fireEvent.click(within(jobCard()).getByRole("button", { name: "Rilancia" }));
    await within(inputPanel()).findByText("Job storico #83 rilanciato.");
    await waitFor(() => expect(screen.getByText("Job #83")).toBeInTheDocument());
    expect(within(inputPanel()).queryByText(message)).not.toBeInTheDocument();
  });

  test("removes only its selected terminal job after delete success without issuing a list refresh", async () => {
    mocks.historyJobs.mockResolvedValue([job(), job({ id: 84 })]);
    await mount();
    const removed = deferred<void>();
    mocks.remove.mockReturnValueOnce(removed.promise);
    fireEvent.click(within(jobCard()).getByRole("button", { name: "Elimina" }));
    expect(within(jobCard()).getByRole("button", { name: "Elimina..." })).toBeDisabled();
    expect(within(jobCard(84)).getByRole("button", { name: "Elimina" })).toBeEnabled();
    expect(mocks.remove).toHaveBeenCalledExactlyOnceWith("session-token", 83);
    await act(async () => removed.resolve());
    expect(screen.queryByText("Job #83")).not.toBeInTheDocument();
    expect(screen.getByText("Job #84")).toBeInTheDocument();
    expect(within(inputPanel()).getByText("Job storico #83 eliminato.")).toBeInTheDocument();
    expect(mocks.historyJobs).toHaveBeenCalledTimes(1);
  });

  test.each([
    [new Error("Delete refused"), "Delete refused"],
    ["unknown failure", "Errore eliminazione job storico anagrafico"],
  ])("retains a failed delete target on %s, releases busy and clears the error on a successful retry", async (failure, message) => {
    mocks.historyJobs.mockResolvedValue([job()]);
    mocks.remove.mockRejectedValueOnce(failure);
    await mount();
    fireEvent.click(within(jobCard()).getByRole("button", { name: "Elimina" }));
    await within(inputPanel()).findByText(message);
    expect(within(jobCard()).getByRole("button", { name: "Elimina" })).toBeEnabled();
    expect(mocks.historyJobs).toHaveBeenCalledTimes(1);
    fireEvent.click(within(jobCard()).getByRole("button", { name: "Elimina" }));
    await within(inputPanel()).findByText("Job storico #83 eliminato.");
    expect(screen.getByText("Nessun job storico registrato")).toBeInTheDocument();
    expect(within(inputPanel()).queryByText(message)).not.toBeInTheDocument();
    expect(mocks.remove).toHaveBeenNthCalledWith(2, "session-token", 83);
  });

  test.each(["rerun", "delete"])("does not dispatch %s after token loss and retains the selected row", async action => {
    mocks.historyJobs.mockResolvedValue([job()]);
    await mount();
    mocks.token.mockReturnValue(null);
    fireEvent.click(within(jobCard()).getByRole("button", { name: action === "rerun" ? "Rilancia" : "Elimina" }));
    expect(mocks.rerun).not.toHaveBeenCalled();
    expect(mocks.remove).not.toHaveBeenCalled();
    expect(mocks.historyJobs).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Job #83")).toBeInTheDocument();
    expect(within(jobCard()).getByRole("button", { name: action === "rerun" ? "Rilancia" : "Elimina" })).toBeEnabled();
  });

  test.each([
    [null], [[]], [{}],
    [{ ...result(), processed: "wrong" }], [{ ...result(), imported: "wrong" }],
    [{ ...result(), skipped: "wrong" }], [{ ...result(), failed: "wrong" }],
  ])("rejects allowed unknown result JSON %j without unsafe result rendering", async resultJson => {
    mocks.historyJobs.mockResolvedValue([job({ result_json: resultJson, error_detail: "Result not available" })]);
    await mount();
    expect(within(jobCard()).getByText("Result not available")).toBeInTheDocument();
    expect(within(reportPanel()).getByText("Nessun report disponibile")).toBeInTheDocument();
    expect(within(jobCard()).queryByText(/snapshot$/)).not.toBeInTheDocument();
  });

  test("renders result totals, item order/status styles, nullable identifiers and error-before-message precedence", async () => {
    mocks.historyJobs.mockResolvedValue([job({ result_json: result({
      processed: 4, imported: 1, skipped: 2, failed: 1, snapshot_records_imported: 9,
      items: [
        { subject_id: "subject-a", idxana: "idx-a", resolved_subject_id: "resolved-a", status: "imported", history_records_total: 4, imported_records: 3, skipped_records: 1, error: "error wins", message: "hidden message" },
        { subject_id: null, idxana: "idx-b", resolved_subject_id: null, status: "failed", history_records_total: 2, imported_records: 0, skipped_records: 0, message: "row failed" },
        { subject_id: "subject-c", status: "skipped", history_records_total: 0, imported_records: 0, skipped_records: 0 },
        { subject_id: "subject-d", status: "skipped", history_records_total: 0, imported_records: 0, skipped_records: 0, error: "", message: "also hidden" },
      ],
    }) })]);
    await mount();
    const panel = reportPanel();
    expect(within(panel).getByText("4 processati · 9 snapshot importati")).toBeInTheDocument();
    for (const [label, value] of [["Processed", 4], ["Imported", 1], ["Skipped", 2], ["Failed", 1], ["Snapshot", 9]] as const) {
      expect(within(within(panel).getByText(label).parentElement!).getByText(String(value))).toBeInTheDocument();
    }
    const rows = within(panel).getAllByRole("row").slice(1);
    expect(within(rows[0]).getByText("subject-a")).toBeInTheDocument();
    expect(within(rows[0]).getByText("idx-a")).toBeInTheDocument();
    expect(within(rows[0]).getByText("resolved-a")).toBeInTheDocument();
    expect(within(rows[0]).getByText("3/4 importati · 1 skipped")).toBeInTheDocument();
    expect(within(rows[0]).getByText("error wins")).toBeInTheDocument();
    expect(within(rows[0]).getByText("imported")).toHaveClass("bg-emerald-50");
    expect(within(rows[1]).getByText("idx-b")).toBeInTheDocument();
    expect(within(rows[1]).getAllByText("—")).toHaveLength(2);
    expect(within(rows[1]).getByText("failed")).toHaveClass("bg-rose-50");
    expect(within(rows[1]).getByText("row failed")).toBeInTheDocument();
    expect(within(rows[2]).getByText("skipped")).toHaveClass("bg-amber-50");
    expect(within(rows[2]).getAllByText("—")).toHaveLength(3);
    expect(within(rows[3]).getByText("subject-d")).toBeInTheDocument();
    expect(rows[3].lastElementChild).toHaveTextContent("");
    expect(within(panel).queryByText("hidden message")).not.toBeInTheDocument();
    expect(within(panel).queryByText("also hidden")).not.toBeInTheDocument();
  });

  test.each([
    [result({ processed: 1 }), { items: [{}, {}, {}] }, "33%"],
    [result({ processed: 4 }), { items: [{}] }, "100%"],
    [result({ processed: 0 }), { items: [] }, "0%"],
    [result(), null, "100%"],
    [{ ...result(), progress_percent: 42 }, { items: [{}] }, "42%"],
    [{ ...result(), progress_percent: 0 }, { items: "unknown" }, "0%"],
  ])("computes observable progress from result %j and payload %j", async (resultJson, payloadJson, percentage) => {
    mocks.historyJobs.mockResolvedValue([job({ result_json: resultJson, payload_json: payloadJson })]);
    await mount();
    expect(within(jobCard()).getByText(percentage)).toBeInTheDocument();
    expect(jobCard().querySelector('[style]')).toHaveStyle({ width: percentage });
  });

  test("selects the first valid terminal result in API order, then lets a valid first-job result override stored data", async () => {
    const stored = result({ processed: 5, snapshot_records_imported: 50 });
    const latest = result({ processed: 8, snapshot_records_imported: 80 });
    const replacement = result({ processed: 6, snapshot_records_imported: 60 });
    mocks.historyJobs.mockResolvedValueOnce([
      job({ id: 1, status: "processing", result_json: {} }),
      job({ id: 2, status: "succeeded", result_json: stored }),
      job({ id: 3, status: "failed", result_json: result({ processed: 7 }) }),
    ]);
    await mount();
    expect(within(reportPanel()).getByText("5 processati · 50 snapshot importati")).toBeInTheDocument();
    mocks.historyJobs.mockResolvedValueOnce([job({ id: 4, status: "processing", result_json: latest })]);
    refresh();
    await within(reportPanel()).findByText("8 processati · 80 snapshot importati");
    mocks.historyJobs.mockResolvedValueOnce([job({ id: 5, status: "processing", result_json: {} })]);
    refresh();
    await within(reportPanel()).findByText("5 processati · 50 snapshot importati");
    mocks.historyJobs.mockResolvedValueOnce([
      job({ id: 5, status: "processing", result_json: {} }), job({ id: 6, status: "completed_with_errors", result_json: replacement }),
    ]);
    refresh();
    await within(reportPanel()).findByText("6 processati · 60 snapshot importati");
    mocks.historyJobs.mockResolvedValueOnce([]);
    refresh();
    await screen.findByText("Nessun job storico registrato");
    expect(within(reportPanel()).getByText("6 processati · 60 snapshot importati")).toBeInTheDocument();
  });

  test("retains stored report after deleting its terminal job rather than clearing report state", async () => {
    mocks.historyJobs.mockResolvedValue([job({ result_json: result() })]);
    await mount();
    fireEvent.click(within(jobCard()).getByRole("button", { name: "Elimina" }));
    await screen.findByText("Nessun job storico registrato");
    expect(within(reportPanel()).getByText("2 processati · 3 snapshot importati")).toBeInTheDocument();
    expect(mocks.historyJobs).toHaveBeenCalledTimes(1);
  });
});
