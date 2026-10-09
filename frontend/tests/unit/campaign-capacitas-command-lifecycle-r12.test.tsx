import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import { ApiError } from "@/lib/api/core";
import type {
  CapacitasAnagraficaHistoryImportJob, CapacitasInCassSyncJobListItem,
  CapacitasParticelleSyncJob, CapacitasTerreniJob,
} from "@/types/api";

const mocks = vi.hoisted(() => ({
  token: vi.fn<() => string | null>(), credentials: vi.fn(),
  terreni: { list: vi.fn(), rerun: vi.fn(), remove: vi.fn() },
  particelle: { list: vi.fn(), rerun: vi.fn(), remove: vi.fn() },
  storico: { list: vi.fn(), rerun: vi.fn(), remove: vi.fn() },
  incass: { list: vi.fn(), rerun: vi.fn(), remove: vi.fn() },
}));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", async () => ({
  listCapacitasCredentials: mocks.credentials,
  listCapacitasTerreniJobs: mocks.terreni.list,
  rerunCapacitasTerreniJob: mocks.terreni.rerun,
  deleteCapacitasTerreniJob: mocks.terreni.remove,
  listCapacitasParticelleSyncJobs: mocks.particelle.list,
  rerunCapacitasParticelleSyncJob: mocks.particelle.rerun,
  deleteCapacitasParticelleSyncJob: mocks.particelle.remove,
  listCapacitasAnagraficaHistoryJobs: mocks.storico.list,
  rerunCapacitasAnagraficaHistoryJob: mocks.storico.rerun,
  deleteCapacitasAnagraficaHistoryJob: mocks.storico.remove,
  listCapacitasInCassSyncJobs: mocks.incass.list,
  rerunCapacitasInCassSyncJob: mocks.incass.rerun,
  deleteCapacitasInCassSyncJob: mocks.incass.remove,
  isAuthError: (await import("@/lib/api/core")).isAuthError,
}));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({ ElaborazioneWorkspaceModal: () => null }));

const families = [
  { section: "terreni", label: "Terreni", prefix: "Job", fallback: "Terreni", interval: 15000, guidance: "del monitor Terreni" },
  { section: "particelle", label: "particelle", prefix: "Job particelle", fallback: "particelle", interval: 15000, guidance: "della sync progressiva particelle" },
  { section: "storico", label: "storico", prefix: "Job storico", fallback: "storico anagrafico", interval: 15000, guidance: "del monitor storico anagrafico" },
  { section: "incass", label: "avvisi", prefix: "Job avvisi", fallback: "avvisi", interval: 20000, guidance: "del monitor avvisi" },
] as const;
type Family = typeof families[number];
type Job = CapacitasTerreniJob | CapacitasParticelleSyncJob | CapacitasAnagraficaHistoryImportJob | CapacitasInCassSyncJobListItem;

function job(id: number, status = "failed", error_detail: string | null = null): Job {
  return {
    id, status, error_detail, result_json: null, credential_id: null, requested_by_user_id: 1,
    mode: "batch", payload_json: { items: [] }, subject_count: null,
    started_at: null, completed_at: null, created_at: "2026-10-09T12:00:00Z", updated_at: "2026-10-09T12:00:00Z",
  };
}
const initialRows = () => [job(11), job(12), job(13, "processing")];
const refreshedRows = () => [job(11, "failed", "Fresh target detail"), job(12, "cancelled"), job(14, "processing")];
const api = (family: Family) => mocks[family.section];
const expiry = (family: Family) => `Sessione GAIA scaduta: il monitor ${family.label} si ferma, ma i job backend gia avviati possono continuare.`;
const guidance = (family: Family) => `Rientra in GAIA per riprendere il polling ${family.guidance}.`;
const success = (family: Family, id: number, action: "rerun" | "remove") => `${family.prefix} #${id} ${action === "rerun" ? "rilanciato" : "eliminato"}.`;

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<Value>((fulfill, fail) => { resolve = fulfill; reject = fail; });
  return { promise, resolve, reject };
}
function notice(message: string, visible: boolean) {
  const matches = screen.queryAllByText(message, { exact: true });
  if (visible) {
    expect(matches.length).toBeGreaterThan(0);
    for (const match of matches) expect(match).toBeVisible();
  } else expect(matches).toHaveLength(0);
}
function row(family: Family, id: number) {
  const label = family.section === "terreni" ? `#${id}` : `Job #${id}`;
  const element = screen.getByText(label, { exact: true });
  const parent = element.closest("tr") ?? element.closest('div[class*="rounded-[24px]"], div[class*="rounded-[20px]"]');
  if (!(parent instanceof HTMLElement)) throw new Error(`Missing public job row ${id}`);
  return within(parent);
}
function expectRows(family: Family, ids: number[]) {
  const pattern = family.section === "terreni" ? /^#\d+$/ : /^Job #\d+$/;
  const actual = screen.queryAllByText(pattern).map(element => Number(element.textContent!.split("#")[1]));
  expect(actual.sort((a, b) => a - b)).toEqual([...ids].sort((a, b) => a - b));
}
function expectLoading(family: Family, busy: boolean) {
  notice(`Caricamento job ${family.label}...`, busy);
  const button = screen.getByRole("button", { name: "Aggiorna job" });
  if (busy) {
    expect(button).toBeDisabled();
    expectRows(family, []);
  } else expect(button).toBeEnabled();
}
function expectBusy(family: Family, id: number, action: "rerun" | "remove", busy: boolean) {
  const label = action === "rerun" ? (busy ? "Rerun..." : "Rilancia") : (busy ? "Elimina..." : "Elimina");
  const button = row(family, id).getByRole("button", { name: label });
  if (busy) expect(button).toBeDisabled();
  else expect(button).toBeEnabled();
}
async function click(family: Family, id: number, action: "rerun" | "remove") {
  await act(async () => {
    fireEvent.click(row(family, id).getByRole("button", { name: action === "rerun" ? "Rilancia" : "Elimina" }));
  });
}
async function tick(milliseconds: number) {
  await act(async () => { await vi.advanceTimersByTimeAsync(milliseconds); });
}
function expectListDispatch(family: Family, call: number, token: string) {
  if (family.section === "incass") expect(api(family).list).toHaveBeenNthCalledWith(call, token, { limit: 300 });
  else expect(api(family).list).toHaveBeenNthCalledWith(call, token);
}
async function mount(family: Family) {
  api(family).list.mockResolvedValue(initialRows());
  render(<ElaborazioniCapacitasWorkspace embedded initialSection={family.section} />);
  await act(async () => {});
  for (const other of families) expect(api(other).list).toHaveBeenCalledTimes(1);
  expectListDispatch(family, 1, "token-A");
  expectLoading(family, false);
  expectRows(family, [11, 12, 13]);
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.useFakeTimers();
  vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
  mocks.token.mockReturnValue("token-A");
  mocks.credentials.mockResolvedValue([]);
  for (const family of families) api(family).list.mockResolvedValue([]);
});
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); });

describe.each(families)("R12 original $section command lifecycle", family => {
  test.each(["Error", "nonError", "401", "403"] as const)("rerun awaits a deferred refresh %s failure and releases busy", async failure => {
    await mount(family);
    const command = deferred<Job>();
    const reload = deferred<Job[]>();
    api(family).rerun.mockReturnValueOnce(command.promise);
    api(family).list.mockReturnValueOnce(reload.promise);
    await click(family, 11, "rerun");
    expect(api(family).rerun).toHaveBeenCalledExactlyOnceWith("token-A", 11);
    expectBusy(family, 11, "rerun", true);
    expect(api(family).list).toHaveBeenCalledTimes(1);
    await act(async () => { command.resolve(job(999)); });
    expectListDispatch(family, 2, "token-A");
    expectLoading(family, true);
    notice(success(family, 11, "rerun"), true);
    notice(success(family, 999, "rerun"), false);
    await act(async () => {
      reload.reject(failure === "Error" ? new Error("Reload unavailable") : failure === "nonError" ? "untyped rejection" : new ApiError("Private reload detail", null, Number(failure)));
    });
    const auth = failure === "401" || failure === "403";
    expectLoading(family, false);
    expectRows(family, [11, 12, 13]);
    expectBusy(family, 11, "rerun", false);
    notice(expiry(family), auth);
    notice(guidance(family), auth);
    notice("Private reload detail", false);
    notice("Reload unavailable", failure === "Error");
    notice(`Errore caricamento job ${family.fallback}`, failure === "nonError");
    notice(success(family, 11, "rerun"), !auth);
    await tick(family.interval);
    expect(api(family).list).toHaveBeenCalledTimes(auth ? 2 : 3);
  });

  test.each(["token-B", null])("rerun retains dispatched token then refresh reads %s", async nextToken => {
    await mount(family);
    const command = deferred<Job>();
    const reload = deferred<Job[]>();
    api(family).rerun.mockReturnValueOnce(command.promise);
    api(family).list.mockReturnValueOnce(reload.promise);
    await click(family, 11, "rerun");
    expectBusy(family, 11, "rerun", true);
    expect(api(family).rerun).toHaveBeenCalledExactlyOnceWith("token-A", 11);
    mocks.token.mockReturnValue(nextToken);
    await act(async () => { command.resolve(job(999)); });
    if (nextToken) {
      expectListDispatch(family, 2, nextToken);
      expectLoading(family, true);
      notice(success(family, 11, "rerun"), true);
      await act(async () => { reload.resolve(refreshedRows()); });
      expectRows(family, [11, 12, 14]);
      expect(row(family, 11).getByText("Fresh target detail")).toBeVisible();
    } else {
      expect(api(family).list).toHaveBeenCalledTimes(1);
      expectRows(family, [11, 12, 13]);
    }
    expectLoading(family, false);
    expectBusy(family, 11, "rerun", false);
    notice(expiry(family), !nextToken);
    notice(guidance(family), !nextToken);
    notice(success(family, 11, "rerun"), Boolean(nextToken));
    expect(api(family).rerun).toHaveBeenCalledTimes(1);
  });

  test.each([
    { action: "rerun" as const, status: 401 }, { action: "rerun" as const, status: 403 },
    { action: "remove" as const, status: 401 }, { action: "remove" as const, status: 403 },
  ])("command $action ApiError $status remains ordinary error and polling continues", async ({ action, status }) => {
    await mount(family);
    const command = deferred<Job | void>();
    api(family)[action].mockReturnValueOnce(command.promise);
    await click(family, 11, action);
    expectBusy(family, 11, action, true);
    expect(api(family)[action]).toHaveBeenCalledExactlyOnceWith("token-A", 11);
    await act(async () => { command.reject(new ApiError("Command auth detail", null, status)); });
    expectRows(family, [11, 12, 13]);
    expectBusy(family, 11, action, false);
    expectLoading(family, false);
    notice("Command auth detail", true);
    notice(expiry(family), false);
    notice(guidance(family), false);
    notice(success(family, 11, action), false);
    expect(api(family).list).toHaveBeenCalledTimes(1);
    await tick(family.interval);
    expectListDispatch(family, 2, "token-A");
    notice("Command auth detail", true);
  });

  test.each([11, 12])("different-ID reruns settle #%s first and release the scalar busy ID early", async firstId => {
    await mount(family);
    const older = deferred<Job>();
    const newer = deferred<Job>();
    const firstReload = deferred<Job[]>();
    const secondReload = deferred<Job[]>();
    api(family).rerun.mockReturnValueOnce(older.promise).mockReturnValueOnce(newer.promise);
    api(family).list.mockReturnValueOnce(firstReload.promise).mockReturnValueOnce(secondReload.promise);
    await click(family, 11, "rerun");
    expectBusy(family, 11, "rerun", true);
    await click(family, 12, "rerun");
    expectBusy(family, 11, "rerun", false);
    expectBusy(family, 12, "rerun", true);
    expect(api(family).rerun).toHaveBeenNthCalledWith(1, "token-A", 11);
    expect(api(family).rerun).toHaveBeenNthCalledWith(2, "token-A", 12);
    const first = firstId === 11 ? older : newer;
    const second = firstId === 11 ? newer : older;
    const secondId = firstId === 11 ? 12 : 11;
    await act(async () => { first.resolve(job(999)); });
    expectLoading(family, true);
    expectListDispatch(family, 2, "token-A");
    notice(success(family, firstId, "rerun"), true);
    await act(async () => { firstReload.resolve(initialRows()); });
    expectLoading(family, false);
    expectBusy(family, 11, "rerun", false);
    expectBusy(family, 12, "rerun", false);
    expect(api(family).list).toHaveBeenCalledTimes(2);
    await act(async () => { second.resolve(job(999)); });
    expectLoading(family, true);
    expectListDispatch(family, 3, "token-A");
    notice(success(family, secondId, "rerun"), true);
    await act(async () => { secondReload.resolve(refreshedRows()); });
    expectLoading(family, false);
    expectRows(family, [11, 12, 14]);
    expectBusy(family, 11, "rerun", false);
    expectBusy(family, 12, "rerun", false);
    expect(api(family).rerun).toHaveBeenCalledTimes(2);
  });

  test.each([
    { firstId: 11, newerFails: false }, { firstId: 12, newerFails: false },
    { firstId: 11, newerFails: true }, { firstId: 12, newerFails: true },
  ])("different-ID deletes settle #$firstId first; newerFails=$newerFails", async ({ firstId, newerFails }) => {
    await mount(family);
    const older = deferred<void>();
    const newer = deferred<void>();
    api(family).remove.mockReturnValueOnce(older.promise).mockReturnValueOnce(newer.promise);
    await click(family, 11, "remove");
    expectBusy(family, 11, "remove", true);
    await click(family, 12, "remove");
    expectBusy(family, 11, "remove", false);
    expectBusy(family, 12, "remove", true);
    expect(api(family).remove).toHaveBeenNthCalledWith(1, "token-A", 11);
    expect(api(family).remove).toHaveBeenNthCalledWith(2, "token-A", 12);
    const settle = (id: number) => {
      if (id === 11) older.resolve();
      else if (newerFails) newer.reject(new Error("Newer delete rejected"));
      else newer.resolve();
    };
    await act(async () => { settle(firstId); });
    expectLoading(family, false);
    expectRows(family, firstId === 11 ? [12, 13] : newerFails ? [11, 12, 13] : [11, 13]);
    const pendingId = firstId === 11 ? 12 : 11;
    expectBusy(family, pendingId, "remove", false);
    notice("Newer delete rejected", firstId === 12 && newerFails);
    await act(async () => { settle(pendingId); });
    expectRows(family, newerFails ? [12, 13] : [13]);
    notice("Newer delete rejected", newerFails && pendingId === 12);
    notice(success(family, newerFails ? 11 : pendingId, "remove"), true);
    if (newerFails) expectBusy(family, 12, "remove", false);
    expect(api(family).list).toHaveBeenCalledTimes(1);
    expect(api(family).remove).toHaveBeenCalledTimes(2);
  });

  test.each([
    { mode: "manual", listFirst: true }, { mode: "manual", listFirst: false },
    { mode: "poll", listFirst: true }, { mode: "poll", listFirst: false },
  ])("delete crosses $mode list; listFirst=$listFirst preserves filtering/resurrection", async ({ mode, listFirst }) => {
    await mount(family);
    const command = deferred<void>();
    const reload = deferred<Job[]>();
    api(family).remove.mockReturnValueOnce(command.promise);
    api(family).list.mockReturnValueOnce(reload.promise);
    await click(family, 11, "remove");
    expectBusy(family, 11, "remove", true);
    expect(api(family).remove).toHaveBeenCalledExactlyOnceWith("token-A", 11);
    mocks.token.mockReturnValue("token-B");
    if (mode === "manual") {
      await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Aggiorna job" })); });
    } else {
      await tick(family.interval - 1);
      expect(api(family).list).toHaveBeenCalledTimes(1);
      await tick(1);
    }
    expectListDispatch(family, 2, "token-B");
    expectLoading(family, mode === "manual");
    if (mode === "poll") expectBusy(family, 11, "remove", true);
    if (listFirst) {
      await act(async () => { reload.resolve(refreshedRows()); });
      expectLoading(family, false);
      expectRows(family, [11, 12, 14]);
      expect(row(family, 11).getByText("Fresh target detail")).toBeVisible();
      expectBusy(family, 11, "remove", true);
      await act(async () => { command.resolve(); });
      expectRows(family, [12, 14]);
      notice("Fresh target detail", false);
    } else {
      await act(async () => { command.resolve(); });
      notice(success(family, 11, "remove"), true);
      expectLoading(family, mode === "manual");
      if (mode === "poll") expectRows(family, [12, 13]);
      await act(async () => { reload.resolve(refreshedRows()); });
      expectLoading(family, false);
      expectRows(family, [11, 12, 14]);
      expect(row(family, 11).getByText("Fresh target detail")).toBeVisible();
      expectBusy(family, 11, "remove", false);
    }
    expect(api(family).remove).toHaveBeenCalledTimes(1);
    expect(api(family).list).toHaveBeenCalledTimes(2);
    notice(expiry(family), false);
    notice(guidance(family), false);
    notice(success(family, 11, "remove"), true);
  });
});
