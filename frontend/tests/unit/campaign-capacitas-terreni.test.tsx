import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import type { CapacitasTerreniBatchResult, CapacitasTerreniJob } from "@/types/api";

const mocks = vi.hoisted(() => ({
  token: vi.fn(), credentials: vi.fn(), terreniJobs: vi.fn(), particelleJobs: vi.fn(),
  historyJobs: vi.fn(), incassJobs: vi.fn(), rerun: vi.fn(), remove: vi.fn(), authError: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", () => ({
  listCapacitasCredentials: mocks.credentials,
  listCapacitasTerreniJobs: mocks.terreniJobs,
  listCapacitasParticelleSyncJobs: mocks.particelleJobs,
  listCapacitasAnagraficaHistoryJobs: mocks.historyJobs,
  listCapacitasInCassSyncJobs: mocks.incassJobs,
  rerunCapacitasTerreniJob: mocks.rerun,
  deleteCapacitasTerreniJob: mocks.remove,
  isAuthError: mocks.authError,
}));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({
  ElaborazioneWorkspaceModal: () => null,
}));

function job(overrides: Partial<CapacitasTerreniJob> = {}): CapacitasTerreniJob {
  return {
    id: 1, credential_id: null, requested_by_user_id: null, status: "succeeded", mode: "batch",
    payload_json: { items: [] }, result_json: null, error_detail: null,
    started_at: null, completed_at: null, created_at: "2026-10-08T12:00:00Z",
    updated_at: "2026-10-08T12:00:00Z", ...overrides,
  };
}

function result(overrides: Partial<CapacitasTerreniBatchResult> = {}): CapacitasTerreniBatchResult {
  return {
    items: [], processed_items: 0, failed_items: 0, total_rows: 0, imported_rows: 0,
    imported_certificati: 0, imported_details: 0, linked_units: 0, linked_occupancies: 0,
    ...overrides,
  };
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<Value>((fulfill, fail) => { resolve = fulfill; reject = fail; });
  return { promise, resolve, reject };
}

function row(id: number) {
  const element = screen.getByText(`#${id}`).closest("tr");
  if (!element) throw new Error(`Missing rendered job row ${id}`);
  return within(element);
}

function refresh() {
  fireEvent.click(screen.getByRole("button", { name: "Aggiorna job" }));
}

async function mount(jobs: CapacitasTerreniJob[] = []) {
  mocks.terreniJobs.mockResolvedValue(jobs);
  const view = render(<ElaborazioniCapacitasWorkspace embedded initialSection="terreni" />);
  await waitFor(() => expect(screen.getByRole("button", { name: "Aggiorna job" })).toBeEnabled());
  if (jobs.length) await screen.findByText(`#${jobs[0].id}`);
  else await screen.findByText("Nessun job registrato");
  return view;
}

async function mountWithTimers(jobs: CapacitasTerreniJob[]) {
  vi.useFakeTimers();
  mocks.terreniJobs.mockResolvedValue(jobs);
  const view = render(<ElaborazioniCapacitasWorkspace embedded initialSection="terreni" />);
  await act(async () => {});
  return view;
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.token.mockReturnValue("session-token");
  mocks.credentials.mockResolvedValue([]);
  mocks.terreniJobs.mockResolvedValue([]);
  mocks.particelleJobs.mockResolvedValue([]);
  mocks.historyJobs.mockResolvedValue([]);
  mocks.incassJobs.mockResolvedValue([]);
  mocks.rerun.mockResolvedValue(job({ status: "pending" }));
  mocks.remove.mockResolvedValue(undefined);
  mocks.authError.mockReturnValue(false);
});

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.useRealTimers(); });

describe("Capacitas Terreni monitor and actions characterization", () => {
  test.each(["succeeded", "completed_with_errors", "failed"])(
    "polling pending → %s opens completion once while another job remains active",
    async (status) => {
      const pending = job({ status: "pending" });
      const stillActive = job({ id: 2, status: "processing" });
      await mountWithTimers([pending, stillActive]);
      mocks.terreniJobs.mockResolvedValue([
        job({ status, error_detail: status === "failed" ? null : "Terminal diagnostic" }), stillActive,
      ]);
      await act(async () => vi.advanceTimersByTimeAsync(15000));
      expect(screen.getByText("Report elaborazione Terreni")).toBeInTheDocument();
      expect(screen.getByText("Job #1 completato")).toBeInTheDocument();
      if (status === "failed") {
        expect(screen.queryByText("Terminal diagnostic")).not.toBeInTheDocument();
        expect(screen.queryByText("Item processati")).not.toBeInTheDocument();
      } else {
        expect(screen.getAllByText("Terminal diagnostic")).toHaveLength(2);
      }
      fireEvent.click(screen.getByText("Chiudi", { selector: "button" }));
      expect(screen.queryByText("Report elaborazione Terreni")).not.toBeInTheDocument();
      await act(async () => vi.advanceTimersByTimeAsync(15000));
      expect(mocks.terreniJobs).toHaveBeenCalledTimes(3);
      expect(screen.queryByText("Report elaborazione Terreni")).not.toBeInTheDocument();
    },
  );

  test("manual refresh shows loading and does not open a completion notification", async () => {
    await mount([job({ status: "pending" })]);
    const loading = deferred<CapacitasTerreniJob[]>();
    mocks.terreniJobs.mockReturnValueOnce(loading.promise);
    refresh();
    expect(screen.getByText("Caricamento job Terreni...")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aggiorna job" })).toBeDisabled();
    await act(async () => loading.resolve([job({ status: "succeeded" })]));
    expect(row(1).getByText("Completato")).toBeInTheDocument();
    expect(screen.queryByText("Report elaborazione Terreni")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aggiorna job" })).toBeEnabled();
  });

  test("silent failure is suppressed, silent recovery preserves manual error, manual success clears it", async () => {
    await mountWithTimers([job({ status: "processing" })]);
    mocks.terreniJobs.mockRejectedValueOnce(new Error("Silent network outage"));
    await act(async () => vi.advanceTimersByTimeAsync(15000));
    expect(screen.queryByText("Silent network outage")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aggiorna job" })).toBeEnabled();
    mocks.terreniJobs.mockRejectedValueOnce(new Error("Manual network outage"));
    refresh();
    await act(async () => {});
    expect(screen.getByText("Manual network outage")).toBeInTheDocument();
    await act(async () => vi.advanceTimersByTimeAsync(15000));
    expect(screen.getByText("Manual network outage")).toBeInTheDocument();
    refresh();
    await act(async () => {});
    expect(screen.queryByText("Manual network outage")).not.toBeInTheDocument();
    expect(row(1).getByText("In corso")).toBeInTheDocument();
  });

  test.each([
    [new Error("Initial network failure"), "Initial network failure"],
    ["untyped failure", "Errore caricamento job Terreni"],
  ])("initial monitor failure %s recovers through explicit refresh", async (failure, message) => {
    mocks.terreniJobs.mockRejectedValueOnce(failure);
    render(<ElaborazioniCapacitasWorkspace embedded initialSection="terreni" />);
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aggiorna job" })).toBeEnabled();
    mocks.terreniJobs.mockResolvedValue([job()]);
    refresh();
    await screen.findByText("#1");
    expect(screen.queryByText(message)).not.toBeInTheDocument();
  });

  test.each([new Error("Expired GAIA"), { status: 401 }])(
    "auth failure during real polling stops it until an explicit recovered refresh",
    async (failure) => {
      await mountWithTimers([job({ status: "processing" })]);
      mocks.authError.mockImplementation((error) => error === failure);
      mocks.terreniJobs.mockRejectedValueOnce(failure);
      await act(async () => vi.advanceTimersByTimeAsync(15000));
      expect(screen.getByText("Sessione GAIA scaduta: il monitor Terreni si ferma, ma i job backend gia avviati possono continuare.")).toBeInTheDocument();
      expect(screen.getByText("Rientra in GAIA per riprendere il polling del monitor Terreni.")).toBeInTheDocument();
      await act(async () => vi.advanceTimersByTimeAsync(45000));
      expect(mocks.terreniJobs).toHaveBeenCalledTimes(2);
      mocks.token.mockReturnValue("renewed-token");
      refresh();
      await act(async () => {});
      expect(mocks.terreniJobs).toHaveBeenLastCalledWith("renewed-token");
      expect(screen.queryByText(/Sessione GAIA scaduta: il monitor Terreni/)).not.toBeInTheDocument();
      expect(screen.getByText("Rientra in GAIA per riprendere il polling del monitor Terreni.")).toBeInTheDocument();
      await act(async () => vi.advanceTimersByTimeAsync(15000));
      expect(mocks.terreniJobs).toHaveBeenCalledTimes(4);
    },
  );

  test("token loss stops active polling before API dispatch and recovery re-enables it", async () => {
    await mountWithTimers([job({ status: "queued_resume" })]);
    mocks.token.mockReturnValue(null);
    await act(async () => vi.advanceTimersByTimeAsync(15000));
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/Sessione GAIA scaduta: il monitor Terreni/)).toBeInTheDocument();
    await act(async () => vi.advanceTimersByTimeAsync(30000));
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(1);
    mocks.token.mockReturnValue("restored-token");
    refresh();
    await act(async () => {});
    expect(screen.queryByText(/Sessione GAIA scaduta: il monitor Terreni/)).not.toBeInTheDocument();
    await act(async () => vi.advanceTimersByTimeAsync(15000));
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(3);
  });

  test("hidden-document ticks skip, visibility recovery runs once, slow polling does not overlap and unmount cleans up", async () => {
    const view = await mountWithTimers([job({ status: "pending" })]);
    const visibility = vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
    await act(async () => vi.advanceTimersByTimeAsync(15000));
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(1);
    const loading = deferred<CapacitasTerreniJob[]>();
    mocks.terreniJobs.mockReturnValueOnce(loading.promise);
    visibility.mockReturnValue("visible");
    await act(async () => document.dispatchEvent(new Event("visibilitychange")));
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(2);
    expect(screen.queryByText("Caricamento job Terreni...")).not.toBeInTheDocument();
    await act(async () => vi.advanceTimersByTimeAsync(45000));
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(2);
    await act(async () => loading.resolve([job({ status: "pending" })]));
    await act(async () => vi.advanceTimersByTimeAsync(15000));
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(3);
    view.unmount();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(45000);
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(3);
  });

  test("rerun awaits its API before refreshing and holds busy through the refresh", async () => {
    await mount([job(), job({ id: 2 })]);
    const rerunning = deferred<CapacitasTerreniJob>();
    const loading = deferred<CapacitasTerreniJob[]>();
    mocks.rerun.mockReturnValueOnce(rerunning.promise);
    mocks.terreniJobs.mockReturnValueOnce(loading.promise);
    fireEvent.click(row(1).getByRole("button", { name: "Rilancia" }));
    expect(mocks.rerun).toHaveBeenCalledExactlyOnceWith("session-token", 1);
    expect(row(1).getByRole("button", { name: "Rerun..." })).toBeDisabled();
    expect(row(2).getByRole("button", { name: "Rilancia" })).toBeEnabled();
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(1);
    await act(async () => rerunning.resolve(job({ status: "pending" })));
    expect(screen.getByText("Job #1 rilanciato.")).toBeInTheDocument();
    expect(screen.getByText("Caricamento job Terreni...")).toBeInTheDocument();
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(2);
    await act(async () => loading.resolve([job({ status: "pending" }), job({ id: 2 })]));
    expect(row(1).getByRole("button", { name: "Rilancia" })).toBeEnabled();
    expect(row(1).getByRole("button", { name: "Elimina" })).toBeDisabled();
  });

  test("delete keeps the row until success, removes only its target and does not refresh the list", async () => {
    await mount([job(), job({ id: 2 })]);
    const removing = deferred<void>();
    mocks.remove.mockReturnValueOnce(removing.promise);
    fireEvent.click(row(1).getByRole("button", { name: "Elimina" }));
    expect(mocks.remove).toHaveBeenCalledExactlyOnceWith("session-token", 1);
    expect(row(1).getByRole("button", { name: "Elimina..." })).toBeDisabled();
    expect(row(2).getByRole("button", { name: "Elimina" })).toBeEnabled();
    await act(async () => removing.resolve());
    expect(screen.queryByText("#1")).not.toBeInTheDocument();
    expect(screen.getByText("#2")).toBeInTheDocument();
    expect(screen.getByText("Job #1 eliminato.")).toBeInTheDocument();
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(1);
  });

  test.each([
    ["rerun", new Error("Rerun rejected"), "Rerun rejected"],
    ["rerun", "rejected", "Errore rerun job Terreni"],
    ["delete", new Error("Delete rejected"), "Delete rejected"],
    ["delete", "rejected", "Errore eliminazione job Terreni"],
  ])("%s failure restores action and retains the row: %s", async (action, failure, message) => {
    await mount([job()]);
    const command = action === "rerun" ? mocks.rerun : mocks.remove;
    command.mockRejectedValueOnce(failure);
    const button = action === "rerun" ? "Rilancia" : "Elimina";
    fireEvent.click(row(1).getByRole("button", { name: button }));
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(row(1).getByRole("button", { name: button })).toBeEnabled();
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(1);
    fireEvent.click(row(1).getByRole("button", { name: button }));
    await waitFor(() => expect(command).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.queryByText(message)).not.toBeInTheDocument());
  });

  test.each(["rerun", "delete"])("token loss before %s prevents its API dispatch and leaves action enabled", async (action) => {
    await mount([job()]);
    mocks.token.mockReturnValue(null);
    const button = action === "rerun" ? "Rilancia" : "Elimina";
    fireEvent.click(row(1).getByRole("button", { name: button }));
    expect(mocks.rerun).not.toHaveBeenCalled();
    expect(mocks.remove).not.toHaveBeenCalled();
    expect(row(1).getByRole("button", { name: button })).toBeEnabled();
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(1);
  });

  test("missing token at mount leaves the monitor recoverable by explicit refresh", async () => {
    mocks.token.mockReturnValue(null);
    render(<ElaborazioniCapacitasWorkspace embedded initialSection="terreni" />);
    expect(await screen.findByText(/Sessione GAIA scaduta: il monitor Terreni/)).toBeInTheDocument();
    expect(mocks.terreniJobs).not.toHaveBeenCalled();
    mocks.token.mockReturnValue("restored-token");
    mocks.terreniJobs.mockResolvedValue([job()]);
    refresh();
    await screen.findByText("#1");
    expect(mocks.terreniJobs).toHaveBeenCalledExactlyOnceWith("restored-token");
    expect(screen.queryByText(/Sessione GAIA scaduta: il monitor Terreni/)).not.toBeInTheDocument();
  });

  test("report shows counters and failed items only, with labels/search keys/error fallbacks and close actions", async () => {
    const item = { total_rows: 1, imported_rows: 0, imported_certificati: 0, imported_details: 0, linked_units: 0, linked_occupancies: 0 };
    const summary = result({
      processed_items: 3, failed_items: 2, total_rows: 6, imported_rows: 4, linked_units: 3,
      linked_occupancies: 2, imported_certificati: 1, imported_details: 4,
      items: [
        { ...item, search_key: "URAS/1/680", label: "Failed labeled parcel", ok: false, error: "Portal diagnostic" },
        { ...item, search_key: "URAS/2/1695", label: null, ok: false, error: null },
        {
          ...item, search_key: "URAS/3/10", label: "Successful parcel", ok: true,
          total_rows: 4, imported_rows: 4, linked_units: 3, linked_occupancies: 2,
          imported_certificati: 1, imported_details: 4,
        },
      ],
    });
    await mount([job({ status: "completed_with_errors", result_json: summary })]);
    fireEvent.click(row(1).getByRole("button", { name: "Dettagli" }));
    expect(screen.getByText("Report elaborazione Terreni")).toBeInTheDocument();
    for (const [label, value] of [["Item processati", 3], ["Righe importate", 4], ["Unità linkate", 3], ["Occupazioni linkate", 2], ["Certificati importati", 1], ["Dettagli importati", 4]] as const) {
      const card = screen.getByText(label).parentElement;
      expect(card).not.toBeNull();
      expect(within(card!).getByText(String(value))).toBeInTheDocument();
    }
    fireEvent.click(screen.getByRole("button", { name: "Vedi 2 errori" }));
    expect(screen.queryByText("Report elaborazione Terreni")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "2 item con errore" })).toBeInTheDocument();
    for (const text of ["Failed labeled parcel", "URAS/1/680", "URAS/2/1695", "Portal diagnostic", "Errore sconosciuto"]) {
      expect(screen.getByText(text)).toBeInTheDocument();
    }
    expect(screen.queryByText("Successful parcel")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Chiudi", { selector: "button" }));
    expect(screen.queryByRole("heading", { name: "2 item con errore" })).not.toBeInTheDocument();
    fireEvent.click(row(1).getByRole("button", { name: "Errori" }));
    fireEvent.click(screen.getByLabelText("Chiudi"));
    expect(screen.queryByText("Portal diagnostic")).not.toBeInTheDocument();
    fireEvent.click(row(1).getByRole("button", { name: "Dettagli" }));
    fireEvent.click(screen.getByLabelText("Chiudi"));
    expect(screen.queryByText("Report elaborazione Terreni")).not.toBeInTheDocument();
  });

  test("an open report follows current job results and retains its snapshot after target deletion", async () => {
    await mount([job({ result_json: result() })]);
    fireEvent.click(row(1).getByRole("button", { name: "Dettagli" }));
    mocks.terreniJobs.mockResolvedValue([job({ result_json: result({ processed_items: 4 }) })]);
    refresh();
    await waitFor(() => expect(row(1).getByText("4 item · 0 righe · 0 unità")).toBeInTheDocument());
    expect(within(screen.getByText("Item processati").parentElement!).getByText("4")).toBeInTheDocument();
    fireEvent.click(row(1).getByRole("button", { name: "Elimina" }));
    await waitFor(() => expect(screen.queryByText("#1")).not.toBeInTheDocument());
    expect(screen.getByText("Report elaborazione Terreni")).toBeInTheDocument();
    expect(within(screen.getByText("Item processati").parentElement!).getByText("0")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Chiudi", { selector: "button" }));
    expect(screen.queryByText("Report elaborazione Terreni")).not.toBeInTheDocument();
  });

  test("open errors modal follows refreshed empty or unavailable results without fabricated state", async () => {
    const failed = result({ processed_items: 1, failed_items: 1, items: [{
      search_key: "URAS/1/680", ok: false, total_rows: 0, imported_rows: 0,
      imported_certificati: 0, imported_details: 0, linked_units: 0, linked_occupancies: 0,
    }] });
    await mount([job({ result_json: failed })]);
    fireEvent.click(row(1).getByRole("button", { name: "Errori" }));
    mocks.terreniJobs.mockResolvedValue([job({ result_json: result() })]);
    refresh();
    expect(await screen.findByText("Nessun errore da mostrare.")).toBeInTheDocument();
    mocks.terreniJobs.mockResolvedValue([job({ result_json: null })]);
    refresh();
    await waitFor(() => expect(row(1).queryByRole("button", { name: "Dettagli" })).not.toBeInTheDocument());
    expect(screen.getByText("Nessun errore da mostrare.")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Chiudi", { selector: "button" }));
  });

  test("status labels, execution progress counts, scheduling detail and dates preserve current display", async () => {
    const statuses = ["pending", "processing", "queued_resume", "succeeded", "completed_with_errors", "failed", "cancelling", "cancelled", "unknown"];
    const labels = ["In attesa", "In corso", "Ripresa pianificata", "Completato", "Con errori", "Fallito", "Fermando…", "Annullato", "In attesa"];
    const records = statuses.map((status, index) => job({
      id: index + 1, status, created_at: index === 0 ? "invalid-date" : "2026-10-08T12:00:00Z",
      result_json: status === "queued_resume" ? result({ processed_items: 2, imported_rows: 3, linked_units: 4, parallel_workers: 2, speed_multiplier: 2, throttle_ms: 0 }) : null,
    }));
    await mount(records);
    records.forEach((record, index) => {
      expect(row(record.id).getByText(labels[index])).toBeInTheDocument();
      expect(row(record.id).getByRole("button", { name: "Elimina" })).toHaveProperty("disabled", index < 3);
    });
    expect(row(1).getByText("invalid-date")).toBeInTheDocument();
    expect(row(2).getByText(new Date("2026-10-08T12:00:00Z").toLocaleString("it-IT"))).toBeInTheDocument();
    expect(row(2).getByText(/start —/)).toHaveTextContent("end —");
    expect(row(3).getByText("2 item · 3 righe · 4 unità")).toBeInTheDocument();
    expect(row(3).getByText("worker 2 · velocita x2 · pausa 0ms · resume automatico pianificato")).toBeInTheDocument();
    fireEvent.click(row(3).getByRole("button", { name: "Dettagli" }));
    expect(screen.getByText("Job #3 in corso")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Vedi .* errori/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Chiudi", { selector: "button" }));
  });

  test.each([null, [], {}, { processed_items: "wrong", failed_items: 0, imported_rows: 0, linked_units: 0 }])(
    "unavailable or invalid result %j stays a diagnostic row, not a crashing result report",
    async (result_json) => {
      await mount([job({ status: "failed", result_json, error_detail: "Job-level failure" })]);
      expect(row(1).getByText("Job-level failure")).toBeInTheDocument();
      expect(row(1).queryByRole("button", { name: "Dettagli" })).not.toBeInTheDocument();
      expect(row(1).queryByRole("button", { name: "Errori" })).not.toBeInTheDocument();
    },
  );
});
