import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import type { CapacitasCredential, CapacitasInCassRuoloHarvestResult, CapacitasInCassSyncJob, CapacitasInCassSyncJobListItem } from "@/types/api";

const mocks = vi.hoisted(() => ({
  token: vi.fn(), credentials: vi.fn(), terreniJobs: vi.fn(), particelleJobs: vi.fn(),
  historyJobs: vi.fn(), incassJobs: vi.fn(), createSync: vi.fn(), createHarvest: vi.fn(),
  rerun: vi.fn(), deleteJob: vi.fn(), authError: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", () => ({
  listCapacitasCredentials: mocks.credentials,
  listCapacitasTerreniJobs: mocks.terreniJobs,
  listCapacitasParticelleSyncJobs: mocks.particelleJobs,
  listCapacitasAnagraficaHistoryJobs: mocks.historyJobs,
  listCapacitasInCassSyncJobs: mocks.incassJobs,
  createCapacitasInCassSyncJob: mocks.createSync,
  createCapacitasInCassRuoloHarvest: mocks.createHarvest,
  rerunCapacitasInCassSyncJob: mocks.rerun,
  deleteCapacitasInCassSyncJob: mocks.deleteJob,
  isAuthError: mocks.authError,
}));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({ ElaborazioneWorkspaceModal: () => null }));

const commands = [
  { mode: "sync" as const, button: "Avvia sync avvisi", busy: "Avvio..." },
  { mode: "harvest" as const, button: "Crea batch job da ruolo", busy: "Creo batch..." },
];

function credential(): CapacitasCredential {
  return {
    id: 7, label: "Operatore", username: "operator-7", active: true,
    allowed_hours_start: 0, allowed_hours_end: 24, last_used_at: null, last_error: null,
    consecutive_failures: 0, created_at: "2026-10-08T12:00:00Z", updated_at: "2026-10-08T12:00:00Z",
  };
}

function syncJob(id = 71): CapacitasInCassSyncJob {
  return {
    id, credential_id: null, requested_by_user_id: 1, status: "succeeded", mode: "batch",
    payload_json: { limit: 100 }, result_json: null, error_detail: null,
    started_at: "2026-10-08T12:01:00Z", completed_at: "2026-10-08T12:02:00Z",
    created_at: "2026-10-08T12:00:00Z", updated_at: "2026-10-08T12:02:00Z",
  };
}

function listJob(id: number): CapacitasInCassSyncJobListItem {
  return {
    id, credential_id: null, requested_by_user_id: 1, status: "succeeded", mode: "batch",
    subject_count: 1, result_json: null, error_detail: null,
    started_at: "2026-10-08T12:01:00Z", completed_at: "2026-10-08T12:02:00Z",
    created_at: "2026-10-08T12:00:00Z", updated_at: "2026-10-08T12:02:00Z",
  };
}

function harvestResult(overrides: Partial<CapacitasInCassRuoloHarvestResult> = {}): CapacitasInCassRuoloHarvestResult {
  return {
    anno: 2025, chunk_size: 100, total_subjects: 120, total_jobs: 2, job_ids: [81, 82],
    credential_id: null, exclude_synced_subjects: true, ...overrides,
  };
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  const promise = new Promise<Value>((fulfill) => { resolve = fulfill; });
  return { promise, resolve };
}

function openPanel(mode: "sync" | "harvest") {
  const tab = mode === "sync" ? /^Avvisi pagamenti/ : /^Storico anagrafico/;
  const navigation = screen.getByRole("navigation", { name: "Sezioni Capacitas" });
  fireEvent.click(within(navigation).getByRole("button", { name: tab }));
  const title = mode === "sync" ? "Sincronizzazione avvisi di pagamento sugli utenti" : "Crea job massivi inCass dai soggetti a ruolo";
  const article = screen.getByText(title).closest("article");
  expect(article).not.toBeNull();
  return within(article!);
}

function jobControls(id: number) {
  const card = screen.getByText(`Job #${id}`).closest('div[class*="rounded-[24px]"]');
  expect(card).not.toBeNull();
  return within(card as HTMLElement);
}

function commandMock(mode: "sync" | "harvest") {
  return mode === "sync" ? mocks.createSync : mocks.createHarvest;
}

async function mountWorkspace() {
  const view = render(<ElaborazioniCapacitasWorkspace embedded initialSection="incass" />);
  await waitFor(() => expect(screen.queryByText("Caricamento job avvisi...")).not.toBeInTheDocument());
  return view;
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.token.mockReturnValue("session-token");
  for (const list of [mocks.credentials, mocks.terreniJobs, mocks.particelleJobs, mocks.historyJobs, mocks.incassJobs]) {
    list.mockResolvedValue([]);
  }
  mocks.authError.mockReturnValue(false);
  mocks.createSync.mockResolvedValue(syncJob());
  mocks.createHarvest.mockResolvedValue(harvestResult());
  mocks.rerun.mockResolvedValue(syncJob(11));
  mocks.deleteJob.mockResolvedValue(undefined);
});

afterEach(() => { cleanup(); });

describe("Capacitas inCASS command creation", () => {
  test("submits the exact sync defaults through the real payload helper and then refreshes the list", async () => {
    await mountWorkspace();
    fireEvent.click(openPanel("sync").getByRole("button", { name: "Avvia sync avvisi" }));
    await waitFor(() => expect(mocks.createSync).toHaveBeenCalledExactlyOnceWith("session-token", {
      credential_id: undefined, limit: 100, include_details: true, include_partitario: true,
      include_mailing_list: true, download_mailing_receipts: false, continue_on_error: true, throttle_ms: 250,
    }));
    expect(await screen.findByText("Job avvisi #71 creato e avviato in background.")).toBeInTheDocument();
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
    expect(mocks.incassJobs).toHaveBeenLastCalledWith("session-token", { limit: 300 });
    expect(mocks.createHarvest).not.toHaveBeenCalled();
  });

  test("maps selected credential, sanitized numeric fields and all sync switches without adding subject_ids", async () => {
    mocks.credentials.mockResolvedValue([credential()]);
    await mountWorkspace();
    const panel = openPanel("sync");
    expect(panel.getByLabelText("Credenziale")).toHaveValue("7");
    fireEvent.change(panel.getByLabelText("Limite soggetti"), { target: { value: "2a5" } });
    fireEvent.change(panel.getByLabelText("Pausa richieste (ms)"), { target: { value: "7x5" } });
    for (const label of ["Salva dettaglio avviso", 'Salva dettaglio "I"', "Recupera recapiti e spedizioni", "Scarica ricevute PEC su NAS", "Continua se un soggetto fallisce"]) {
      fireEvent.click(panel.getByLabelText(label));
    }
    expect(panel.getByLabelText("Limite soggetti")).toHaveValue("25");
    expect(panel.getByLabelText("Pausa richieste (ms)")).toHaveValue("75");
    fireEvent.click(panel.getByRole("button", { name: "Avvia sync avvisi" }));
    await waitFor(() => expect(mocks.createSync).toHaveBeenCalledExactlyOnceWith("session-token", {
      credential_id: 7, limit: 25, include_details: false, include_partitario: false,
      include_mailing_list: false, download_mailing_receipts: true, continue_on_error: false, throttle_ms: 75,
    }));
  });

  test.each([
    { input: "", limit: undefined, throttle: 250 },
    { input: "0", limit: 0, throttle: 0 },
  ])("retains blank/zero sync semantics for input '$input'", async ({ input, limit, throttle }) => {
    await mountWorkspace();
    const panel = openPanel("sync");
    fireEvent.change(panel.getByLabelText("Limite soggetti"), { target: { value: input } });
    fireEvent.change(panel.getByLabelText("Pausa richieste (ms)"), { target: { value: input } });
    fireEvent.click(panel.getByRole("button", { name: "Avvia sync avvisi" }));
    await waitFor(() => expect(mocks.createSync).toHaveBeenCalledExactlyOnceWith("session-token", {
      credential_id: undefined, limit, include_details: true, include_partitario: true,
      include_mailing_list: true, download_mailing_receipts: false, continue_on_error: true, throttle_ms: throttle,
    }));
  });

  test("submits exact harvest defaults and keeps the returned job/subject totals across sections", async () => {
    await mountWorkspace();
    fireEvent.click(openPanel("harvest").getByRole("button", { name: "Crea batch job da ruolo" }));
    await waitFor(() => expect(mocks.createHarvest).toHaveBeenCalledExactlyOnceWith("session-token", {
      credential_id: undefined, anno: 2025, chunk_size: 100, limit_subjects: undefined,
      exclude_synced_subjects: true, include_details: true, include_partitario: true,
      include_mailing_list: true, download_mailing_receipts: false, continue_on_error: true, throttle_ms: 250,
    }));
    expect(openPanel("harvest").getByText(/Ultimo batch:/)).toHaveTextContent("Ultimo batch: 2 job per 120 soggetti.");
    expect(openPanel("sync").getByText("Creati 2 job inCass per 120 soggetti a ruolo.")).toBeInTheDocument();
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
    expect(mocks.createSync).not.toHaveBeenCalled();
  });

  test("maps harvest credential/year/limits and each filter/receipt switch to the exact payload", async () => {
    mocks.credentials.mockResolvedValue([credential()]);
    mocks.createHarvest.mockResolvedValue(harvestResult({ anno: 2024, chunk_size: 25, total_subjects: 45, credential_id: 7, exclude_synced_subjects: false }));
    await mountWorkspace();
    const panel = openPanel("harvest");
    expect(panel.getByLabelText("Credenziale")).toHaveValue("");
    fireEvent.change(panel.getByLabelText("Credenziale"), { target: { value: "7" } });
    for (const [label, value] of [["Anno ruolo", "20a24"], ["Soggetti per job", "2x5"], ["Limite soggetti", "2-00"], ["Pausa richieste (ms)", "0"]]) {
      fireEvent.change(panel.getByLabelText(label), { target: { value } });
    }
    for (const label of ["Escludi soggetti già sincronizzati", "Salva dettaglio avviso", "Salva partitario completo", "Recupera recapiti e spedizioni", "Scarica ricevute PEC su NAS", "Continua se un soggetto fallisce"]) {
      fireEvent.click(panel.getByLabelText(label));
    }
    expect(panel.getByLabelText("Anno ruolo")).toHaveValue("2024");
    expect(panel.getByLabelText("Soggetti per job")).toHaveValue("25");
    expect(panel.getByLabelText("Limite soggetti")).toHaveValue("200");
    fireEvent.click(panel.getByRole("button", { name: "Crea batch job da ruolo" }));
    await waitFor(() => expect(mocks.createHarvest).toHaveBeenCalledExactlyOnceWith("session-token", {
      credential_id: 7, anno: 2024, chunk_size: 25, limit_subjects: 200,
      exclude_synced_subjects: false, include_details: false, include_partitario: false,
      include_mailing_list: false, download_mailing_receipts: true, continue_on_error: false, throttle_ms: 0,
    }));
  });

  test("uses blank harvest defaults and renders the zero-eligible outcome without inventing jobs", async () => {
    mocks.createHarvest.mockResolvedValue(harvestResult({ anno: null, total_subjects: 0, total_jobs: 0, job_ids: [] }));
    await mountWorkspace();
    const panel = openPanel("harvest");
    for (const label of ["Anno ruolo", "Soggetti per job", "Limite soggetti", "Pausa richieste (ms)"]) {
      fireEvent.change(panel.getByLabelText(label), { target: { value: "" } });
    }
    fireEvent.click(panel.getByRole("button", { name: "Crea batch job da ruolo" }));
    await waitFor(() => expect(mocks.createHarvest).toHaveBeenCalledExactlyOnceWith("session-token", {
      credential_id: undefined, anno: undefined, chunk_size: 100, limit_subjects: undefined,
      exclude_synced_subjects: true, include_details: true, include_partitario: true,
      include_mailing_list: true, download_mailing_receipts: false, continue_on_error: true, throttle_ms: 250,
    }));
    expect(openPanel("harvest").getByText(/Ultimo batch:/)).toHaveTextContent("Ultimo batch: 0 job per 0 soggetti.");
    expect(openPanel("sync").getByText("Nessun soggetto a ruolo eleggibile per il batch richiesto.")).toBeInTheDocument();
    expect(screen.getByText("Nessun job avvisi registrato")).toBeInTheDocument();
  });

  test.each(commands)("keeps $mode creation disabled until its subsequent monitor refresh completes", async ({ mode, button, busy }) => {
    const creation = deferred<CapacitasInCassSyncJob | CapacitasInCassRuoloHarvestResult>();
    const refresh = deferred<[]>();
    commandMock(mode).mockReturnValueOnce(creation.promise);
    await mountWorkspace();
    mocks.incassJobs.mockReturnValueOnce(refresh.promise);
    fireEvent.click(openPanel(mode).getByRole("button", { name: button }));
    expect(openPanel(mode).getByRole("button", { name: busy })).toBeDisabled();
    expect(mocks.incassJobs).toHaveBeenCalledTimes(1);
    await act(async () => creation.resolve(mode === "sync" ? syncJob() : harvestResult()));
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
    const pending = openPanel(mode).getByRole("button", { name: busy });
    expect(pending).toBeDisabled();
    fireEvent.click(pending);
    expect(commandMock(mode)).toHaveBeenCalledTimes(1);
    await act(async () => refresh.resolve([]));
    expect(openPanel(mode).getByRole("button", { name: button })).toBeEnabled();
  });

  test.each(commands)("does not dispatch $mode creation after its GAIA token disappears", async ({ mode, button }) => {
    await mountWorkspace();
    mocks.token.mockReturnValue(null);
    fireEvent.click(openPanel(mode).getByRole("button", { name: button }));
    expect(commandMock(mode)).not.toHaveBeenCalled();
    expect(openPanel(mode).getByRole("button", { name: button })).toBeEnabled();
    expect(mocks.incassJobs).toHaveBeenCalledTimes(1);
  });

  test.each([
    { mode: "sync" as const, failure: new Error("Sync unavailable"), message: "Sync unavailable" },
    { mode: "sync" as const, failure: "sync rejection", message: "Errore avvio job avvisi" },
    { mode: "harvest" as const, failure: new Error("Harvest unavailable"), message: "Harvest unavailable" },
    { mode: "harvest" as const, failure: "harvest rejection", message: "Errore creazione job harvest inCass" },
  ])("renders $mode command failure and recovers on retry: $message", async ({ mode, failure, message }) => {
    commandMock(mode).mockRejectedValueOnce(failure);
    await mountWorkspace();
    const button = commands.find((command) => command.mode === mode)!.button;
    const control = openPanel(mode).getByRole("button", { name: button });
    await act(async () => { fireEvent.click(control); });
    if (mode === "harvest") expect(screen.queryByText(message)).not.toBeInTheDocument();
    expect(openPanel("sync").getByText(message)).toBeInTheDocument();
    expect(mocks.incassJobs).toHaveBeenCalledTimes(1);
    fireEvent.click(openPanel(mode).getByRole("button", { name: button }));
    await waitFor(() => expect(mocks.incassJobs).toHaveBeenCalledTimes(2));
    expect(commandMock(mode)).toHaveBeenCalledTimes(2);
    expect(openPanel("sync").queryByText(message)).not.toBeInTheDocument();
  });

  test.each([
    { failure: new Error("Monitor unavailable"), message: "Monitor unavailable" },
    { failure: "monitor rejection", message: "Errore caricamento job avvisi" },
  ])("preserves successful creation status when the refresh fails: $message", async ({ failure, message }) => {
    await mountWorkspace();
    mocks.incassJobs.mockRejectedValueOnce(failure);
    fireEvent.click(openPanel("sync").getByRole("button", { name: "Avvia sync avvisi" }));
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.getByText("Job avvisi #71 creato e avviato in background.")).toBeInTheDocument();
    expect(openPanel("sync").getByRole("button", { name: "Avvia sync avvisi" })).toBeEnabled();
    expect(mocks.createSync).toHaveBeenCalledTimes(1);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
  });

  test("replaces successful creation status when its refresh reports session expiry", async () => {
    await mountWorkspace();
    mocks.incassJobs.mockRejectedValueOnce(new Error("GAIA session expired"));
    mocks.authError.mockReturnValueOnce(true);
    fireEvent.click(openPanel("sync").getByRole("button", { name: "Avvia sync avvisi" }));
    expect(await screen.findByText("Sessione GAIA scaduta: il monitor avvisi si ferma, ma i job backend gia avviati possono continuare.")).toBeInTheDocument();
    expect(screen.getByText("Rientra in GAIA per riprendere il polling del monitor avvisi.")).toBeInTheDocument();
    expect(screen.queryByText("Job avvisi #71 creato e avviato in background.")).not.toBeInTheDocument();
    expect(openPanel("sync").getByRole("button", { name: "Avvia sync avvisi" })).toBeEnabled();
    expect(mocks.createSync).toHaveBeenCalledTimes(1);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
  });

  test("retains the previous harvest totals when a later harvest creation fails", async () => {
    await mountWorkspace();
    fireEvent.click(openPanel("harvest").getByRole("button", { name: "Crea batch job da ruolo" }));
    await waitFor(() => expect(mocks.incassJobs).toHaveBeenCalledTimes(2));
    expect(openPanel("harvest").getByText(/Ultimo batch:/)).toHaveTextContent("Ultimo batch: 2 job per 120 soggetti.");
    mocks.createHarvest.mockRejectedValueOnce(new Error("Second harvest rejected"));
    const control = openPanel("harvest").getByRole("button", { name: "Crea batch job da ruolo" });
    await act(async () => { fireEvent.click(control); });
    expect(openPanel("harvest").getByText(/Ultimo batch:/)).toHaveTextContent("Ultimo batch: 2 job per 120 soggetti.");
    expect(openPanel("sync").getByText("Second harvest rejected")).toBeInTheDocument();
    expect(screen.getByText("Creati 2 job inCass per 120 soggetti a ruolo.")).toBeInTheDocument();
    expect(mocks.createHarvest).toHaveBeenCalledTimes(2);
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
  });
});

describe("Capacitas inCASS row commands", () => {
  test("reruns only the selected row and hides row commands until refresh completes", async () => {
    const rerun = deferred<CapacitasInCassSyncJob>();
    const refresh = deferred<CapacitasInCassSyncJobListItem[]>();
    mocks.incassJobs.mockResolvedValueOnce([listJob(11), listJob(12)]);
    mocks.rerun.mockReturnValueOnce(rerun.promise);
    await mountWorkspace();
    mocks.incassJobs.mockReturnValueOnce(refresh.promise);
    fireEvent.click(jobControls(11).getByRole("button", { name: "Rilancia" }));
    expect(mocks.rerun).toHaveBeenCalledExactlyOnceWith("session-token", 11);
    expect(jobControls(11).getByRole("button", { name: "Rerun..." })).toBeDisabled();
    expect(jobControls(12).getByRole("button", { name: "Rilancia" })).toBeEnabled();
    expect(mocks.incassJobs).toHaveBeenCalledTimes(1);
    await act(async () => rerun.resolve(syncJob(11)));
    expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
    expect(screen.getByText("Job avvisi #11 rilanciato.")).toBeInTheDocument();
    expect(screen.getByText("Caricamento job avvisi...")).toBeInTheDocument();
    expect(screen.queryByText("Job #11")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Rilancia" })).not.toBeInTheDocument();
    expect(mocks.rerun).toHaveBeenCalledTimes(1);
    await act(async () => refresh.resolve([listJob(11), listJob(12)]));
    expect(jobControls(11).getByRole("button", { name: "Rilancia" })).toBeEnabled();
    expect(screen.getByText("Job #12")).toBeInTheDocument();
  });

  test("deletes only the targeted row after API success without reloading the monitor", async () => {
    const deletion = deferred<void>();
    mocks.incassJobs.mockResolvedValueOnce([listJob(11), listJob(12)]);
    mocks.deleteJob.mockReturnValueOnce(deletion.promise);
    await mountWorkspace();
    fireEvent.click(jobControls(11).getByRole("button", { name: "Elimina" }));
    expect(mocks.deleteJob).toHaveBeenCalledExactlyOnceWith("session-token", 11);
    expect(jobControls(11).getByRole("button", { name: "Elimina..." })).toBeDisabled();
    expect(jobControls(12).getByRole("button", { name: "Elimina" })).toBeEnabled();
    expect(screen.getByText("Job #11")).toBeInTheDocument();
    await act(async () => deletion.resolve());
    expect(screen.queryByText("Job #11")).not.toBeInTheDocument();
    expect(screen.getByText("Job #12")).toBeInTheDocument();
    expect(screen.getByText("Job avvisi #11 eliminato.")).toBeInTheDocument();
    expect(mocks.incassJobs).toHaveBeenCalledTimes(1);
  });

  test.each([
    { action: "rerun" as const, label: "Rilancia", failure: new Error("Rerun unavailable"), message: "Rerun unavailable" },
    { action: "rerun" as const, label: "Rilancia", failure: "rerun rejection", message: "Errore rerun job avvisi" },
    { action: "delete" as const, label: "Elimina", failure: new Error("Delete unavailable"), message: "Delete unavailable" },
    { action: "delete" as const, label: "Elimina", failure: "delete rejection", message: "Errore eliminazione job avvisi" },
  ])("preserves both rows on $action failure and permits retry: $message", async ({ action, label, failure, message }) => {
    mocks.incassJobs.mockResolvedValue([listJob(11), listJob(12)]);
    const endpoint = action === "rerun" ? mocks.rerun : mocks.deleteJob;
    endpoint.mockRejectedValueOnce(failure);
    await mountWorkspace();
    fireEvent.click(jobControls(11).getByRole("button", { name: label }));
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(jobControls(11).getByRole("button", { name: label })).toBeEnabled();
    expect(screen.getByText("Job #12")).toBeInTheDocument();
    expect(mocks.incassJobs).toHaveBeenCalledTimes(1);
    fireEvent.click(jobControls(11).getByRole("button", { name: label }));
    await waitFor(() => expect(screen.queryByText(message)).not.toBeInTheDocument());
    expect(endpoint).toHaveBeenCalledTimes(2);
    expect(screen.getByText("Job #12")).toBeInTheDocument();
    if (action === "delete") expect(screen.queryByText("Job #11")).not.toBeInTheDocument();
    else expect(mocks.incassJobs).toHaveBeenCalledTimes(2);
  });

  test.each(["Rilancia", "Elimina"])("does not dispatch %s when the token disappears", async (label) => {
    mocks.incassJobs.mockResolvedValue([listJob(11), listJob(12)]);
    await mountWorkspace();
    mocks.token.mockReturnValue(null);
    fireEvent.click(jobControls(11).getByRole("button", { name: label }));
    expect(mocks.rerun).not.toHaveBeenCalled();
    expect(mocks.deleteJob).not.toHaveBeenCalled();
    expect(jobControls(11).getByRole("button", { name: label })).toBeEnabled();
    expect(screen.getByText("Job #12")).toBeInTheDocument();
    expect(mocks.incassJobs).toHaveBeenCalledTimes(1);
  });
});
