import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import {
  EXPORT_JOB_HISTORY_LIMIT,
  EXPORT_JOB_HISTORY_POLL_INTERVAL_MS,
  findNewlyCompletedJobs,
  hasActiveExportJob,
  isActiveExportJobStatus,
  sortExportJobs,
  useExportJobHistory,
  type ExportJobHistoryOptions,
} from "@/app/presenze/export/use-export-job-history";
import type { PresenzeSyncJob } from "@/types/api";

const auth = vi.hoisted(() => ({ getStoredAccessToken: vi.fn() }));
vi.mock("@/lib/auth", () => auth);

function job(id: string, status: string, createdAt = "2026-06-04T09:00:00Z"): PresenzeSyncJob {
  return {
    id,
    status,
    requested_by_user_id: 1,
    credential_id: null,
    import_job_id: null,
    period_start: "2026-05-01",
    period_end: "2026-05-31",
    collaborator_limit: 1,
    records_imported: 0,
    records_skipped: 0,
    records_errors: 0,
    json_artifact_path: null,
    worker_log_path: null,
    worker_pid: null,
    attempt_count: 1,
    max_attempts: 1,
    error_detail: null,
    params_json: {},
    created_at: createdAt,
    started_at: null,
    finished_at: null,
  } as PresenzeSyncJob;
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

const completionNotice = (item: PresenzeSyncJob) => `pronto ${item.id}`;

function buildOptions(overrides: Partial<ExportJobHistoryOptions> = {}): ExportJobHistoryOptions {
  return {
    enabled: true,
    listJobs: vi.fn().mockResolvedValue([]),
    completionNotice,
    loadErrorMessage: "Errore storico",
    onSuccess: vi.fn(),
    onError: vi.fn(),
    ...overrides,
  };
}

// waitFor polls through setInterval, which these tests fake: settle pending promises through act instead.
async function flush() {
  await act(async () => {
    for (let index = 0; index < 5; index += 1) {
      await Promise.resolve();
    }
  });
}

async function tick() {
  await act(async () => {
    vi.advanceTimersByTime(EXPORT_JOB_HISTORY_POLL_INTERVAL_MS);
  });
}

describe("export job history helpers", () => {
  test("sorts jobs by creation date descending without mutating the input", () => {
    const items = [job("old", "completed", "2026-06-01T09:00:00Z"), job("new", "completed", "2026-06-03T09:00:00Z")];
    expect(sortExportJobs(items).map((item) => item.id)).toEqual(["new", "old"]);
    expect(items.map((item) => item.id)).toEqual(["old", "new"]);
  });

  test("treats only pending and running statuses as active", () => {
    expect(isActiveExportJobStatus("pending")).toBe(true);
    expect(isActiveExportJobStatus("running")).toBe(true);
    expect(isActiveExportJobStatus("completed")).toBe(false);
    expect(isActiveExportJobStatus(undefined)).toBe(false);
    expect(hasActiveExportJob(new Map())).toBe(false);
    expect(hasActiveExportJob(new Map([["a", "failed"], ["b", "running"]]))).toBe(true);
  });

  test("finds only jobs that moved from an active status to completed", () => {
    const known = new Map([
      ["was-pending", "pending"],
      ["was-running", "running"],
      ["was-failed", "failed"],
      ["still-running", "running"],
    ]);
    const items = [
      job("was-pending", "completed"),
      job("was-running", "completed"),
      job("was-failed", "completed"),
      job("still-running", "running"),
      job("unknown", "completed"),
    ];
    expect(findNewlyCompletedJobs(items, known).map((item) => item.id)).toEqual(["was-pending", "was-running"]);
  });
});

describe("useExportJobHistory", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
    auth.getStoredAccessToken.mockReset();
    auth.getStoredAccessToken.mockReturnValue("token");
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("does nothing without an access token", async () => {
    auth.getStoredAccessToken.mockReturnValue(null);
    const options = buildOptions();
    const { result } = renderHook(() => useExportJobHistory(options));

    await tick();

    expect(options.listJobs).not.toHaveBeenCalled();
    expect(result.current.isLoading).toBe(true);
    expect(result.current.jobs).toEqual([]);
    expect(vi.getTimerCount()).toBe(0);
  });

  test("loads sorted jobs with the history limit and clears the loading flag", async () => {
    const listJobs = vi.fn().mockResolvedValue([job("old", "completed", "2026-06-01T09:00:00Z"), job("new", "completed", "2026-06-03T09:00:00Z")]);
    const options = buildOptions({ listJobs });
    const { result } = renderHook(() => useExportJobHistory(options));

    expect(result.current.isLoading).toBe(true);
    await flush();
    expect(result.current.isLoading).toBe(false);

    expect(listJobs).toHaveBeenCalledWith("token", { limit: EXPORT_JOB_HISTORY_LIMIT });
    expect(EXPORT_JOB_HISTORY_LIMIT).toBe(25);
    expect(result.current.jobs.map((item) => item.id)).toEqual(["new", "old"]);
    expect(Array.from(result.current.knownStatusesRef.current.entries())).toEqual([
      ["new", "completed"],
      ["old", "completed"],
    ]);
    expect(options.onSuccess).not.toHaveBeenCalled();
  });

  test("does not poll when no known job is active", async () => {
    const listJobs = vi.fn().mockResolvedValue([job("done", "completed")]);
    const options = buildOptions({ listJobs });
    renderHook(() => useExportJobHistory(options));

    await flush();
    expect(listJobs).toHaveBeenCalledTimes(1);
    await tick();
    await tick();

    expect(listJobs).toHaveBeenCalledTimes(1);
  });

  test("polls silently every interval while a job is active and announces completions", async () => {
    const silentLoad = deferred<PresenzeSyncJob[]>();
    const listJobs = vi
      .fn()
      .mockResolvedValueOnce([job("a", "running"), job("b", "failed")])
      .mockReturnValueOnce(silentLoad.promise);
    const options = buildOptions({ listJobs });
    const { result } = renderHook(() => useExportJobHistory(options));

    await flush();
    expect(result.current.isLoading).toBe(false);
    expect(EXPORT_JOB_HISTORY_POLL_INTERVAL_MS).toBe(2500);
    await act(async () => {
      vi.advanceTimersByTime(EXPORT_JOB_HISTORY_POLL_INTERVAL_MS - 1);
    });
    expect(listJobs).toHaveBeenCalledTimes(1);

    await act(async () => {
      vi.advanceTimersByTime(1);
    });
    expect(listJobs).toHaveBeenCalledTimes(2);
    expect(result.current.isLoading).toBe(false);

    await act(async () => {
      silentLoad.resolve([job("a", "completed"), job("b", "completed")]);
    });

    expect(options.onSuccess).toHaveBeenCalledTimes(1);
    expect(options.onSuccess).toHaveBeenCalledWith("pronto a");
    expect(result.current.isLoading).toBe(false);
    expect(result.current.jobs.map((item) => item.status)).toEqual(["completed", "completed"]);

    await tick();
    expect(listJobs).toHaveBeenCalledTimes(2);
  });

  test("polls a job registered through the returned ref", async () => {
    const listJobs = vi.fn().mockResolvedValueOnce([]).mockResolvedValue([job("new", "completed")]);
    const options = buildOptions({ listJobs });
    const { result } = renderHook(() => useExportJobHistory(options));

    await flush();
    expect(result.current.isLoading).toBe(false);
    await tick();
    expect(listJobs).toHaveBeenCalledTimes(1);

    act(() => {
      result.current.setJobs([job("new", "pending")]);
      result.current.knownStatusesRef.current.set("new", "pending");
    });
    expect(result.current.jobs.map((item) => item.id)).toEqual(["new"]);
    await tick();

    await flush();
    expect(options.onSuccess).toHaveBeenCalledWith("pronto new");
    expect(listJobs).toHaveBeenCalledTimes(2);
  });

  test("suppresses the completion notice on the initial load of a re-run effect", async () => {
    const firstList = vi.fn().mockResolvedValue([job("a", "running")]);
    const secondList = vi.fn().mockResolvedValue([job("a", "completed")]);
    const options = buildOptions({ listJobs: firstList });
    const { result, rerender } = renderHook((props: ExportJobHistoryOptions) => useExportJobHistory(props), { initialProps: options });

    await flush();
    expect(result.current.isLoading).toBe(false);
    rerender({ ...options, listJobs: secondList });

    await flush();
    expect(result.current.jobs[0]?.status).toBe("completed");
    expect(secondList).toHaveBeenCalledTimes(1);
    expect(options.onSuccess).not.toHaveBeenCalled();
  });

  test("resets the history when disabled", async () => {
    const listJobs = vi.fn().mockResolvedValue([job("a", "running")]);
    const options = buildOptions({ listJobs });
    const { result, rerender } = renderHook((props: ExportJobHistoryOptions) => useExportJobHistory(props), { initialProps: options });

    await flush();
    expect(result.current.jobs).toHaveLength(1);
    rerender({ ...options, enabled: false });

    expect(result.current.jobs).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.knownStatusesRef.current.size).toBe(0);
    await tick();
    expect(listJobs).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(0);
  });

  test("starts disabled without loading", async () => {
    const options = buildOptions({ enabled: false });
    const { result } = renderHook(() => useExportJobHistory(options));

    expect(result.current.isLoading).toBe(false);
    await tick();
    expect(options.listJobs).not.toHaveBeenCalled();
  });

  test("reports Error messages and clears the loading flag", async () => {
    const options = buildOptions({ listJobs: vi.fn().mockRejectedValue(new Error("Storico non disponibile")) });
    const { result } = renderHook(() => useExportJobHistory(options));

    await flush();
    expect(result.current.isLoading).toBe(false);
    expect(options.onError).toHaveBeenCalledWith("Storico non disponibile");
  });

  test("reports the fallback message for non-Error rejections", async () => {
    const options = buildOptions({ listJobs: vi.fn().mockRejectedValue("boom") });
    const { result } = renderHook(() => useExportJobHistory(options));

    await flush();
    expect(result.current.isLoading).toBe(false);
    expect(options.onError).toHaveBeenCalledWith("Errore storico");
  });

  test("reports silent polling errors without touching the loading flag", async () => {
    const silentLoad = deferred<PresenzeSyncJob[]>();
    const listJobs = vi.fn().mockResolvedValueOnce([job("a", "pending")]).mockReturnValueOnce(silentLoad.promise);
    const options = buildOptions({ listJobs });
    const { result } = renderHook(() => useExportJobHistory(options));

    await flush();
    expect(result.current.isLoading).toBe(false);
    await tick();
    await act(async () => {
      silentLoad.reject(new Error("Polling fallito"));
    });

    expect(options.onError).toHaveBeenCalledWith("Polling fallito");
    expect(result.current.isLoading).toBe(false);
    expect(result.current.jobs.map((item) => item.status)).toEqual(["pending"]);
  });

  test("ignores a load resolved after unmount and clears the interval", async () => {
    const pendingLoad = deferred<PresenzeSyncJob[]>();
    const options = buildOptions({ listJobs: vi.fn().mockReturnValue(pendingLoad.promise) });
    const { result, unmount } = renderHook(() => useExportJobHistory(options));
    const knownStatusesRef = result.current.knownStatusesRef;

    expect(vi.getTimerCount()).toBe(1);
    unmount();
    expect(vi.getTimerCount()).toBe(0);
    await act(async () => {
      pendingLoad.resolve([job("a", "completed")]);
    });

    expect(knownStatusesRef.current.size).toBe(0);
    expect(options.onSuccess).not.toHaveBeenCalled();
    expect(options.onError).not.toHaveBeenCalled();
  });

  test("ignores a load rejected after unmount", async () => {
    const pendingLoad = deferred<PresenzeSyncJob[]>();
    const options = buildOptions({ listJobs: vi.fn().mockReturnValue(pendingLoad.promise) });
    const { unmount } = renderHook(() => useExportJobHistory(options));

    unmount();
    await act(async () => {
      pendingLoad.reject(new Error("late failure"));
    });

    expect(options.onError).not.toHaveBeenCalled();
  });

  test("keeps the loading flag of a new load when a stale load settles after enabled toggles", async () => {
    const staleLoad = deferred<PresenzeSyncJob[]>();
    const freshLoad = deferred<PresenzeSyncJob[]>();
    const listJobs = vi.fn().mockReturnValueOnce(staleLoad.promise).mockReturnValueOnce(freshLoad.promise);
    const options = buildOptions({ listJobs });
    const { result, rerender } = renderHook((props: ExportJobHistoryOptions) => useExportJobHistory(props), { initialProps: options });

    expect(result.current.isLoading).toBe(true);
    rerender({ ...options, enabled: false });
    expect(result.current.isLoading).toBe(false);
    rerender({ ...options, enabled: true });
    expect(listJobs).toHaveBeenCalledTimes(2);
    expect(result.current.isLoading).toBe(true);

    await act(async () => {
      staleLoad.resolve([job("stale", "completed")]);
    });
    expect(result.current.isLoading).toBe(true);
    expect(result.current.jobs).toEqual([]);

    await act(async () => {
      freshLoad.resolve([job("fresh", "completed")]);
    });
    expect(result.current.isLoading).toBe(false);
    expect(result.current.jobs.map((item) => item.id)).toEqual(["fresh"]);
  });
});
