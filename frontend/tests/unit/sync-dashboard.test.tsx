import { act, cleanup, fireEvent, render, renderHook, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import * as api from "@/lib/api";
import { ApiError } from "@/lib/api/core";
import { catastoGisGetLatestAdeWfsRunStatus } from "@/lib/api/catasto";
import { getVehicleAutodocSyncStatus } from "@/features/operazioni/api/client";
import { getStoredAccessToken } from "@/lib/auth";
import { jobSnapshot, latestSync, matchesSyncFilter, resultMetrics, syncCounts, syncError, syncStatus, syncSummary } from "@/lib/sync-dashboard-model";
import { SYNC_SERVICES } from "@/lib/sync-dashboard-services";
import { SyncServiceCard } from "@/components/elaborazioni/sync-service-card";
import { SyncServiceDetails } from "@/components/elaborazioni/sync-service-details";
import { SyncSchedules } from "@/components/elaborazioni/sync-schedules";
import { useSyncDashboard } from "@/components/elaborazioni/use-sync-dashboard";
import ElaborazioniPage from "@/app/elaborazioni/page";

vi.mock("@/lib/api", () => ({
  listCapacitasParticelleSyncJobs: vi.fn(), listCapacitasInCassSyncJobs: vi.fn(),
  listCapacitasAnagraficaHistoryJobs: vi.fn(), listCapacitasTerreniJobs: vi.fn(), listCapacitasDomandeIrrigueSyncJobs: vi.fn(),
  listPostaOnlineRegisteredMailJobs: vi.fn(), listPresenzeSyncJobs: vi.fn(), getElaborazioneBatches: vi.fn(),
  getSyncJobs: vi.fn(), getBonificaSyncStatus: vi.fn(), getGateMobileSyncStatus: vi.fn(),
  getElaborazioneRuoloAutoSyncStatus: vi.fn(), getElaborazioneAnprSummary: vi.fn(),
  getElaborazioneAutoJobControls: vi.fn(), updateElaborazioneAutoJobControl: vi.fn(),
}));
vi.mock("@/lib/api/catasto", () => ({ catastoGisGetLatestAdeWfsRunStatus: vi.fn() }));
vi.mock("@/features/operazioni/api/client", () => ({ getVehicleAutodocSyncStatus: vi.fn() }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: vi.fn() }));
vi.mock("@/components/app/protected-page", () => ({ ProtectedPage: ({ children }: { children: ReactNode }) => <main>{children}</main> }));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({
  NativeWorkspaceRenderer: ({ href, onNavigate }: { href: string; onNavigate: (href: string) => void }) =>
    <div>Monitor: {href}<button onClick={() => onNavigate("/elaborazioni/batches/123")}>Apri lavorazione</button></div>,
}));
vi.mock("next/dynamic", async () => {
  const { lazy, Suspense } = await import("react");
  return { default: (loader: () => Promise<React.ComponentType>, options: { loading: React.ComponentType }) => {
    const Content = lazy(async () => ({ default: await loader() }));
    const Loading = options.loading;
    return function LazyContent(props: object) { return <Suspense fallback={<Loading />}><Content {...props} /></Suspense>; };
  } };
});

const listNames = ["listCapacitasParticelleSyncJobs", "listCapacitasInCassSyncJobs", "listCapacitasAnagraficaHistoryJobs",
  "listCapacitasTerreniJobs", "listCapacitasDomandeIrrigueSyncJobs", "listPostaOnlineRegisteredMailJobs", "listPresenzeSyncJobs", "getElaborazioneBatches", "getSyncJobs"] as const;
const time = "2026-09-15T10:00:00Z";
const job = { status: "completed", created_at: time, started_at: time, completed_at: time, finished_at: time,
  error_detail: null, result_json: { processed_subjects: 12, notices_synced: 23 }, period_start: "2026-09-01", period_end: "2026-09-15",
  records_imported: 10, records_skipped: 2, records_errors: 0, total_items: 4, completed_items: 3, failed_items: 1,
  current_operation: "Download", persisted_users: 2, persisted_groups: 3, persisted_shares: 4, persisted_permission_entries: 5 };
const control = { key: "sync", label: "Sync giornaliera", description: "Ogni giorno", enabled: true, detail: "Ore 08:00", management_href: "/elaborazioni/bonifica" };

function resolveMock(name: keyof typeof api, value: unknown) {
  vi.mocked(api[name]).mockResolvedValue(value as never);
}
async function load(id: string) { return SYNC_SERVICES.find((service) => service.id === id)!.load("token"); }

beforeEach(() => {
  vi.resetAllMocks();
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
  vi.mocked(getStoredAccessToken).mockReturnValue("token");
  for (const name of listNames) resolveMock(name, []);
  resolveMock("getBonificaSyncStatus", { entities: {} });
  resolveMock("getGateMobileSyncStatus", { sync_enabled: false, gateway_configured: false, token_configured: false, last_run: null });
  resolveMock("getElaborazioneRuoloAutoSyncStatus", { config: { enabled: false, batch_size: 10, last_planner_at: null, last_error_message: null }, running_batch: null, last_batch: null });
  resolveMock("getElaborazioneAnprSummary", { recent_runs: [], calls_today: 0, effective_daily_limit: 100 });
  resolveMock("getElaborazioneAutoJobControls", []);
  vi.mocked(getVehicleAutodocSyncStatus).mockResolvedValue(null);
  vi.mocked(catastoGisGetLatestAdeWfsRunStatus).mockRejectedValue(new ApiError("Nessun run", null, 404));
});
afterEach(() => { cleanup(); vi.useRealTimers(); });

describe("normalizzazione", () => {
  it("riassume tutti i flussi dando precedenza ai problemi e filtra senza nascondere errori", () => {
    const state = { snapshots: [], updatedAt: null, error: null };
    expect(matchesSyncFilter(undefined, "all")).toBe(true);
    expect(matchesSyncFilter(undefined, "active")).toBe(false);
    expect(matchesSyncFilter(state, "attention")).toBe(false);
    expect(syncSummary().label).toBe("Caricamento stato...");
    expect(syncSummary(state).label).toBe("Nessuna esecuzione");
    expect(syncSummary({ ...state, error: "offline" }).label).toBe("Da verificare");
    const multiple = { ...state, snapshots: [
      { status: "completed", metrics: [], startedAt: "2026-01-01" },
      { status: "running", metrics: [], startedAt: time },
      { status: "idle", metrics: [] },
    ] };
    expect(syncSummary(multiple)).toMatchObject({ label: "In corso / in coda", lastStarted: time });
    expect(matchesSyncFilter(multiple, "active")).toBe(true);
    expect(syncSummary({ ...state, snapshots: [{ status: "completed", metrics: [] }] }).label).toBe("Completato");
    expect(syncSummary({ ...multiple, snapshots: multiple.snapshots.filter((item) => item.status !== "running") }).label).toBe("Nessun flusso attivo");
    expect(syncStatus("succeeded").label).toBe("Completato");
    multiple.snapshots.push({ status: "failed", metrics: [], startedAt: "2026-08-01" });
    expect(syncSummary(multiple).label).toBe("Da verificare");
    expect(matchesSyncFilter(multiple, "attention")).toBe(true);
  });
  it("ordina per creazione senza mutare i job e non confonde aggiornamento e ultimo sync", () => {
    const old = { ...job, created_at: "2026-09-01T10:00:00Z", updated_at: "2026-09-30T10:00:00Z" };
    const jobs = [old, job];
    expect(latestSync(jobs)).toBe(job);
    expect(jobs[0]).toBe(old);
    expect(latestSync([])).toBeUndefined();
    expect(jobSnapshot(undefined)).toEqual([]);
    expect(jobSnapshot({ status: "pending", created_at: time })).toEqual([{ status: "pending", startedAt: time, finishedAt: undefined, error: undefined, metrics: [] }]);
    expect(jobSnapshot({ ...job, completed_at: null })[0].finishedAt).toBe(time);
  });
  it("traduce stati noti e conserva quelli sconosciuti", () => {
    expect(syncStatus("running").label).toBe("In corso");
    expect(syncStatus("failed").label).toBe("Fallito");
    expect(syncStatus("completed").label).toBe("Completato");
    expect(syncStatus("unknown").label).toBe("unknown");
    expect(syncCounts({})).toEqual({ active: 0, attention: 0 });
    expect(syncCounts({ a: { snapshots: [{ status: "running", metrics: [] }], updatedAt: time, error: null },
      b: { snapshots: [{ status: "failed", metrics: [] }], updatedAt: time, error: null },
      c: { snapshots: [], updatedAt: null, error: "offline" },
      d: { snapshots: [{ status: "completed", error: "partial", metrics: [] }], updatedAt: time, error: null },
      e: { snapshots: [{ status: "completed", metrics: [] }], updatedAt: time, error: null } })).toEqual({ active: 1, attention: 3 });
  });
  it("mostra solo contatori riconosciuti e numerici", () => {
    for (const value of [null, [], "text", 1]) expect(resultMetrics(value)).toEqual([]);
    expect(resultMetrics({ notices_synced: 4, processed_subjects: "invalid", secret: "hidden" })).toEqual([{ label: "Avvisi sincronizzati", value: 4 }]);
    expect(syncError(new Error("offline"))).toBe("offline");
    expect(syncError(null)).toBe("Impossibile leggere lo stato del servizio");
  });
});

describe("servizi", () => {
  it("gestisce tutti i servizi senza esecuzioni", async () => {
    for (const service of SYNC_SERVICES) expect(await service.load("token")).toBeInstanceOf(Array);
  });
  it("legge i job di ogni integrazione e limita inCass a uno", async () => {
    for (const name of listNames) resolveMock(name, [{ ...job, created_at: "2026-01-01T00:00:00Z" }, job]);
    for (const service of SYNC_SERVICES.slice(0, listNames.length)) {
      const rows = await service.load("token");
      expect(rows).toHaveLength(1);
      expect(rows[0].startedAt).toBe(time);
    }
    expect(api.listCapacitasInCassSyncJobs).toHaveBeenCalledWith("token", { limit: 1 });
    expect((await load("incass"))[0].metrics).toContainEqual({ label: "Avvisi sincronizzati", value: 23 });
    resolveMock("getElaborazioneBatches", [{ ...job, current_operation: null }]);
    expect((await load("visure"))[0].metrics).toContainEqual({ label: "Operazione", value: "In attesa" });
  });
  it("mostra separatamente tutte le entita WhiteCompany, anche senza contatori", async () => {
    resolveMock("getBonificaSyncStatus", { entities: { a: { entity: "mezzi", status: "running", records_synced: 0, records_skipped: 2, records_errors: 3 }, b: { entity: "utenze", status: "idle" } } });
    const rows = await load("whitecompany");
    expect(rows).toHaveLength(2);
    expect(rows[0].metrics[0].value).toBe(0);
    expect(rows[1].metrics[0].value).toBe("-");
  });
  it("mostra AUTODOC con e senza contatori", async () => {
    vi.mocked(getVehicleAutodocSyncStatus).mockResolvedValue({ ...job, records_synced: 3 } as never);
    expect((await load("autodoc"))[0].metrics[0].value).toBe(3);
    vi.mocked(getVehicleAutodocSyncStatus).mockResolvedValue({ ...job, records_synced: null, records_skipped: null, records_errors: null } as never);
    expect((await load("autodoc"))[0].metrics.map((item) => item.value)).toEqual(["-", "-", "-"]);
  });
  it("espone esito e configurazione Mobile senza trattare lo stato enabled come successo", async () => {
    resolveMock("getGateMobileSyncStatus", { sync_enabled: true, gateway_configured: true, token_configured: true, last_run: { status: "failed", started_at: time, finished_at: time, error_message: "gateway", operators_pushed: 0, requested_tasks_count: 1 } });
    const rows = await load("mobile");
    expect(rows[0].error).toBe("gateway");
    expect(rows[0].metrics[1].value).toBe("Completa");
    resolveMock("getGateMobileSyncStatus", { sync_enabled: true, gateway_configured: true, token_configured: false, last_run: { status: "completed", error_message: null } });
    expect((await load("mobile"))[0].error).toBe("Configurazione gateway o token incompleta");
    resolveMock("getGateMobileSyncStatus", { sync_enabled: true, gateway_configured: true, token_configured: false, last_run: null });
    expect((await load("mobile"))[0].metrics[1].value).toBe("Incompleta");
  });
  it("sceglie il batch autosync attivo e poi l'ultimo batch", async () => {
    const config = { enabled: true, last_planner_at: time, last_error_message: "planner", batch_size: 12 };
    resolveMock("getElaborazioneRuoloAutoSyncStatus", { config, running_batch: job, last_batch: null });
    expect((await load("autosync"))[0].status).toBe("completed");
    resolveMock("getElaborazioneRuoloAutoSyncStatus", { config, running_batch: null, last_batch: job });
    expect((await load("autosync"))[0].startedAt).toBe(time);
  });
  it("legge AdE e non nasconde errori diversi dall'assenza di run", async () => {
    vi.mocked(catastoGisGetLatestAdeWfsRunStatus).mockResolvedValue({ status: "running", started_at: time, progress_percent: 50, tiles_completed: 2, tiles: 4, with_geometry: 8 } as never);
    expect((await load("ade"))[0].metrics[0].value).toBe(50);
    vi.mocked(catastoGisGetLatestAdeWfsRunStatus).mockRejectedValue(new ApiError("vietato", null, 403));
    await expect(load("ade")).rejects.toThrow("vietato");
    vi.mocked(catastoGisGetLatestAdeWfsRunStatus).mockRejectedValue(new Error("network"));
    await expect(load("ade")).rejects.toThrow("network");
  });
  it("seleziona il run ANPR piu recente", async () => {
    resolveMock("getElaborazioneAnprSummary", { recent_runs: [{ started_at: "2026-01-01", status: "failed" }, { started_at: time, completed_at: time, status: "completed", subjects_processed: 4, errors: 0 }], calls_today: 2, effective_daily_limit: 100 });
    expect((await load("anpr"))[0].status).toBe("completed");
  });
});

describe("interfaccia e aggiornamento", () => {
  it("carica la dashboard, filtra servizi e aggiorna manualmente", async () => {
    render(<ElaborazioniPage />);
    expect(screen.getByRole("button", { name: "Aggiornamento..." })).toBeDisabled();
    await waitFor(() => expect(screen.getByRole("button", { name: "Aggiorna ora" })).toBeEnabled());
    expect(screen.getByRole("article", { name: "Capacitas inCass" })).toBeInTheDocument();
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "  INCASS  " } });
    expect(screen.getAllByRole("article")).toHaveLength(1);
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "inesistente" } });
    expect(screen.getByText("Nessun servizio corrisponde alla ricerca.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna ora" }));
    await waitFor(() => expect(api.listCapacitasInCassSyncJobs).toHaveBeenCalledTimes(2));
  });
  it("mantiene la card sintetica e apre dettagli e monitor con azioni distinte", () => {
    const service = SYNC_SERVICES[0];
    const onDetails = vi.fn();
    const onOpen = vi.fn();
    const { rerender } = render(<SyncServiceCard service={service} onDetails={onDetails} onOpen={onOpen} />);
    expect(screen.getByText("Caricamento stato...")).toBeInTheDocument();
    rerender(<SyncServiceCard service={service} onDetails={onDetails} onOpen={onOpen} state={{ snapshots: [{ status: "failed", startedAt: time, metrics: [{ label: "Record importati", value: 12 }], error: "errore sync" }], updatedAt: time, error: null }} />);
    expect(screen.getByText("Da verificare")).toBeInTheDocument();
    expect(screen.getByText("Record importati")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.queryByText("errore sync")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Vedi dettagli" }));
    fireEvent.click(screen.getByRole("button", { name: "Apri monitor" }));
    expect(onDetails).toHaveBeenCalledOnce();
    expect(onOpen).toHaveBeenCalledOnce();
    rerender(<SyncServiceCard service={service} onDetails={onDetails} onOpen={onOpen} state={{ snapshots: [], updatedAt: null, error: "offline" }} />);
    expect(screen.getByText("Dati non disponibili. Apri i dettagli.")).toBeInTheDocument();
  });
  it("mostra tutti i risultati e la diagnostica nei dettagli", () => {
    const { rerender } = render(<SyncServiceDetails />);
    expect(screen.getByText("Caricamento stato...")).toBeInTheDocument();
    rerender(<SyncServiceDetails state={{ snapshots: [
      { status: "failed", startedAt: time, finishedAt: time, metrics: [{ label: "Numero", value: 1234 }, { label: "Periodo", value: "settembre" }], error: "errore sync" },
      { status: "idle", detail: "Altro flusso", metrics: [] },
    ], updatedAt: time, error: null }} />);
    expect(screen.getByText("1234")).toBeInTheDocument();
    expect(screen.getByText("errore sync")).toBeInTheDocument();
    expect(screen.getByText("Altro flusso")).toBeInTheDocument();
    rerender(<SyncServiceDetails state={{ snapshots: [], updatedAt: null, error: "offline" }} />);
    expect(screen.getByRole("alert")).toHaveTextContent("offline");
    expect(screen.queryByText("Nessuna sincronizzazione registrata.")).not.toBeInTheDocument();
    rerender(<SyncServiceDetails state={{ snapshots: [], updatedAt: time, error: null }} />);
    expect(screen.getByText("Nessuna sincronizzazione registrata.")).toBeInTheDocument();
  });
  it("apre tutte le destinazioni in modale conservando ricerca e filtro", async () => {
    render(<ElaborazioniPage />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Aggiorna ora" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: /Da verificare/ }));
    expect(screen.getAllByRole("article")).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: /In corso \/ in coda/ }));
    expect(screen.getByText("Nessun servizio corrisponde alla ricerca.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Mostra tutti i servizi" }));
    expect(screen.getAllByRole("article")).toHaveLength(15);
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "inCass" } });
    fireEvent.click(screen.getByRole("button", { name: "Vedi dettagli" }));
    expect(screen.getByRole("dialog", { name: "Capacitas inCass" })).toBeInTheDocument();
    expect(document.body.style.overflow).toBe("hidden");
    const dialog = screen.getByRole("dialog");
    const firstButton = within(dialog).getByRole("button", { name: "Chiudi" });
    const lastButton = within(dialog).getByRole("button", { name: "Apri monitor" });
    const hidden = document.createElement("button");
    dialog.append(hidden);
    for (const button of [firstButton, lastButton]) vi.spyOn(button, "getClientRects").mockReturnValue([{}] as unknown as DOMRectList);
    firstButton.focus();
    fireEvent.keyDown(firstButton, { key: "Enter" });
    fireEvent.keyDown(firstButton, { key: "Tab" });
    fireEvent.keyDown(firstButton, { key: "Tab", shiftKey: true });
    expect(lastButton).toHaveFocus();
    fireEvent.keyDown(lastButton, { key: "Tab", shiftKey: true });
    fireEvent.keyDown(lastButton, { key: "Tab" });
    expect(firstButton).toHaveFocus();
    hidden.remove();
    fireEvent.click(lastButton);
    expect(await screen.findByText("Monitor: /elaborazioni/capacitas?section=incass")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toHaveClass("h-[min(88dvh,900px)]", "w-[min(calc(100%-2rem),1280px)]");
    fireEvent.click(screen.getByRole("button", { name: "Apri lavorazione" }));
    expect(await screen.findByText("Monitor: /elaborazioni/batches/123")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    expect(document.body.style.overflow).toBe("");
    expect(screen.getByRole("searchbox")).toHaveValue("inCass");
    fireEvent.click(screen.getByRole("button", { name: "Apri monitor" }));
    expect(await screen.findByText("Monitor: /elaborazioni/capacitas?section=incass")).toBeInTheDocument();
    fireEvent(screen.getByRole("dialog"), new Event("cancel", { bubbles: true, cancelable: true }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    for (const title of ["Credenziali e impostazioni", "Richieste e documenti", "Pianificazioni automatiche"]) {
      fireEvent.click(screen.getByRole("button", { name: title }));
      expect(screen.getByRole("dialog", { name: title })).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    }
  });
  it("isola gli errori, evita richieste concorrenti e ripristina il servizio", async () => {
    let resolve!: (value: never[]) => void;
    vi.mocked(api.listCapacitasInCassSyncJobs).mockReturnValueOnce(new Promise((done) => { resolve = done; }));
    vi.mocked(api.getSyncJobs).mockRejectedValueOnce(new Error("offline"));
    const { result } = renderHook(useSyncDashboard);
    await waitFor(() => expect(result.current.states.nas.error).toBe("offline"));
    expect(result.current.states.presenze.error).toBeNull();
    await act(async () => { await result.current.refresh(); });
    expect(api.listCapacitasInCassSyncJobs).toHaveBeenCalledTimes(1);
    await act(async () => { resolve([]); });
    await act(async () => { await result.current.refresh(); });
    expect(result.current.states.nas.error).toBeNull();
  });
  it("non richiede dati senza sessione e ignora risposte dopo unmount", async () => {
    vi.mocked(getStoredAccessToken).mockReturnValue(null);
    const first = renderHook(useSyncDashboard);
    expect(api.getSyncJobs).not.toHaveBeenCalled();
    first.unmount();
    vi.mocked(getStoredAccessToken).mockReturnValue("token");
    let done!: (value: never[]) => void;
    vi.mocked(api.getSyncJobs).mockReturnValueOnce(new Promise((resolve) => { done = resolve; }));
    const second = renderHook(useSyncDashboard);
    second.unmount();
    await act(async () => { done([]); });
  });
  it("aggiorna anche quando tutti i servizi sono inattivi", async () => {
    vi.useFakeTimers();
    renderHook(useSyncDashboard);
    await act(async () => {});
    await act(async () => { await vi.advanceTimersByTimeAsync(30000); });
    expect(api.getSyncJobs).toHaveBeenCalledTimes(2);
  });
});

describe("pianificazioni", () => {
  it("mantiene attivazione, disattivazione e configurazione", async () => {
    resolveMock("getElaborazioneAutoJobControls", [control, { ...control, key: "other", label: "Altro", enabled: false, detail: null, management_href: null }]);
    const onOpen = vi.fn();
    render(<SyncSchedules onOpen={onOpen} />);
    await screen.findByRole("button", { name: "Disattiva" });
    fireEvent.click(screen.getByRole("button", { name: "Disattiva" }));
    expect(screen.getByRole("button", { name: "Aggiornamento..." })).toBeDisabled();
    await waitFor(() => expect(api.updateElaborazioneAutoJobControl).toHaveBeenCalledWith("token", "sync", { enabled: false }));
    await screen.findByRole("button", { name: "Disattiva" });
    fireEvent.click(screen.getByRole("button", { name: "Attiva" }));
    await waitFor(() => expect(api.updateElaborazioneAutoJobControl).toHaveBeenCalledWith("token", "other", { enabled: true }));
    fireEvent.click(screen.getByRole("button", { name: "Configura" }));
    expect(onOpen).toHaveBeenCalledWith(control.management_href, control.label);
  });
  it("segnala errori di lettura e aggiornamento", async () => {
    vi.mocked(api.getElaborazioneAutoJobControls).mockRejectedValueOnce(new Error("lettura"));
    const first = render(<SyncSchedules onOpen={vi.fn()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("lettura");
    first.unmount();
    resolveMock("getElaborazioneAutoJobControls", [control]);
    vi.mocked(api.updateElaborazioneAutoJobControl).mockRejectedValueOnce("offline");
    render(<SyncSchedules onOpen={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Disattiva" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Impossibile leggere");
    vi.mocked(getStoredAccessToken).mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: "Disattiva" }));
    expect(api.updateElaborazioneAutoJobControl).toHaveBeenCalledTimes(1);
  });
  it("rispetta assenza sessione e unmount durante caricamento", async () => {
    vi.mocked(getStoredAccessToken).mockReturnValue(null);
    const first = render(<SyncSchedules onOpen={vi.fn()} />);
    expect(api.getElaborazioneAutoJobControls).not.toHaveBeenCalled();
    first.unmount();
    vi.mocked(getStoredAccessToken).mockReturnValue("token");
    for (const fail of [false, true]) {
      let settle!: () => void;
      vi.mocked(api.getElaborazioneAutoJobControls).mockReturnValueOnce(new Promise((resolve, reject) => { settle = () => fail ? reject(new Error("offline")) : resolve([]); }));
      const view = render(<SyncSchedules onOpen={vi.fn()} />);
      view.unmount();
      await act(async () => { settle(); });
    }
  });
});
