import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import type { CapacitasRefetchCertificatiResult, CapacitasTerreniJob } from "@/types/api";

const mocks = vi.hoisted(() => ({
  token: vi.fn(),
  credentials: vi.fn(),
  terreniJobs: vi.fn(),
  particelleJobs: vi.fn(),
  historyJobs: vi.fn(),
  incassJobs: vi.fn(),
  refetch: vi.fn(),
  authError: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", () => ({
  listCapacitasCredentials: mocks.credentials,
  listCapacitasTerreniJobs: mocks.terreniJobs,
  listCapacitasParticelleSyncJobs: mocks.particelleJobs,
  listCapacitasAnagraficaHistoryJobs: mocks.historyJobs,
  listCapacitasInCassSyncJobs: mocks.incassJobs,
  refetchCapacitasCertificatiEmpty: mocks.refetch,
  isAuthError: mocks.authError,
}));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({
  ElaborazioneWorkspaceModal: () => null,
}));

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<Value>((fulfill, fail) => {
    resolve = fulfill;
    reject = fail;
  });
  return { promise, resolve, reject };
}

async function mountCertificati() {
  const view = render(<ElaborazioniCapacitasWorkspace embedded initialSection="certificati" />);
  await waitFor(() => expect(mocks.credentials).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(screen.getByLabelText("Credenziale")).toHaveValue(""));
  return view;
}

function launch() {
  fireEvent.click(screen.getByRole("button", { name: "Avvia re-fetch" }));
}

function stat(label: string) {
  const card = screen.getByText(label).parentElement;
  if (!card) throw new Error(`Missing rendered stat card: ${label}`);
  return card;
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.token.mockReturnValue("session-token");
  mocks.credentials.mockResolvedValue([]);
  mocks.terreniJobs.mockResolvedValue([]);
  mocks.particelleJobs.mockResolvedValue([]);
  mocks.historyJobs.mockResolvedValue([]);
  mocks.incassJobs.mockResolvedValue([]);
  mocks.refetch.mockResolvedValue({ refetched: 4, remaining_empty: 0 });
  mocks.authError.mockReturnValue(false);
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("Capacitas Certificati re-fetch characterization", () => {
  test("submits the default nullable credential and displays successful result with default empty tone", async () => {
    await mountCertificati();
    expect(screen.getByLabelText("Limite certificati")).toHaveValue(100);
    expect(screen.getByLabelText("Throttle (ms)")).toHaveValue(300);
    expect(screen.queryByText("Ri-fetchati")).not.toBeInTheDocument();
    launch();
    await waitFor(() => expect(mocks.refetch).toHaveBeenCalledExactlyOnceWith("session-token", {
      credential_id: null, limit: 100, throttle_ms: 300,
    }));
    expect(await screen.findByText("Ri-fetchati")).toBeInTheDocument();
    expect(within(stat("Ri-fetchati")).getByText("4")).toBeInTheDocument();
    expect(stat("Ri-fetchati")).toHaveClass("border-emerald-200/70", "bg-emerald-50/80");
    expect(within(stat("Ancora vuoti")).getByText("0")).toBeInTheDocument();
    expect(stat("Ancora vuoti")).toHaveClass("border-white/70", "bg-white/75");
    expect(screen.getByRole("button", { name: "Avvia re-fetch" })).toBeEnabled();
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(1);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(1);
  });

  test("keeps auto-selection for one credential until selected and maps numeric limit and zero throttle", async () => {
    mocks.credentials.mockResolvedValue([{ id: 7, label: "Operatore", username: "user", active: true }]);
    mocks.refetch.mockResolvedValue({ refetched: 2, remaining_empty: 3 });
    await mountCertificati();
    await screen.findByRole("option", { name: "Operatore · user" });
    expect(screen.getByLabelText("Credenziale")).toHaveValue("");
    fireEvent.change(screen.getByLabelText("Credenziale"), { target: { value: "7" } });
    fireEvent.change(screen.getByLabelText("Limite certificati"), { target: { value: "23" } });
    fireEvent.change(screen.getByLabelText("Throttle (ms)"), { target: { value: "0" } });
    launch();
    await waitFor(() => expect(mocks.refetch).toHaveBeenCalledExactlyOnceWith("session-token", {
      credential_id: 7, limit: 23, throttle_ms: 0,
    }));
    await screen.findByText("Ancora vuoti");
    expect(within(stat("Ancora vuoti")).getByText("3")).toBeInTheDocument();
    expect(stat("Ancora vuoti")).toHaveClass("border-amber-200/80", "bg-amber-50/80");
  });

  test("clears a previous result synchronously and freezes only the dispatched payload while awaiting completion", async () => {
    await mountCertificati();
    launch();
    await screen.findByText("Ri-fetchati");
    const pending = deferred<CapacitasRefetchCertificatiResult>();
    mocks.refetch.mockReturnValueOnce(pending.promise);
    launch();
    const busy = screen.getByRole("button", { name: "Re-fetch in corso..." });
    expect(busy).toBeDisabled();
    expect(screen.queryByText("Ri-fetchati")).not.toBeInTheDocument();
    expect(screen.queryByText("Ancora vuoti")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Limite certificati")).toBeEnabled();
    fireEvent.change(screen.getByLabelText("Limite certificati"), { target: { value: "12" } });
    fireEvent.change(screen.getByLabelText("Throttle (ms)"), { target: { value: "500" } });
    fireEvent.click(busy);
    expect(mocks.refetch).toHaveBeenCalledTimes(2);
    expect(mocks.refetch).toHaveBeenLastCalledWith("session-token", {
      credential_id: null, limit: 100, throttle_ms: 300,
    });
    await act(async () => pending.resolve({ refetched: 8, remaining_empty: 1 }));
    expect(within(stat("Ri-fetchati")).getByText("8")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Avvia re-fetch" })).toBeEnabled();
    launch();
    await waitFor(() => expect(mocks.refetch).toHaveBeenLastCalledWith("session-token", {
      credential_id: null, limit: 12, throttle_ms: 500,
    }));
    await screen.findByText("Ri-fetchati");
  });

  test.each([
    { failure: new Error("Credential rejected"), auth: true, message: "Sessione GAIA scaduta. Rientra per riprovare." },
    { failure: { status: 401 }, auth: true, message: "Sessione GAIA scaduta. Rientra per riprovare." },
    { failure: new Error("Portal unavailable"), auth: false, message: "Portal unavailable" },
    { failure: "portal rejection", auth: false, message: "Errore durante il re-fetch." },
  ])("shows $message on rejection and clears it before a deferred retry", async ({ failure, auth, message }) => {
    const first = deferred<CapacitasRefetchCertificatiResult>();
    mocks.refetch.mockReturnValueOnce(first.promise);
    mocks.authError.mockImplementation((error) => error === failure && auth);
    await mountCertificati();
    launch();
    expect(screen.getByRole("button", { name: "Re-fetch in corso..." })).toBeDisabled();
    await act(async () => first.reject(failure));
    expect(screen.getByText(message)).toBeInTheDocument();
    expect(mocks.authError).toHaveBeenCalledExactlyOnceWith(failure);
    expect(screen.queryByText("Ri-fetchati")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Avvia re-fetch" })).toBeEnabled();
    const retry = deferred<CapacitasRefetchCertificatiResult>();
    mocks.refetch.mockReturnValueOnce(retry.promise);
    mocks.token.mockReturnValue("renewed-token");
    launch();
    expect(screen.queryByText(message)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Re-fetch in corso..." })).toBeDisabled();
    expect(mocks.refetch).toHaveBeenLastCalledWith("renewed-token", {
      credential_id: null, limit: 100, throttle_ms: 300,
    });
    await act(async () => retry.resolve({ refetched: 1, remaining_empty: 0 }));
    expect(within(stat("Ri-fetchati")).getByText("1")).toBeInTheDocument();
    expect(screen.queryByText(message)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Avvia re-fetch" })).toBeEnabled();
  });

  test("token loss before dispatch preserves previous result and a restored token permits another run", async () => {
    await mountCertificati();
    launch();
    await screen.findByText("Ri-fetchati");
    mocks.token.mockReturnValue(null);
    launch();
    expect(mocks.refetch).toHaveBeenCalledTimes(1);
    expect(within(stat("Ri-fetchati")).getByText("4")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Avvia re-fetch" })).toBeEnabled();
    mocks.token.mockReturnValue("restored-token");
    launch();
    await waitFor(() => expect(mocks.refetch).toHaveBeenLastCalledWith("restored-token", {
      credential_id: null, limit: 100, throttle_ms: 300,
    }));
    await screen.findByText("Ri-fetchati");
  });

  test("missing token at mount dispatches no API work and restoration permits the explicit command", async () => {
    mocks.token.mockReturnValue(null);
    render(<ElaborazioniCapacitasWorkspace embedded initialSection="certificati" />);
    await act(async () => {});
    launch();
    expect(mocks.credentials).not.toHaveBeenCalled();
    for (const list of [mocks.terreniJobs, mocks.particelleJobs, mocks.historyJobs, mocks.incassJobs]) {
      expect(list).not.toHaveBeenCalled();
    }
    expect(mocks.refetch).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Avvia re-fetch" })).toBeEnabled();
    mocks.token.mockReturnValue("restored-token");
    launch();
    await screen.findByText("Ri-fetchati");
    expect(mocks.refetch).toHaveBeenCalledExactlyOnceWith("restored-token", {
      credential_id: null, limit: 100, throttle_ms: 300,
    });
  });

  test("an already-dispatched request can finish after token loss without changing its credentials", async () => {
    const pending = deferred<CapacitasRefetchCertificatiResult>();
    mocks.refetch.mockReturnValueOnce(pending.promise);
    await mountCertificati();
    launch();
    mocks.token.mockReturnValue(null);
    await act(async () => pending.resolve({ refetched: 6, remaining_empty: 0 }));
    expect(within(stat("Ri-fetchati")).getByText("6")).toBeInTheDocument();
    expect(mocks.refetch).toHaveBeenCalledExactlyOnceWith("session-token", {
      credential_id: null, limit: 100, throttle_ms: 300,
    });
    expect(screen.getByRole("button", { name: "Avvia re-fetch" })).toBeEnabled();
  });

  test("real job polling remains independent of a busy re-fetch and is cleaned up on unmount", async () => {
    vi.useFakeTimers();
    mocks.terreniJobs.mockResolvedValue([{
      id: 1, status: "pending", payload_json: { items: [] }, result_json: null,
      created_at: "2026-10-08T12:00:00Z", started_at: null, completed_at: null, error_detail: null,
      updated_at: "2026-10-08T12:00:00Z", credential_id: null, requested_by_user_id: null, mode: "batch",
    } satisfies CapacitasTerreniJob]);
    const pending = deferred<CapacitasRefetchCertificatiResult>();
    mocks.refetch.mockReturnValueOnce(pending.promise);
    const view = render(<ElaborazioniCapacitasWorkspace embedded initialSection="certificati" />);
    await act(async () => {});
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(1);
    launch();
    await act(async () => vi.advanceTimersByTimeAsync(15000));
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(2);
    expect(mocks.refetch).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Re-fetch in corso..." })).toBeDisabled();
    await act(async () => pending.resolve({ refetched: 3, remaining_empty: 0 }));
    expect(within(stat("Ri-fetchati")).getByText("3")).toBeInTheDocument();
    view.unmount();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(45000);
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(2);
    expect(mocks.refetch).toHaveBeenCalledTimes(1);
  });
});
