import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { SisterCredentialPool } from "@/components/elaborazioni/sister-credential-pool";
import type { ElaborazioneCredential, ElaborazioneCredentialTestResult } from "@/types/api";

const apiMocks = vi.hoisted(() => ({
  getElaborazioneCredentialTest: vi.fn(),
  testElaborazioneCredentials: vi.fn(),
  updateElaborazioneCredential: vi.fn(),
}));

const authState = vi.hoisted(() => ({ token: "token" as string | null }));

vi.mock("@/lib/api", () => apiMocks);
vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: () => authState.token,
}));

function credential(id: string, overrides: Partial<ElaborazioneCredential> = {}): ElaborazioneCredential {
  return {
    id,
    user_id: 1,
    label: `Profilo ${id}`,
    sister_username: `user-${id}`,
    convenzione: "CONSORZIO DI BONIFICA DELL'ORISTANESE",
    codice_richiesta: `CODE-${id}`,
    ufficio_provinciale: "ORISTANO Territorio",
    active: true,
    is_default: false,
    verified_at: null,
    created_at: "2026-08-20T08:00:00Z",
    updated_at: "2026-08-20T08:00:00Z",
    ...overrides,
  };
}

function result(
  id: string,
  credentialId: string,
  overrides: Partial<ElaborazioneCredentialTestResult> = {},
): ElaborazioneCredentialTestResult {
  return {
    id,
    credential_id: credentialId,
    status: "completed",
    success: true,
    mode: "worker",
    reachable: true,
    authenticated: true,
    message: `Esito ${credentialId}`,
    verified_at: "2026-08-20T08:05:00Z",
    created_at: "2026-08-20T08:00:00Z",
    started_at: "2026-08-20T08:01:00Z",
    completed_at: "2026-08-20T08:05:00Z",
    ...overrides,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function props(overrides: Record<string, unknown> = {}) {
  return {
    credentials: [] as ElaborazioneCredential[],
    selectedCredentialId: null as string | null,
    currentTestResult: null as ElaborazioneCredentialTestResult | null,
    embedded: false,
    externalBusy: false,
    releaseBusy: false,
    resumeReleasedBusy: false,
    releasedBatchesCount: 0,
    onSelectCredential: vi.fn(),
    onMakeDefault: vi.fn().mockResolvedValue(undefined),
    onDeleteCredential: vi.fn(),
    onTestResult: vi.fn(),
    onTestError: vi.fn(),
    onClearFeedback: vi.fn(),
    onRefreshCredentials: vi.fn().mockResolvedValue(undefined),
    onBulkBusyChange: vi.fn(),
    onReleaseSessions: vi.fn().mockResolvedValue(undefined),
    onResumeReleasedBatch: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

describe("SisterCredentialPool", () => {
  beforeEach(() => {
    authState.token = "token";
    apiMocks.getElaborazioneCredentialTest.mockReset();
    apiMocks.testElaborazioneCredentials.mockReset();
    apiMocks.updateElaborazioneCredential.mockReset();
    apiMocks.updateElaborazioneCredential.mockResolvedValue(credential("updated", { active: false }));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("renders the empty state and disabled pool controls", () => {
    const view = render(<SisterCredentialPool {...props({ externalBusy: true })} />);

    expect(screen.getByText("Nessuna credenziale SISTER configurata")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Testa tutte" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Nessun batch in pausa" })).toBeDisabled();
    expect(screen.getByText("Nessun batch in pausa da rilascio sessioni disponibile per la ripartenza.")).toBeInTheDocument();

    view.rerender(<SisterCredentialPool {...props({ embedded: true })} />);
    expect(screen.getByText("Nessuna credenziale SISTER configurata")).toBeInTheDocument();
    view.unmount();
  });

  test("renders responsive cards and delegates card actions", async () => {
    const primary = credential("primary", { is_default: true, verified_at: "2026-08-19T10:00:00Z" });
    const secondary = credential("secondary", {
      active: false,
      convenzione: null,
      codice_richiesta: null,
    });
    const currentTest = result("test-secondary", "secondary", {
      status: "processing",
      success: null,
      reachable: null,
      authenticated: null,
      message: null,
    });
    const callbacks = props({
      credentials: [primary, secondary],
      selectedCredentialId: "secondary",
      currentTestResult: currentTest,
      embedded: true,
      releasedBatchesCount: 2,
      resumeReleasedBusy: true,
      releaseBusy: true,
    });
    render(<SisterCredentialPool {...callbacks} />);

    expect(screen.getByText("1/2 attive")).toBeInTheDocument();
    expect(screen.getByText("1 verificate")).toBeInTheDocument();
    expect(screen.getByText("2 batch in pausa dopo il rilascio delle sessioni SISTER.")).toBeInTheDocument();
    expect(screen.getByText("Default")).toBeInTheDocument();
    expect(screen.getByText("Disattiva")).toBeInTheDocument();
    expect(screen.getByText("In verifica")).toBeInTheDocument();
    expect(screen.getAllByText("Non indicata")).toHaveLength(1);
    expect(screen.getAllByText("Non indicato")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Ripresa..." })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Pausa..." })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Sessione in pausa" })).toBeDisabled();

    const secondaryCard = screen.getByText("Profilo secondary").closest("article");
    expect(secondaryCard).not.toBeNull();
    fireEvent.click(within(secondaryCard!).getByRole("button", { name: "Modifica" }));
    fireEvent.click(within(secondaryCard!).getByRole("button", { name: "Rendi default" }));
    fireEvent.click(within(secondaryCard!).getByRole("button", { name: "Elimina" }));

    expect(callbacks.onSelectCredential).toHaveBeenCalledWith(secondary);
    expect(callbacks.onMakeDefault).toHaveBeenCalledWith(secondary);
    expect(callbacks.onDeleteCredential).toHaveBeenCalledWith(secondary);
  });

  test("starts an individual saved-credential test", async () => {
    const item = credential("one");
    const pending = deferred<ElaborazioneCredentialTestResult>();
    apiMocks.testElaborazioneCredentials.mockReturnValue(pending.promise);
    const callbacks = props({ credentials: [item], releasedBatchesCount: 1 });
    render(<SisterCredentialPool {...callbacks} />);

    fireEvent.click(screen.getByRole("button", { name: "Testa" }));
    expect(screen.getByRole("button", { name: "Test in corso" })).toBeDisabled();
    expect(callbacks.onSelectCredential).toHaveBeenCalledWith(item);
    expect(callbacks.onClearFeedback).toHaveBeenCalledTimes(1);
    expect(apiMocks.testElaborazioneCredentials).toHaveBeenCalledWith("token", { credential_id: "one" });

    pending.resolve(result("test-one", "one"));
    await waitFor(() => expect(callbacks.onTestResult).toHaveBeenCalledWith(result("test-one", "one")));
    expect(screen.getByRole("button", { name: "Testa" })).toBeEnabled();

    fireEvent.click(screen.getByRole("button", { name: "Riprendi batch" }));
    fireEvent.click(screen.getByRole("button", { name: "Pausa e libera sessioni" }));
    fireEvent.click(screen.getByRole("button", { name: "Pausa e libera" }));
    expect(callbacks.onResumeReleasedBatch).toHaveBeenCalledTimes(1);
    expect(callbacks.onReleaseSessions).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(apiMocks.updateElaborazioneCredential).toHaveBeenCalledWith("token", "one", { active: false }));
    expect(callbacks.onRefreshCredentials).toHaveBeenCalled();
  });

  test("reports single-session release failures and requires a token", async () => {
    const item = credential("one");
    const callbacks = props({ credentials: [item] });
    apiMocks.updateElaborazioneCredential
      .mockRejectedValueOnce(new Error("single release error"))
      .mockRejectedValueOnce("release failed");
    render(<SisterCredentialPool {...callbacks} />);

    fireEvent.click(screen.getByRole("button", { name: "Pausa e libera" }));
    await waitFor(() => expect(callbacks.onTestError).toHaveBeenCalledWith("single release error"));
    await waitFor(() => expect(screen.getByRole("button", { name: "Pausa e libera" })).toBeEnabled());

    fireEvent.click(screen.getByRole("button", { name: "Pausa e libera" }));
    await waitFor(() => expect(callbacks.onTestError).toHaveBeenCalledWith("Errore rilascio sessione SISTER"));

    apiMocks.updateElaborazioneCredential.mockClear();
    authState.token = null;
    await waitFor(() => expect(screen.getByRole("button", { name: "Pausa e libera" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Pausa e libera" }));
    expect(apiMocks.updateElaborazioneCredential).not.toHaveBeenCalled();
  });

  test("reports Error and non-Error failures from an individual test", async () => {
    const callbacks = props({ credentials: [credential("one")] });
    apiMocks.testElaborazioneCredentials.mockRejectedValueOnce(new Error("login rifiutato"));
    const view = render(<SisterCredentialPool {...callbacks} />);

    fireEvent.click(screen.getByRole("button", { name: "Testa" }));
    await waitFor(() => expect(callbacks.onTestError).toHaveBeenCalledWith("login rifiutato"));

    apiMocks.testElaborazioneCredentials.mockRejectedValueOnce("network");
    fireEvent.click(screen.getByRole("button", { name: "Testa" }));
    await waitFor(() => expect(callbacks.onTestError).toHaveBeenCalledWith("Errore test connessione SISTER"));

    authState.token = null;
    fireEvent.click(screen.getByRole("button", { name: "Testa" }));
    expect(apiMocks.testElaborazioneCredentials).toHaveBeenCalledTimes(2);
    view.unmount();
  });

  test("tests the complete pool and renders all terminal result tones", async () => {
    const credentials = [credential("ok"), credential("warning"), credential("failed")];
    apiMocks.testElaborazioneCredentials.mockImplementation(async (_token: string, payload: { credential_id: string }) => {
      if (payload.credential_id === "warning") {
        return result("test-warning", "warning", { authenticated: false, message: "Solo portale raggiungibile" });
      }
      if (payload.credential_id === "failed") {
        return result("test-failed", "failed", {
          status: "failed",
          success: false,
          reachable: false,
          authenticated: false,
          message: "Password non valida",
        });
      }
      return result("test-ok", "ok", { message: "Autenticazione valida" });
    });
    const callbacks = props({ credentials });
    render(<SisterCredentialPool {...callbacks} />);

    fireEvent.click(screen.getByRole("button", { name: "Testa tutte (3)" }));

    expect(await screen.findByText("Verifica del pool completata")).toBeInTheDocument();
    expect(screen.getByText("3/3 completati")).toBeInTheDocument();
    expect(screen.getByText("1 autenticati")).toBeInTheDocument();
    expect(screen.getByText("1 da controllare")).toBeInTheDocument();
    expect(screen.getByText("1 falliti")).toBeInTheDocument();
    expect(screen.getByText("Autenticazione valida")).toBeInTheDocument();
    expect(screen.getByText("Solo portale raggiungibile")).toBeInTheDocument();
    expect(screen.getByText("Password non valida")).toBeInTheDocument();
    expect(callbacks.onBulkBusyChange).toHaveBeenNthCalledWith(1, true);
    expect(callbacks.onBulkBusyChange).toHaveBeenLastCalledWith(false);
    expect(callbacks.onRefreshCredentials).toHaveBeenCalledTimes(1);
    expect(apiMocks.testElaborazioneCredentials.mock.calls.map((call) => call[1])).toEqual([
      { credential_id: "ok" },
      { credential_id: "warning" },
      { credential_id: "failed" },
    ]);
  });

  test("polls a queued bulk test and renders the plural resume action", async () => {
    vi.useFakeTimers();
    const item = credential("one");
    apiMocks.testElaborazioneCredentials.mockResolvedValue(
      result("test-one", "one", { status: "pending", success: null, reachable: null, authenticated: null }),
    );
    apiMocks.getElaborazioneCredentialTest.mockResolvedValue(result("test-one", "one"));
    const callbacks = props({ credentials: [item], releasedBatchesCount: 2 });
    render(<SisterCredentialPool {...callbacks} />);

    expect(screen.getByRole("button", { name: "Riprendi batch (2)" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Testa tutte (1)" }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });

    expect(apiMocks.getElaborazioneCredentialTest).toHaveBeenCalledWith("token", "test-one");
    expect(screen.getByText("Verifica del pool completata")).toBeInTheDocument();
  });

  test("shows queued and running accounts, then cancels the remaining tests", async () => {
    vi.useFakeTimers();
    const credentials = [credential("one"), credential("two")];
    apiMocks.testElaborazioneCredentials.mockResolvedValue(
      result("test-one", "one", { status: "pending", success: null, reachable: null, authenticated: null }),
    );
    const callbacks = props({ credentials });
    render(<SisterCredentialPool {...callbacks} />);

    fireEvent.click(screen.getByRole("button", { name: "Testa tutte (2)" }));
    await act(async () => Promise.resolve());
    expect(screen.getByText("Verifica sequenziale in corso")).toBeInTheDocument();
    expect(screen.getByText("Account corrente: Profilo one. I test non vengono mai eseguiti in parallelo.")).toBeInTheDocument();
    expect(screen.getByText("In coda")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Test in corso" })).toHaveLength(2);

    fireEvent.click(screen.getByRole("button", { name: "Interrompi" }));
    expect(screen.getByText("Interruzione in corso")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Interruzione..." })).toBeDisabled();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });

    expect(screen.getByText("Verifica del pool interrotta")).toBeInTheDocument();
    expect(screen.getAllByText("Non eseguita")).toHaveLength(2);
    expect(screen.getByText("0/2 completati")).toBeInTheDocument();
    expect(apiMocks.getElaborazioneCredentialTest).not.toHaveBeenCalled();
  });

  test("handles refresh failures after a completed bulk run", async () => {
    apiMocks.testElaborazioneCredentials.mockResolvedValue(result("test-one", "one"));
    const errorCallbacks = props({
      credentials: [credential("one")],
      onRefreshCredentials: vi.fn().mockRejectedValue(new Error("refresh fallito")),
    });
    const view = render(<SisterCredentialPool {...errorCallbacks} />);
    fireEvent.click(screen.getByRole("button", { name: "Testa tutte (1)" }));
    await waitFor(() => expect(errorCallbacks.onTestError).toHaveBeenCalledWith("refresh fallito"));
    expect(screen.getByText("Verifica del pool interrotta")).toBeInTheDocument();
    view.unmount();

    const fallbackCallbacks = props({
      credentials: [credential("one")],
      onRefreshCredentials: vi.fn().mockRejectedValue("refresh"),
    });
    render(<SisterCredentialPool {...fallbackCallbacks} />);
    fireEvent.click(screen.getByRole("button", { name: "Testa tutte (1)" }));
    await waitFor(() =>
      expect(fallbackCallbacks.onTestError).toHaveBeenCalledWith("Errore durante la verifica del pool SISTER"),
    );
  });

  test("does not start a bulk run without a token or without credentials", () => {
    const item = credential("one");
    const callbacks = props({ credentials: [item] });
    authState.token = null;
    const view = render(<SisterCredentialPool {...callbacks} />);
    fireEvent.click(screen.getByRole("button", { name: "Testa tutte (1)" }));
    expect(apiMocks.testElaborazioneCredentials).not.toHaveBeenCalled();
    view.unmount();

    authState.token = "token";
    render(<SisterCredentialPool {...props()} />);
    fireEvent.click(screen.getByRole("button", { name: "Testa tutte" }));
    expect(apiMocks.testElaborazioneCredentials).not.toHaveBeenCalled();
  });

  test("avoids state updates when unmounted during individual and bulk tests", async () => {
    const singleDeferred = deferred<ElaborazioneCredentialTestResult>();
    apiMocks.testElaborazioneCredentials.mockReturnValueOnce(singleDeferred.promise);
    const singleCallbacks = props({ credentials: [credential("one")] });
    const singleView = render(<SisterCredentialPool {...singleCallbacks} />);
    fireEvent.click(screen.getByRole("button", { name: "Testa" }));
    singleView.unmount();
    singleDeferred.resolve(result("test-one", "one"));
    await act(async () => Promise.resolve());

    const bulkDeferred = deferred<ElaborazioneCredentialTestResult>();
    apiMocks.testElaborazioneCredentials.mockReturnValueOnce(bulkDeferred.promise);
    const bulkCallbacks = props({ credentials: [credential("one")] });
    const bulkView = render(<SisterCredentialPool {...bulkCallbacks} />);
    fireEvent.click(screen.getByRole("button", { name: "Testa tutte (1)" }));
    bulkView.unmount();
    bulkDeferred.resolve(result("test-one", "one"));
    await act(async () => Promise.resolve());

    expect(singleCallbacks.onTestResult).toHaveBeenCalledTimes(1);
    expect(bulkCallbacks.onRefreshCredentials).not.toHaveBeenCalled();
    expect(bulkCallbacks.onBulkBusyChange).toHaveBeenCalledTimes(1);
  });

  test("ignores a refresh rejection after the pool is unmounted", async () => {
    const refreshDeferred = deferred<void>();
    apiMocks.testElaborazioneCredentials.mockResolvedValue(result("test-one", "one"));
    const callbacks = props({
      credentials: [credential("one")],
      onRefreshCredentials: vi.fn().mockReturnValue(refreshDeferred.promise),
    });
    const view = render(<SisterCredentialPool {...callbacks} />);
    fireEvent.click(screen.getByRole("button", { name: "Testa tutte (1)" }));
    await waitFor(() => expect(callbacks.onRefreshCredentials).toHaveBeenCalledTimes(1));
    view.unmount();
    refreshDeferred.reject(new Error("late refresh"));
    await act(async () => Promise.resolve());

    expect(callbacks.onTestError).not.toHaveBeenCalled();
  });

  test("keeps progress valid when the credential list becomes empty mid-run", async () => {
    const pending = deferred<ElaborazioneCredentialTestResult>();
    apiMocks.testElaborazioneCredentials.mockReturnValue(pending.promise);
    const initialProps = props({ credentials: [credential("one")] });
    const view = render(<SisterCredentialPool {...initialProps} />);
    fireEvent.click(screen.getByRole("button", { name: "Testa tutte (1)" }));
    view.rerender(<SisterCredentialPool {...initialProps} credentials={[]} />);

    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuemax", "0");
    expect(screen.getByText("0/0 completati")).toBeInTheDocument();
    view.unmount();
    pending.resolve(result("test-one", "one"));
    await act(async () => Promise.resolve());
  });
});
