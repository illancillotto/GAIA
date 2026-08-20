import { describe, expect, test, vi } from "vitest";

import {
  classifySisterCredentialTest,
  isSisterCredentialTestRunning,
  shouldRefreshSisterCredentialAfterTest,
  testSisterCredentialPool,
  type SisterCredentialTestProgress,
} from "@/lib/sister-credential-tests";
import type { ElaborazioneCredential, ElaborazioneCredentialTestResult } from "@/types/api";

function credential(id: string): ElaborazioneCredential {
  return {
    id,
    user_id: 1,
    label: `Profilo ${id}`,
    sister_username: `user-${id}`,
    convenzione: null,
    codice_richiesta: null,
    ufficio_provinciale: "ORISTANO Territorio",
    active: true,
    is_default: false,
    verified_at: null,
    created_at: "2026-08-20T08:00:00Z",
    updated_at: "2026-08-20T08:00:00Z",
  };
}

function result(
  id: string,
  overrides: Partial<ElaborazioneCredentialTestResult> = {},
): ElaborazioneCredentialTestResult {
  return {
    id,
    credential_id: "credential-1",
    status: "completed",
    success: true,
    mode: "worker",
    reachable: true,
    authenticated: true,
    message: "ok",
    verified_at: "2026-08-20T08:05:00Z",
    created_at: "2026-08-20T08:00:00Z",
    started_at: "2026-08-20T08:01:00Z",
    completed_at: "2026-08-20T08:05:00Z",
    ...overrides,
  };
}

describe("SISTER credential test orchestration", () => {
  test("classifies running, authenticated, reachable and failed outcomes", () => {
    expect(isSisterCredentialTestRunning("pending")).toBe(true);
    expect(isSisterCredentialTestRunning("processing")).toBe(true);
    expect(isSisterCredentialTestRunning("completed")).toBe(false);
    expect(shouldRefreshSisterCredentialAfterTest(false, "completed")).toBe(true);
    expect(shouldRefreshSisterCredentialAfterTest(true, "completed")).toBe(false);
    expect(shouldRefreshSisterCredentialAfterTest(false, "processing")).toBe(false);

    expect(
      classifySisterCredentialTest("credential-1", result("pending", { status: "pending", message: null })).phase,
    ).toBe("running");
    expect(
      classifySisterCredentialTest("credential-1", result("processing", { status: "processing" })).message,
    ).toBe("ok");
    expect(classifySisterCredentialTest("credential-1", result("success")).phase).toBe("success");
    expect(
      classifySisterCredentialTest("credential-1", result("success-fallback", { message: null })).message,
    ).toBe("Autenticazione SISTER confermata.");
    expect(
      classifySisterCredentialTest(
        "credential-1",
        result("warning-success", { authenticated: false, success: true, reachable: false }),
      ).phase,
    ).toBe("warning");
    expect(
      classifySisterCredentialTest(
        "credential-1",
        result("warning-reachable", { authenticated: false, success: false, reachable: true, message: null }),
      ).message,
    ).toBe("Portale raggiungibile, autenticazione non confermata.");
    expect(
      classifySisterCredentialTest(
        "credential-1",
        result("failed", { status: "failed", authenticated: false, success: false, reachable: false }),
      ).phase,
    ).toBe("error");
    expect(
      classifySisterCredentialTest(
        "credential-1",
        result("failed-fallback", {
          status: "failed",
          authenticated: false,
          success: null,
          reachable: null,
          message: null,
        }),
      ).message,
    ).toBe("Test credenziale SISTER fallito.");
  });

  test("runs every credential sequentially and continues after a failed request", async () => {
    const credentials = [credential("one"), credential("two"), credential("three")];
    const events: string[] = [];
    const progress: SisterCredentialTestProgress[] = [];
    const terminalResults: ElaborazioneCredentialTestResult[] = [];

    const run = await testSisterCredentialPool({
      credentials,
      startTest: async (credentialId) => {
        events.push(`start:${credentialId}`);
        if (credentialId === "two") {
          throw new Error("credenziale rifiutata");
        }
        return result(`test-${credentialId}`, { credential_id: credentialId });
      },
      getTest: vi.fn(),
      onProgress: (item) => progress.push(item),
      onTerminalResult: (item) => {
        terminalResults.push(item);
        events.push(`done:${item.credential_id}`);
      },
    });

    expect(run).toEqual({ cancelled: false, processed: 3 });
    expect(events).toEqual(["start:one", "done:one", "start:two", "start:three", "done:three"]);
    expect(progress.find((item) => item.credentialId === "two" && item.phase === "error")?.message).toBe(
      "credenziale rifiutata",
    );
    expect(terminalResults).toHaveLength(2);
  });

  test("polls a pending test until completion", async () => {
    const getTest = vi
      .fn()
      .mockResolvedValueOnce(result("test-one", { status: "processing", authenticated: null, success: null }))
      .mockResolvedValueOnce(result("test-one"));
    const progress: SisterCredentialTestProgress[] = [];

    const run = await testSisterCredentialPool({
      credentials: [credential("one")],
      startTest: vi.fn().mockResolvedValue(
        result("test-one", { status: "pending", authenticated: null, success: null, reachable: null, message: null }),
      ),
      getTest,
      onProgress: (item) => progress.push(item),
      wait: vi.fn().mockResolvedValue(undefined),
      pollIntervalMs: 5,
      maxPollAttempts: 3,
    });

    expect(run).toEqual({ cancelled: false, processed: 1 });
    expect(getTest).toHaveBeenCalledTimes(2);
    expect(progress.map((item) => item.phase)).toEqual(["running", "running", "running", "success"]);
  });

  test("reports a timeout when the configured polling budget is exhausted", async () => {
    const progress: SisterCredentialTestProgress[] = [];
    const pending = result("test-one", { status: "pending", authenticated: null, success: null });

    await testSisterCredentialPool({
      credentials: [credential("one")],
      startTest: vi.fn().mockResolvedValue(pending),
      getTest: vi.fn(),
      onProgress: (item) => progress.push(item),
      maxPollAttempts: 0,
    });

    expect(progress.at(-1)).toMatchObject({
      phase: "error",
      message: "Timeout: il worker non ha concluso il test entro il tempo previsto.",
      result: pending,
    });
  });

  test("marks all credentials as stopped when already cancelled", async () => {
    const controller = new AbortController();
    const progress: SisterCredentialTestProgress[] = [];
    controller.abort();

    const run = await testSisterCredentialPool({
      credentials: [credential("one"), credential("two")],
      startTest: vi.fn(),
      getTest: vi.fn(),
      onProgress: (item) => progress.push(item),
      signal: controller.signal,
    });

    expect(run).toEqual({ cancelled: true, processed: 0 });
    expect(progress.map((item) => [item.credentialId, item.phase])).toEqual([
      ["one", "stopped"],
      ["two", "stopped"],
    ]);
  });

  test("stops the current and following credentials when cancelled while polling", async () => {
    const controller = new AbortController();
    const progress: SisterCredentialTestProgress[] = [];

    const run = await testSisterCredentialPool({
      credentials: [credential("one"), credential("two")],
      startTest: vi.fn().mockResolvedValue(
        result("test-one", { status: "pending", authenticated: null, success: null }),
      ),
      getTest: vi.fn(),
      onProgress: (item) => progress.push(item),
      signal: controller.signal,
      wait: async () => controller.abort(),
    });

    expect(run).toEqual({ cancelled: true, processed: 0 });
    expect(progress.slice(-2).map((item) => item.phase)).toEqual(["stopped", "stopped"]);
  });

  test("handles cancellation raised during the start request", async () => {
    const controller = new AbortController();
    const progress: SisterCredentialTestProgress[] = [];

    const run = await testSisterCredentialPool({
      credentials: [credential("one"), credential("two")],
      startTest: async () => {
        controller.abort();
        throw new Error("aborted request");
      },
      getTest: vi.fn(),
      onProgress: (item) => progress.push(item),
      signal: controller.signal,
    });

    expect(run.cancelled).toBe(true);
    expect(progress.slice(-2).map((item) => item.phase)).toEqual(["stopped", "stopped"]);
  });

  test("uses the fallback message for non-Error failures", async () => {
    const progress: SisterCredentialTestProgress[] = [];

    await testSisterCredentialPool({
      credentials: [credential("one")],
      startTest: async () => {
        throw "network";
      },
      getTest: vi.fn(),
      onProgress: (item) => progress.push(item),
    });

    expect(progress.at(-1)?.message).toBe("Errore imprevisto durante il test SISTER.");
  });

  test("checks cancellation between two completed credentials", async () => {
    const controller = new AbortController();
    const progress: SisterCredentialTestProgress[] = [];

    const run = await testSisterCredentialPool({
      credentials: [credential("one"), credential("two")],
      startTest: async (credentialId) => result(`test-${credentialId}`, { credential_id: credentialId }),
      getTest: vi.fn(),
      onProgress: (item) => progress.push(item),
      onTerminalResult: () => controller.abort(),
      signal: controller.signal,
    });

    expect(run).toEqual({ cancelled: true, processed: 1 });
    expect(progress.at(-1)).toMatchObject({ credentialId: "two", phase: "stopped" });
  });

  test("supports an empty pool", async () => {
    await expect(
      testSisterCredentialPool({
        credentials: [],
        startTest: vi.fn(),
        getTest: vi.fn(),
        onProgress: vi.fn(),
      }),
    ).resolves.toEqual({ cancelled: false, processed: 0 });
  });

  test("uses the browser timer and default polling limits", async () => {
    vi.useFakeTimers();
    try {
      const promise = testSisterCredentialPool({
        credentials: [credential("one")],
        startTest: vi.fn().mockResolvedValue(
          result("test-one", { status: "pending", authenticated: null, success: null }),
        ),
        getTest: vi.fn().mockResolvedValue(result("test-one")),
        onProgress: vi.fn(),
      });
      await vi.advanceTimersByTimeAsync(1500);
      await expect(promise).resolves.toEqual({ cancelled: false, processed: 1 });
    } finally {
      vi.useRealTimers();
    }
  });
});
