import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import { ApiError } from "@/lib/api/core";
import type {
  CapacitasAnagraficaHistoryImportJob, CapacitasAnagraficaHistoryImportResult,
  CapacitasInCassSyncJobListItem, CapacitasParticelleSyncJob, CapacitasTerreniJob,
} from "@/types/api";

const mocks = vi.hoisted(() => ({
  token: vi.fn<() => string | null>(), credentials: vi.fn(),
  terreni: vi.fn(), particelle: vi.fn(), storico: vi.fn(), incass: vi.fn(),
}));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", async () => ({
  listCapacitasCredentials: mocks.credentials,
  listCapacitasTerreniJobs: mocks.terreni,
  listCapacitasParticelleSyncJobs: mocks.particelle,
  listCapacitasAnagraficaHistoryJobs: mocks.storico,
  listCapacitasInCassSyncJobs: mocks.incass,
  isAuthError: (await import("@/lib/api/core")).isAuthError,
}));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({ ElaborazioneWorkspaceModal: () => null }));

const families = [
  { section: "terreni", interval: 15000, label: "Terreni", guidance: "del monitor Terreni", fallback: "Terreni", completion: null },
  { section: "particelle", interval: 15000, label: "particelle", guidance: "della sync progressiva particelle", fallback: "particelle", completion: "Sync progressiva particelle aggiornata." },
  { section: "storico", interval: 15000, label: "storico", guidance: "del monitor storico anagrafico", fallback: "storico anagrafico", completion: "Storico anagrafico aggiornato." },
  { section: "incass", interval: 20000, label: "avvisi", guidance: "del monitor avvisi", fallback: "avvisi", completion: "Sync avvisi aggiornata." },
] as const;
type Family = typeof families[number];
type Job = CapacitasTerreniJob | CapacitasParticelleSyncJob | CapacitasAnagraficaHistoryImportJob | CapacitasInCassSyncJobListItem;

function historyResult(processed: number): CapacitasAnagraficaHistoryImportResult {
  return { processed, imported: processed, skipped: 0, failed: 0, snapshot_records_imported: processed + 1, items: [] };
}

function job(id: number, status: string, result_json: Job["result_json"] = null): Job {
  return {
    id, status, result_json, credential_id: null, requested_by_user_id: 1, mode: "batch",
    payload_json: { items: [] }, subject_count: null, error_detail: null,
    started_at: null, completed_at: null, created_at: "2026-10-08T12:00:00Z", updated_at: "2026-10-08T12:00:00Z",
  };
}

function initialJobs(family: Family): Job[] {
  const jobs = [job(11, "pending"), job(12, "processing")];
  return family.section === "storico" ? [...jobs, job(99, "succeeded", historyResult(7))] : jobs;
}
const manualRows = () => [job(12, "queued_resume"), job(11, "pending")];
const silentRows = () => [job(11, "processing"), job(12, "pending")];
const terminalRows = () => [job(11, "failed"), job(12, "succeeded", historyResult(22)), job(13, "succeeded", historyResult(33))];

function deferred() {
  let resolve!: (jobs: Job[]) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<Job[]>((fulfill, fail) => { resolve = fulfill; reject = fail; });
  return { promise, resolve, reject };
}
const list = (family: Family) => mocks[family.section];
const expiry = (family: Family) => `Sessione GAIA scaduta: il monitor ${family.label} si ferma, ma i job backend gia avviati possono continuare.`;
const guidance = (family: Family) => `Rientra in GAIA per riprendere il polling ${family.guidance}.`;
const loading = (family: Family) => `Caricamento job ${family.label}...`;
const fallback = (family: Family) => `Errore caricamento job ${family.fallback}`;

function notice(message: string, visible: boolean) {
  const matches = screen.queryAllByText(message, { exact: true });
  if (visible) {
    expect(matches.length).toBeGreaterThan(0);
    for (const match of matches) expect(match).toBeVisible();
  } else expect(matches).toHaveLength(0);
}

function expectLoading(family: Family, busy: boolean) {
  notice(loading(family), busy);
  const button = screen.getByRole("button", { name: "Aggiorna job" });
  if (busy) expect(button).toBeDisabled();
  else expect(button).toBeEnabled();
}

function expectRows(family: Family, ids: number[], labels: string[]) {
  const pattern = family.section === "terreni" ? /^#\d+$/ : /^Job #\d+$/;
  expect(screen.getAllByText(pattern).map(element => element.textContent)).toEqual(
    ids.map(id => family.section === "terreni" ? `#${id}` : `Job #${id}`),
  );
  ids.forEach((id, index) => {
    const element = screen.getByText(family.section === "terreni" ? `#${id}` : `Job #${id}`);
    const row = element.closest("tr") ?? element.closest('div[class*="rounded-[24px]"], div[class*="rounded-[20px]"]');
    expect(row).not.toBeNull();
    expect(within(row as HTMLElement).getByText(labels[index], { exact: true })).toBeVisible();
  });
}

function expectInitialRows(family: Family) {
  if (family.section === "incass") expectRows(family, [12, 11], ["In corso", "In attesa"]);
  else if (family.section === "storico") expectRows(family, [11, 12, 99], ["In attesa", "In corso", "Completato"]);
  else expectRows(family, [11, 12], ["In attesa", "In corso"]);
}

function expectReport(processed: number) {
  const panel = screen.getByText("Report aggregato dell'ultima importazione storico anagrafico eseguita dal workspace Capacitas.").closest("article")!;
  expect(within(panel).getByText(`${processed} processati · ${processed + 1} snapshot importati`)).toBeVisible();
}
async function tick(milliseconds: number) {
  await act(async () => { await vi.advanceTimersByTimeAsync(milliseconds); });
}
async function refresh() {
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Aggiorna job" })); });
}
async function mount(family: Family) {
  render(<ElaborazioniCapacitasWorkspace embedded initialSection={family.section} />);
  await act(async () => {});
  for (const candidate of families) expect(list(candidate)).toHaveBeenCalledTimes(1);
  expectLoading(family, false);
}
function expectDispatch(family: Family, call: number, token: string) {
  if (family.section === "incass") expect(list(family)).toHaveBeenNthCalledWith(call, token, { limit: 300 });
  else expect(list(family)).toHaveBeenNthCalledWith(call, token);
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.useFakeTimers();
  vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
  mocks.token.mockReturnValue("token-A");
  mocks.credentials.mockResolvedValue([]);
  for (const family of families) list(family).mockResolvedValue([]);
});
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); });

describe.each(families)("R11 $section authentic expiry", family => {
  test.each([401, 403])("real ApiError %s stops ticks and manual recovery clears error but retains guidance", async status => {
    list(family).mockResolvedValueOnce(initialJobs(family)).mockRejectedValueOnce(new ApiError("Private API detail", null, status)).mockResolvedValue(silentRows());
    await mount(family);
    expectDispatch(family, 1, "token-A");
    await tick(family.interval - 1);
    expect(list(family)).toHaveBeenCalledTimes(1);
    await tick(1);
    expectDispatch(family, 2, "token-A");
    notice(expiry(family), true);
    notice(guidance(family), true);
    notice("Private API detail", false);
    expectLoading(family, false);
    expectInitialRows(family);
    await tick(family.interval * 3);
    await act(async () => { document.dispatchEvent(new Event("visibilitychange")); });
    expect(list(family)).toHaveBeenCalledTimes(2);
    mocks.token.mockReturnValue("restored-token");
    await refresh();
    expectDispatch(family, 3, "restored-token");
    notice(expiry(family), false);
    notice(guidance(family), true);
    expectRows(family, [11, 12], ["In corso", "In attesa"]);
    await tick(family.interval);
    expectDispatch(family, 4, "restored-token");
    if (family.section === "storico") expectReport(7);
  });
});

describe("R11 Terreni first tracked terminal in response order", () => {
  test.each([[11, 12], [12, 11]])("API tracked order %s then %s selects the first, skipping an unrelated terminal", async (first, second) => {
    const family = families[0];
    list(family).mockResolvedValueOnce(initialJobs(family)).mockResolvedValue([job(90, "succeeded"), job(first, "failed"), job(second, "succeeded")]);
    await mount(family);
    await tick(14999);
    expect(list(family)).toHaveBeenCalledTimes(1);
    await tick(1);
    notice(`Job #${first} completato`, true);
    notice(`Job #${second} completato`, false);
    notice("Job #90 completato", false);
    expectRows(family, [90, first, second], ["Completato", "Fallito", "Completato"]);
    fireEvent.click(screen.getByText("Chiudi", { selector: "button", exact: true }));
    await tick(45000);
    expect(list(family)).toHaveBeenCalledTimes(2);
    notice("Report elaborazione Terreni", false);
  });
});

const pairs = [
  "manual-active/silent-terminal", "manual-error/silent-active", "manual-401/silent-active",
  "manual-active/silent-error", "manual-active/silent-403", "manual-fallback/silent-terminal",
] as const;
const orders = ["manual-first", "silent-first"] as const;
const timelines = families.flatMap(family => pairs.flatMap(pair => orders.map(order => ({ family, section: family.section, pair, order }))));

describe("R11 manual refresh overlaps real polling without freshness filtering", () => {
  test.each(timelines)("$section $pair $order", async ({ family, pair, order }) => {
    const manual = deferred();
    const silent = deferred();
    list(family).mockResolvedValueOnce(initialJobs(family)).mockReturnValueOnce(manual.promise).mockReturnValueOnce(silent.promise).mockResolvedValue(silentRows());
    await mount(family);
    if (family.section === "storico") expectReport(7);
    await refresh();
    expectDispatch(family, 2, "token-A");
    expectLoading(family, true);
    mocks.token.mockReturnValue("token-B");
    await tick(family.interval - 1);
    expect(list(family)).toHaveBeenCalledTimes(2);
    await tick(1);
    expectDispatch(family, 3, "token-B");
    expectLoading(family, true);
    mocks.token.mockReturnValue(null);
    const manualError = pair === "manual-error/silent-active";
    const manualAuth = pair === "manual-401/silent-active";
    const manualFallback = pair === "manual-fallback/silent-terminal";
    const silentError = pair === "manual-active/silent-error";
    const silentAuth = pair === "manual-active/silent-403";
    const terminal = pair.endsWith("silent-terminal");
    const manualSuccess = !manualError && !manualAuth && !manualFallback;
    const silentSuccess = !silentError && !silentAuth;
    const settleManual = () => {
      if (manualError) manual.reject(new Error("Manual list unavailable"));
      else if (manualAuth) manual.reject(new ApiError("Manual private detail", null, 401));
      else if (manualFallback) manual.reject({ status: 401, message: "Status-only is not ApiError" });
      else manual.resolve(manualRows());
    };
    const settleSilent = () => {
      if (silentError) silent.reject(new Error("Silent list unavailable"));
      else if (silentAuth) silent.reject(new ApiError("Silent private detail", null, 403));
      else silent.resolve(terminal ? terminalRows() : silentRows());
    };
    const manualFirst = order === "manual-first";
    await act(async () => { (manualFirst ? settleManual : settleSilent)(); });
    expectLoading(family, !manualFirst);
    notice("Silent list unavailable", false);
    notice("Manual private detail", false);
    notice("Silent private detail", false);
    notice("Status-only is not ApiError", false);
    notice("Manual list unavailable", manualFirst && manualError);
    notice(fallback(family), manualFirst && manualFallback);
    notice(expiry(family), manualFirst ? manualAuth : silentAuth);
    notice(guidance(family), manualFirst ? manualAuth : silentAuth);
    if (manualFirst) {
      if (manualSuccess) expectRows(family, [12, 11], ["Ripresa pianificata", "In attesa"]);
      else expectInitialRows(family);
    } else {
      expect(screen.queryByText(family.section === "terreni" ? "#11" : "Job #11", { exact: true })).not.toBeInTheDocument();
    }
    if (family.section === "storico") expectReport(!manualFirst && terminal ? 22 : 7);
    if (family.section === "terreni") notice("Job #11 completato", !manualFirst && terminal);
    await act(async () => { (manualFirst ? settleSilent : settleManual)(); });
    expectLoading(family, false);
    expect(list(family)).toHaveBeenCalledTimes(3);
    const lastRowsAreManual = manualSuccess && (!manualFirst || !silentSuccess);
    if (lastRowsAreManual) expectRows(family, [12, 11], ["Ripresa pianificata", "In attesa"]);
    else if (terminal) expectRows(family, [11, 12, 13], ["Fallito", "Completato", "Completato"]);
    else expectRows(family, [11, 12], ["In corso", "In attesa"]);
    notice("Manual list unavailable", manualError);
    notice(fallback(family), manualFallback);
    notice(expiry(family), manualAuth || (silentAuth && manualFirst));
    notice(guidance(family), manualAuth || silentAuth);
    notice("Silent list unavailable", false);
    if (family.completion) notice(family.completion, false);
    if (family.section === "storico") expectReport(terminal ? 22 : 7);
    if (family.section === "terreni") {
      notice("Report elaborazione Terreni", terminal);
      if (terminal) notice(`Job #11 ${lastRowsAreManual ? "in corso" : "completato"}`, true);
    }
    mocks.token.mockReturnValue("restored-token");
    const shouldPoll = (!terminal || lastRowsAreManual) && !(manualAuth && !manualFirst) && !(silentAuth && manualFirst);
    await tick(family.interval - 1);
    expect(list(family)).toHaveBeenCalledTimes(3);
    await tick(1);
    expect(list(family)).toHaveBeenCalledTimes(shouldPoll ? 4 : 3);
    if (shouldPoll) expectDispatch(family, 4, "restored-token");
    notice("Manual list unavailable", manualError);
    notice(fallback(family), manualFallback);
    notice(expiry(family), manualAuth || (silentAuth && manualFirst));
    notice(guidance(family), manualAuth || silentAuth);
    for (const other of families) if (other.section !== family.section) expect(list(other)).toHaveBeenCalledTimes(1);
    if (family.section === "storico") {
      list(family).mockResolvedValueOnce([]);
      await refresh();
      notice("Nessun job storico registrato", true);
      expectReport(terminal ? 22 : 7);
    }
  });
});
