import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import type { CapacitasInCassSyncItemResult, CapacitasInCassSyncJobListItem, CapacitasInCassSyncJobResult } from "@/types/api";

const mocks = vi.hoisted(() => ({
  token: vi.fn(), credentials: vi.fn(), terreniJobs: vi.fn(), particelleJobs: vi.fn(),
  historyJobs: vi.fn(), incassJobs: vi.fn(), authError: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", () => ({
  listCapacitasCredentials: mocks.credentials,
  listCapacitasTerreniJobs: mocks.terreniJobs,
  listCapacitasParticelleSyncJobs: mocks.particelleJobs,
  listCapacitasAnagraficaHistoryJobs: mocks.historyJobs,
  listCapacitasInCassSyncJobs: mocks.incassJobs,
  isAuthError: mocks.authError,
}));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({ ElaborazioneWorkspaceModal: () => null }));

const sessionError = "Sessione GAIA scaduta: il monitor avvisi si ferma, ma i job backend gia avviati possono continuare.";
const sessionGuidance = "Rientra in GAIA per riprendere il polling del monitor avvisi.";

function job(id: number, overrides: Partial<CapacitasInCassSyncJobListItem> = {}): CapacitasInCassSyncJobListItem {
  return {
    id, credential_id: null, requested_by_user_id: 1, status: "succeeded", mode: "batch",
    subject_count: null, result_json: null, error_detail: null,
    started_at: "2026-10-08T12:01:00Z", completed_at: "2026-10-08T12:02:00Z",
    created_at: "2026-10-08T12:00:00Z", updated_at: "2026-10-08T12:02:00Z", ...overrides,
  };
}

function activeJob(id = 11, status = "processing"): CapacitasInCassSyncJobListItem {
  return job(id, { status, completed_at: null, started_at: status === "pending" ? null : "2026-10-08T12:01:00Z" });
}

function queue(count: number): CapacitasInCassSyncJobListItem[] {
  return Array.from({ length: count }, (_, index) => index === 0 ? activeJob(1001) : job(1001 + index));
}

function item(id: number, overrides: Partial<CapacitasInCassSyncItemResult> = {}): CapacitasInCassSyncItemResult {
  return {
    subject_id: String(id), identifier: `CF-${id}`, display_name: `Soggetto ${id}`,
    status: "synced", notices_found: 1, notices_synced: 1, error: null, ...overrides,
  };
}

function result(overrides: Partial<CapacitasInCassSyncJobResult> = {}): CapacitasInCassSyncJobResult {
  return {
    items: [], processed_subjects: 0, failed_subjects: 0, notices_found: 0, notices_synced: 0,
    ...overrides,
  };
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  const promise = new Promise<Value>((fulfill) => { resolve = fulfill; });
  return { promise, resolve };
}

async function mountWorkspace() {
  const view = render(<ElaborazioniCapacitasWorkspace embedded initialSection="incass" />);
  await act(async () => {});
  return view;
}

async function advance(milliseconds: number) {
  await act(async () => { await vi.advanceTimersByTimeAsync(milliseconds); });
}

async function refresh() {
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Aggiorna job" })); });
}

function card(id: number) {
  const element = screen.getByText(`Job #${id}`).closest('div[class*="rounded-[24px]"]');
  expect(element).not.toBeNull();
  return within(element as HTMLElement);
}

function visibleIds() {
  return screen.getAllByText(/^Job #\d+$/).map((element) => element.textContent);
}

function expectStat(id: number, label: string, value: string, description?: string) {
  const element = card(id).getByText(label).parentElement;
  expect(element).not.toBeNull();
  const stat = within(element!);
  expect(stat.getByText(value, { exact: true })).toBeInTheDocument();
  if (description) expect(stat.getByText(description, { exact: true })).toBeInTheDocument();
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.useFakeTimers();
  vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
  mocks.token.mockReturnValue("session-token");
  for (const list of [mocks.credentials, mocks.terreniJobs, mocks.particelleJobs, mocks.historyJobs, mocks.incassJobs]) {
    list.mockResolvedValue([]);
  }
  mocks.authError.mockReturnValue(false);
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("Capacitas inCASS real monitor polling", () => {
  test("loads the empty list once with its real limit and does not start polling", async () => {
    await mountWorkspace();
    expect(mocks.incassJobs).toHaveBeenCalledExactlyOnceWith("session-token", { limit: 300 });
    expect(screen.getByText("Nessun job avvisi registrato")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aggiorna job" })).toBeEnabled();
    await advance(90000);
    document.dispatchEvent(new Event("visibilitychange"));
    expect(mocks.incassJobs).toHaveBeenCalledTimes(1);
  });

  test("shows initial loading and disables manual refresh until the first list resolves", async () => {
    const loading = deferred<CapacitasInCassSyncJobListItem[]>();
    mocks.incassJobs.mockReturnValueOnce(loading.promise).mockResolvedValue([activeJob()]);
    await mountWorkspace();
    expect(screen.getByText("Caricamento job avvisi...")).toBeInTheDocument();
    const button = screen.getByRole("button", { name: "Aggiorna job" });
    expect(button).toBeDisabled();
    fireEvent.click(button);
    await advance(20000);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(1);
    await act(async () => loading.resolve([activeJob()]));
    expect(screen.queryByText("Caricamento job avvisi...")).not.toBeInTheDocument();
    expect(screen.getByText("Job #11")).toBeInTheDocument();
    expect(button).toBeEnabled();
    await advance(19999);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(1);
    await advance(1);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
  });

  test.each([
    { status: "pending", label: "In attesa" },
    { status: "processing", label: "In corso" },
    { status: "queued_resume", label: "Ripresa pianificata" },
  ])("polls active $status rows and disables their deletion", async ({ status, label }) => {
    mocks.incassJobs.mockResolvedValue([activeJob(11, status)]);
    await mountWorkspace();
    expect(card(11).getByText(label)).toBeInTheDocument();
    expect(card(11).getByRole("button", { name: "Elimina" })).toBeDisabled();
    expect(card(11).getByRole("button", { name: "Rilancia" })).toBeEnabled();
    const resume = card(11).queryByText("Resume automatico pianificato dopo restart backend.");
    if (status === "queued_resume") expect(resume).toBeInTheDocument();
    else expect(resume).not.toBeInTheDocument();
    await advance(20000);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
    expect(mocks.incassJobs).toHaveBeenLastCalledWith("session-token", { limit: 300 });
    expect(screen.queryByText("Caricamento job avvisi...")).not.toBeInTheDocument();
  });

  test.each([
    { status: "succeeded", label: "Completato" },
    { status: "completed_with_errors", label: "Con errori" },
    { status: "failed", label: "Fallito" },
  ])("does not poll terminal $status rows", async ({ status, label }) => {
    mocks.incassJobs.mockResolvedValue([job(11, { status })]);
    await mountWorkspace();
    expect(card(11).getByText(label)).toBeInTheDocument();
    expect(card(11).getByRole("button", { name: "Elimina" })).toBeEnabled();
    await advance(90000);
    document.dispatchEvent(new Event("visibilitychange"));
    expect(mocks.incassJobs).toHaveBeenCalledTimes(1);
  });

  test.each([
    { count: 100, interval: 20000 },
    { count: 101, interval: 45000 },
  ])("polls exactly $count listed jobs every $interval milliseconds", async ({ count, interval }) => {
    mocks.incassJobs.mockResolvedValue(queue(count));
    await mountWorkspace();
    expect(screen.getByText(/^Mostrati/)).toHaveTextContent(`Mostrati 15 di ${count} job. Altri ${count - 15} sono nascosti.`);
    await advance(interval - 1);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(1);
    await advance(1);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
    await advance(interval - 1);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
    await advance(1);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(3);
  });

  test("reschedules the real interval when the list crosses 100 to 101 and back", async () => {
    mocks.incassJobs.mockResolvedValueOnce(queue(100)).mockResolvedValueOnce(queue(101)).mockResolvedValue(queue(100));
    await mountWorkspace();
    await advance(20000);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
    expect(screen.getByRole("button", { name: "Mostra tutti (101)" })).toBeInTheDocument();
    await advance(44999);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
    await advance(1);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(3);
    expect(screen.getByRole("button", { name: "Mostra tutti (100)" })).toBeInTheDocument();
    await advance(19999);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(3);
    await advance(1);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(4);
  });

  test("skips hidden-document ticks and immediately refreshes when visibility returns", async () => {
    const visibility = vi.spyOn(document, "visibilityState", "get");
    mocks.incassJobs.mockResolvedValue([activeJob()]);
    await mountWorkspace();
    visibility.mockReturnValue("hidden");
    document.dispatchEvent(new Event("visibilitychange"));
    await advance(60000);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(1);
    visibility.mockReturnValue("visible");
    await act(async () => document.dispatchEvent(new Event("visibilitychange")));
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
    expect(screen.getByText("Job #11")).toBeInTheDocument();
    await advance(20000);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(3);
  });

  test("keeps polling single-flight across slow ticks and visible-tab refetches", async () => {
    const slow = deferred<CapacitasInCassSyncJobListItem[]>();
    mocks.incassJobs.mockResolvedValueOnce([activeJob()]).mockReturnValueOnce(slow.promise).mockResolvedValue([activeJob()]);
    await mountWorkspace();
    await advance(20000);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
    expect(screen.queryByText("Caricamento job avvisi...")).not.toBeInTheDocument();
    expect(screen.getByText("Job #11")).toBeInTheDocument();
    await act(async () => document.dispatchEvent(new Event("visibilitychange")));
    await advance(40000);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
    await act(async () => slow.resolve([activeJob()]));
    await act(async () => document.dispatchEvent(new Event("visibilitychange")));
    expect(mocks.incassJobs).toHaveBeenCalledTimes(3);
  });

  test("removes timers and visibility listeners on unmount even with a request in flight", async () => {
    const slow = deferred<CapacitasInCassSyncJobListItem[]>();
    mocks.incassJobs.mockResolvedValueOnce([activeJob()]).mockReturnValueOnce(slow.promise).mockResolvedValue([activeJob()]);
    const view = await mountWorkspace();
    await advance(20000);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
    view.unmount();
    await advance(90000);
    document.dispatchEvent(new Event("visibilitychange"));
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
    await act(async () => slow.resolve([activeJob()]));
    await advance(90000);
    document.dispatchEvent(new Event("visibilitychange"));
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
    expect(screen.queryByText("Job #11")).not.toBeInTheDocument();
  });

  test("manual refresh is not part of polling single-flight and a late manual response replaces newer rows", async () => {
    const manual = deferred<CapacitasInCassSyncJobListItem[]>();
    const poll = deferred<CapacitasInCassSyncJobListItem[]>();
    mocks.incassJobs.mockResolvedValueOnce([activeJob()]).mockReturnValueOnce(manual.promise).mockReturnValueOnce(poll.promise).mockResolvedValue([activeJob()]);
    await mountWorkspace();
    await refresh();
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
    expect(screen.getByText("Caricamento job avvisi...")).toBeInTheDocument();
    await advance(20000);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(3);
    await act(async () => poll.resolve([job(11)]));
    expect(screen.getByText("Caricamento job avvisi...")).toBeInTheDocument();
    expect(screen.queryByText("Job #11")).not.toBeInTheDocument();
    await act(async () => manual.resolve([activeJob()]));
    expect(card(11).getByText("In corso")).toBeInTheDocument();
    expect(card(11).queryByText("Completato")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aggiorna job" })).toBeEnabled();
    await advance(20000);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(4);
  });

  test("a silent terminal transition updates rows without a completion message and stops polling", async () => {
    mocks.incassJobs.mockResolvedValueOnce([activeJob()]).mockResolvedValue([job(11)]);
    await mountWorkspace();
    await advance(20000);
    expect(card(11).getByText("Completato")).toBeInTheDocument();
    expect(screen.queryByText("Sync avvisi aggiornata.")).not.toBeInTheDocument();
    await advance(90000);
    document.dispatchEvent(new Event("visibilitychange"));
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
  });

  test.each(["succeeded", "completed_with_errors", "failed"])("a manual refresh announces the tracked job becoming %s", async (status) => {
    mocks.incassJobs.mockResolvedValueOnce([activeJob()]).mockResolvedValue([job(11, { status })]);
    await mountWorkspace();
    await refresh();
    expect(screen.getByText("Sync avvisi aggiornata.")).toBeInTheDocument();
    expect(card(11).getByRole("button", { name: "Elimina" })).toBeEnabled();
    await advance(90000);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
  });

  test("does not announce an unrelated terminal job as completion of a tracked active ID", async () => {
    mocks.incassJobs.mockResolvedValueOnce([activeJob(11)]).mockResolvedValue([job(12)]);
    await mountWorkspace();
    await refresh();
    expect(screen.queryByText("Job #11")).not.toBeInTheDocument();
    expect(screen.getByText("Job #12")).toBeInTheDocument();
    expect(screen.queryByText("Sync avvisi aggiornata.")).not.toBeInTheDocument();
  });
});

describe("Capacitas inCASS monitor error and session recovery", () => {
  test.each([
    { failure: new Error("Monitor unavailable"), message: "Monitor unavailable" },
    { failure: "unknown rejection", message: "Errore caricamento job avvisi" },
  ])("reports an initial list failure and recovers by manual refresh: $message", async ({ failure, message }) => {
    mocks.incassJobs.mockRejectedValueOnce(failure).mockResolvedValue([activeJob()]);
    await mountWorkspace();
    expect(screen.getByText(message)).toBeInTheDocument();
    expect(screen.getByText("Nessun job avvisi registrato")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aggiorna job" })).toBeEnabled();
    await refresh();
    expect(screen.queryByText(message)).not.toBeInTheDocument();
    expect(screen.getByText("Job #11")).toBeInTheDocument();
    await advance(20000);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(3);
  });

  test.each([
    { failure: new Error("Silent unavailable"), message: "Silent unavailable" },
    { failure: "silent rejection", message: "Errore caricamento job avvisi" },
  ])("keeps rows and retries a silent failure without displaying it: $message", async ({ failure, message }) => {
    mocks.incassJobs.mockResolvedValueOnce([activeJob()]).mockRejectedValueOnce(failure).mockResolvedValue([activeJob()]);
    await mountWorkspace();
    await advance(20000);
    expect(screen.getByText("Job #11")).toBeInTheDocument();
    expect(screen.queryByText(message)).not.toBeInTheDocument();
    expect(screen.queryByText("Caricamento job avvisi...")).not.toBeInTheDocument();
    await advance(20000);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(3);
    expect(mocks.authError).toHaveBeenCalledWith(failure);
  });

  test("silent recovery preserves the explicit refresh error until another manual success", async () => {
    mocks.incassJobs.mockResolvedValueOnce([activeJob()]).mockRejectedValueOnce(new Error("Manual unavailable")).mockResolvedValue([activeJob()]);
    await mountWorkspace();
    await refresh();
    expect(screen.getByText("Manual unavailable")).toBeInTheDocument();
    expect(screen.getByText("Job #11")).toBeInTheDocument();
    await advance(20000);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(3);
    expect(screen.getByText("Manual unavailable")).toBeInTheDocument();
    await refresh();
    expect(mocks.incassJobs).toHaveBeenCalledTimes(4);
    expect(screen.queryByText("Manual unavailable")).not.toBeInTheDocument();
  });

  test("a missing token at mount prevents API calls and only manual refresh resumes after login", async () => {
    mocks.token.mockReturnValue(null);
    mocks.incassJobs.mockResolvedValue([activeJob()]);
    await mountWorkspace();
    expect(mocks.incassJobs).not.toHaveBeenCalled();
    expect(screen.getByText(sessionError)).toBeInTheDocument();
    expect(screen.getByText(sessionGuidance)).toBeInTheDocument();
    mocks.token.mockReturnValue("restored-token");
    await advance(90000);
    document.dispatchEvent(new Event("visibilitychange"));
    expect(mocks.incassJobs).not.toHaveBeenCalled();
    await refresh();
    expect(mocks.incassJobs).toHaveBeenCalledExactlyOnceWith("restored-token", { limit: 300 });
    expect(screen.queryByText(sessionError)).not.toBeInTheDocument();
    expect(screen.getByText(sessionGuidance)).toBeInTheDocument();
    await advance(20000);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
  });

  test("token loss during polling freezes the monitor without losing rows and manual login recovery resumes it", async () => {
    mocks.incassJobs.mockResolvedValue([activeJob()]);
    await mountWorkspace();
    mocks.token.mockReturnValue(null);
    await advance(20000);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(1);
    expect(screen.getByText(sessionError)).toBeInTheDocument();
    expect(screen.getByText("Job #11")).toBeInTheDocument();
    mocks.token.mockReturnValue("restored-token");
    await advance(90000);
    document.dispatchEvent(new Event("visibilitychange"));
    expect(mocks.incassJobs).toHaveBeenCalledTimes(1);
    await refresh();
    expect(mocks.incassJobs).toHaveBeenLastCalledWith("restored-token", { limit: 300 });
    expect(screen.queryByText(sessionError)).not.toBeInTheDocument();
    await advance(20000);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(3);
  });

  test.each(["initial", "poll"])("handles %s API auth expiry, stops automatic requests and permits manual recovery", async (phase) => {
    const expiry = new Error("GAIA token expired");
    if (phase === "initial") mocks.incassJobs.mockRejectedValueOnce(expiry).mockResolvedValue([activeJob()]);
    else mocks.incassJobs.mockResolvedValueOnce([activeJob()]).mockRejectedValueOnce(expiry).mockResolvedValue([activeJob()]);
    mocks.authError.mockReturnValueOnce(true);
    await mountWorkspace();
    if (phase === "poll") await advance(20000);
    const stoppedCalls = phase === "initial" ? 1 : 2;
    expect(mocks.incassJobs).toHaveBeenCalledTimes(stoppedCalls);
    expect(screen.getByText(sessionError)).toBeInTheDocument();
    expect(screen.getByText(sessionGuidance)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aggiorna job" })).toBeEnabled();
    await advance(90000);
    document.dispatchEvent(new Event("visibilitychange"));
    expect(mocks.incassJobs).toHaveBeenCalledTimes(stoppedCalls);
    mocks.token.mockReturnValue("restored-token");
    await refresh();
    expect(mocks.incassJobs).toHaveBeenLastCalledWith("restored-token", { limit: 300 });
    expect(screen.queryByText(sessionError)).not.toBeInTheDocument();
    await advance(20000);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(stoppedCalls + 2);
  });
});

describe("Capacitas inCASS queue visibility and ordering", () => {
  test("prioritizes running/resume jobs when collapsed, preserves API order expanded and re-collapses after refresh", async () => {
    const jobs = Array.from({ length: 18 }, (_, index) => job(101 + index));
    jobs[1] = activeJob(102, "pending");
    jobs[3] = activeJob(104, "processing");
    jobs[5] = activeJob(106, "queued_resume");
    mocks.incassJobs.mockResolvedValueOnce(jobs).mockResolvedValue([...jobs].reverse());
    await mountWorkspace();
    const collapsed = [104, 106, 101, 102, 103, 105, 107, 108, 109, 110, 111, 112, 113, 114, 115];
    expect(visibleIds()).toEqual(collapsed.map((id) => `Job #${id}`));
    expect(screen.getByText(/^Mostrati/)).toHaveTextContent("Mostrati 15 di 18 job. Altri 3 sono nascosti.");
    fireEvent.click(screen.getByRole("button", { name: "Mostra tutti (18)" }));
    expect(visibleIds()).toEqual(jobs.map((entry) => `Job #${entry.id}`));
    expect(screen.getByText(/^Mostrati/)).toHaveTextContent("Mostrati 18 di 18 job.");
    expect(screen.getByText(/^Mostrati/)).not.toHaveTextContent("nascosti");
    await advance(20000);
    expect(visibleIds()).toEqual([...jobs].reverse().map((entry) => `Job #${entry.id}`));
    expect(screen.getByRole("button", { name: "Mostra solo primi 15" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Mostra solo primi 15" }));
    expect(visibleIds()).toEqual([106, 104, 118, 117, 116, 115, 114, 113, 112, 111, 110, 109, 108, 107, 105].map((id) => `Job #${id}`));
    expect(screen.queryByText("Job #102")).not.toBeInTheDocument();
  });

  test.each([15, 16])("shows the expand toggle only above the 15-job boundary: %s jobs", async (count) => {
    const jobs = Array.from({ length: count }, (_, index) => job(101 + index));
    mocks.incassJobs.mockResolvedValue(jobs);
    await mountWorkspace();
    expect(visibleIds()).toHaveLength(15);
    expect(screen.getByText(/^Mostrati/)).toHaveTextContent(`Mostrati 15 di ${count} job.`);
    const toggle = screen.queryByRole("button", { name: `Mostra tutti (${count})` });
    if (count === 16) {
      expect(toggle).toBeInTheDocument();
      fireEvent.click(toggle!);
      expect(visibleIds()).toHaveLength(16);
      expect(screen.getByText("Job #116")).toBeInTheDocument();
    } else expect(toggle).not.toBeInTheDocument();
  });
});

describe("Capacitas inCASS result shape and presentation", () => {
  test.each([
    { label: "null", value: null },
    { label: "array", value: [] },
    { label: "missing fields", value: {} },
    { label: "non-array items", value: { ...result(), items: {} } },
    { label: "non-numeric processed_subjects", value: { ...result(), processed_subjects: "0" } },
    { label: "non-numeric failed_subjects", value: { ...result(), failed_subjects: "0" } },
    { label: "non-numeric notices_found", value: { ...result(), notices_found: "0" } },
    { label: "non-numeric notices_synced", value: { ...result(), notices_synced: "0" } },
  ])("rejects $label results and displays the persisted job error instead of counters", async ({ value }) => {
    mocks.incassJobs.mockResolvedValue([job(11, { status: "failed", result_json: value, error_detail: "Portale non disponibile" })]);
    await mountWorkspace();
    expect(card(11).getByText("Portale non disponibile")).toBeInTheDocument();
    expect(card(11).queryByText("Soggetti processati")).not.toBeInTheDocument();
    expect(card(11).queryByRole("table")).not.toBeInTheDocument();
    expect(card(11).queryByText(/%$/)).not.toBeInTheDocument();
    expect(card(11).getByRole("button", { name: "Elimina" })).toBeEnabled();
  });

  test("an invalid result without persisted error renders a safe row without a result section", async () => {
    mocks.incassJobs.mockResolvedValue([job(11, { result_json: { items: "invalid" } })]);
    await mountWorkspace();
    expect(card(11).getByText("Completato")).toBeInTheDocument();
    expect(card(11).queryByText("Soggetti processati")).not.toBeInTheDocument();
    expect(card(11).queryByRole("table")).not.toBeInTheDocument();
    expect(card(11).getByRole("button", { name: "Rilancia" })).toBeEnabled();
  });

  test.each([
    { status: "succeeded", progress: "100%", total: undefined },
    { status: "processing", progress: "0%", total: 0 },
  ])("renders empty $status results with zero optional counters and $progress progress", async ({ status, progress, total }) => {
    mocks.incassJobs.mockResolvedValue([job(11, { status, result_json: result({ total_items: total }) })]);
    await mountWorkspace();
    expect(card(11).getByText("soggetti 0/? · avvisi 0/0 · pagati 0")).toBeInTheDocument();
    expect(card(11).getByText(progress)).toBeInTheDocument();
    expectStat(11, "Soggetti processati", "0", "0 con errore.");
    expectStat(11, "Avvisi sincronizzati", "0");
    expectStat(11, "Stato pagamenti", "0/0/0");
    expectStat(11, "Nuovi pagati", "0", "0 cambi stato pagamento.");
    expect(card(11).queryByRole("table")).not.toBeInTheDocument();
  });

  test("renders aggregate payments and real item outcomes with nullable field and optional counter fallbacks", async () => {
    const detailed = result({
      items: [
        item(301, { display_name: "Ada Rossi", notices_found: 3, notices_synced: 3, paid_notices: 2, partial_notices: 1, unpaid_notices: 0, newly_paid_notices: 1 }),
        item(302, { display_name: null, identifier: null, status: "failed", notices_synced: 0, unpaid_notices: 1, error: "Richiesta fallita" }),
        item(303, { status: "skipped", notices_found: 0, notices_synced: 0 }),
      ],
      processed_subjects: 3, failed_subjects: 1, notices_found: 4, notices_synced: 3,
      paid_notices: 2, partial_notices: 1, unpaid_notices: 1, newly_paid_notices: 1,
      payment_status_changed: 2,
    });
    mocks.incassJobs.mockResolvedValue([job(11, { status: "completed_with_errors", result_json: detailed, error_detail: "Hidden job-level error" })]);
    await mountWorkspace();
    expect(card(11).getByText("soggetti 3/3 · avvisi 3/4 · pagati 2")).toBeInTheDocument();
    expect(card(11).getByText("100%")).toBeInTheDocument();
    expectStat(11, "Soggetti processati", "3", "1 con errore.");
    expectStat(11, "Avvisi trovati", "4");
    expectStat(11, "Avvisi sincronizzati", "3");
    expectStat(11, "Stato pagamenti", "2/1/1");
    expectStat(11, "Nuovi pagati", "1", "2 cambi stato pagamento.");
    expect(card(11).queryByText("Hidden job-level error")).not.toBeInTheDocument();
    const rows = within(card(11).getByRole("table")).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(3);
    const first = within(rows[0]);
    expect(first.getByText("Ada Rossi")).toBeInTheDocument();
    expect(first.getByText("CF-301")).toBeInTheDocument();
    expect(first.getByText("synced")).toHaveClass("text-emerald-700");
    expect(first.getByText("3/3")).toBeInTheDocument();
    expect(first.getByText("+1 pagati")).toBeInTheDocument();
    const failed = within(rows[1]);
    expect(failed.getAllByText("302")).toHaveLength(2);
    expect(failed.getByText("—")).toBeInTheDocument();
    expect(failed.getByText("failed")).toHaveClass("text-rose-700");
    expect(failed.getByText("0/1")).toBeInTheDocument();
    expect(failed.getByText("0/0/1")).toBeInTheDocument();
    expect(failed.getByText("Richiesta fallita")).toBeInTheDocument();
    const skipped = within(rows[2]);
    expect(skipped.getByText("skipped")).toHaveClass("text-amber-700");
    expect(skipped.getByText("0/0/0")).toBeInTheDocument();
    expect(skipped.queryByText(/pagati$/)).not.toBeInTheDocument();
    expect(card(11).queryByText(/^Anteprima dei primi/)).not.toBeInTheDocument();
  });

  test("renders only 12 of the API's 15 preview items and uses the real untruncated total", async () => {
    const preview = Array.from({ length: 15 }, (_, index) => item(401 + index));
    mocks.incassJobs.mockResolvedValue([job(11, { result_json: result({
      items: preview, processed_subjects: 20, failed_subjects: 0, notices_found: 20,
      notices_synced: 20, total_items: 20, items_truncated: true,
    }) })]);
    await mountWorkspace();
    expect(card(11).getByText("soggetti 20/20 · avvisi 20/20 · pagati 0")).toBeInTheDocument();
    expect(card(11).getByText("100%")).toBeInTheDocument();
    expect(within(card(11).getByRole("table")).getAllByRole("row")).toHaveLength(13);
    expect(card(11).getByText("Soggetto 401")).toBeInTheDocument();
    expect(card(11).getByText("Soggetto 412")).toBeInTheDocument();
    expect(card(11).queryByText("Soggetto 413")).not.toBeInTheDocument();
    expect(card(11).getByText("Anteprima dei primi 15 soggetti su 20.")).toBeInTheDocument();
  });
});
