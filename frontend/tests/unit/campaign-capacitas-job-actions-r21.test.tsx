import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import type {
  CapacitasAnagraficaHistoryImportJob,
  CapacitasInCassSyncJobListItem,
  CapacitasTerreniJob,
} from "@/types/api";

const mocks = vi.hoisted(() => ({
  token: vi.fn(), credentials: vi.fn(), particelle: vi.fn(),
  terreni: { list: vi.fn(), rerun: vi.fn(), remove: vi.fn() },
  storico: { list: vi.fn(), rerun: vi.fn(), remove: vi.fn() },
  incass: { list: vi.fn(), rerun: vi.fn(), remove: vi.fn() },
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", () => ({
  listCapacitasCredentials: mocks.credentials,
  listCapacitasParticelleSyncJobs: mocks.particelle,
  listCapacitasTerreniJobs: mocks.terreni.list,
  rerunCapacitasTerreniJob: mocks.terreni.rerun,
  deleteCapacitasTerreniJob: mocks.terreni.remove,
  listCapacitasAnagraficaHistoryJobs: mocks.storico.list,
  rerunCapacitasAnagraficaHistoryJob: mocks.storico.rerun,
  deleteCapacitasAnagraficaHistoryJob: mocks.storico.remove,
  listCapacitasInCassSyncJobs: mocks.incass.list,
  rerunCapacitasInCassSyncJob: mocks.incass.rerun,
  deleteCapacitasInCassSyncJob: mocks.incass.remove,
  isAuthError: () => false,
}));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({ ElaborazioneWorkspaceModal: () => null }));

const families = [
  { section: "terreni", tab: /^Terreni/ },
  { section: "storico", tab: /^Storico anagrafico/ },
  { section: "incass", tab: /^Avvisi pagamenti/ },
] as const;
type Family = typeof families[number];
type Job = CapacitasTerreniJob | CapacitasAnagraficaHistoryImportJob | CapacitasInCassSyncJobListItem;
type Action = "rerun" | "remove";

const eligibility = [
  { status: "pending", disabled: true },
  { status: "processing", disabled: true },
  { status: "queued_resume", disabled: true },
  { status: "succeeded", disabled: false },
  { status: "completed_with_errors", disabled: false },
  { status: "failed", disabled: false },
  { status: "cancelling", disabled: false },
  { status: "cancelled", disabled: false },
  { status: "unknown", disabled: false },
  { status: "PENDING", disabled: false },
  { status: "", disabled: false },
];

function job(id = 11, status = "failed"): Job {
  return {
    id, status, error_detail: null, result_json: null, credential_id: null,
    requested_by_user_id: 1, mode: "batch", payload_json: { items: [] }, subject_count: null,
    started_at: null, completed_at: null,
    created_at: "2026-10-10T12:00:00Z", updated_at: "2026-10-10T12:00:00Z",
  };
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<Value>((fulfill, fail) => { resolve = fulfill; reject = fail; });
  return { promise, resolve, reject };
}

function row(family: Family, id = 11) {
  const label = family.section === "terreni" ? `#${id}` : `Job #${id}`;
  const element = screen.getByText(label, { exact: true });
  const container = element.closest("tr") ?? element.closest('div[class*="rounded-[24px]"]');
  if (!(container instanceof HTMLElement)) throw new Error(`Missing rendered ${family.section} job ${id}`);
  return within(container);
}

function actionButton(family: Family, action: Action, busy = false, id = 11) {
  const name = action === "rerun" ? (busy ? "Rerun..." : "Rilancia") : (busy ? "Elimina..." : "Elimina");
  return row(family, id).getByRole<HTMLButtonElement>("button", { name });
}

async function mount(family: Family, records: Job[] = [job()]) {
  mocks[family.section].list.mockResolvedValue(records);
  render(<ElaborazioniCapacitasWorkspace embedded initialSection={family.section} />);
  await act(async () => {});
  for (const current of families) expect(mocks[current.section].list).toHaveBeenCalledTimes(1);
  expect(mocks.particelle).toHaveBeenCalledTimes(1);
  expect(actionButton(family, "rerun")).toBeEnabled();
  for (const current of families) {
    expect(mocks[current.section].rerun).not.toHaveBeenCalled();
    expect(mocks[current.section].remove).not.toHaveBeenCalled();
  }
}

async function click(button: HTMLElement) {
  await act(async () => { fireEvent.click(button); });
}

async function navigate(family: Family) {
  const navigation = screen.getByRole("navigation", { name: "Sezioni Capacitas" });
  await click(within(navigation).getByRole("button", { name: family.tab }));
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.useFakeTimers();
  mocks.token.mockReturnValue("session-token");
  mocks.credentials.mockResolvedValue([]);
  mocks.particelle.mockResolvedValue([]);
  for (const family of families) {
    mocks[family.section].list.mockResolvedValue([]);
    mocks[family.section].rerun.mockResolvedValue(job(99));
    mocks[family.section].remove.mockResolvedValue(undefined);
  }
});

afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); });

describe.each(families)("R21 public $section action presentation", (family) => {
  test.each(eligibility)("status '$status' retains exact deletion eligibility and blocked-click behavior", async ({ status, disabled }) => {
    await mount(family, [job(11, status)]);
    const rerun = actionButton(family, "rerun");
    const remove = actionButton(family, "remove");
    expect(rerun).toBeEnabled();
    expect(remove).toHaveProperty("disabled", disabled);
    expect(rerun.className).toBe("btn-secondary");
    expect(remove.className).toBe("btn-secondary");
    expect(rerun).toHaveAttribute("type", "button");
    expect(remove).toHaveAttribute("type", "button");
    expect(rerun.nextElementSibling).toBe(remove);
    if (disabled) {
      await click(remove);
      expect(mocks[family.section].remove).not.toHaveBeenCalled();
      expect(mocks[family.section].rerun).not.toHaveBeenCalled();
      expect(mocks[family.section].list).toHaveBeenCalledTimes(1);
    }
  });

  test.each(["rerun", "remove"] as const)("%s reads the retained API job ID at click time, not render time", async (action) => {
    const record = job();
    await mount(family, [record]);
    const button = actionButton(family, action);
    const command = deferred<Job | void>();
    mocks[family.section][action].mockReturnValueOnce(command.promise);
    record.id = 92;
    expect(mocks[family.section][action]).not.toHaveBeenCalled();
    await click(button);
    expect(mocks[family.section][action]).toHaveBeenCalledExactlyOnceWith("session-token", 92);
    expect(mocks[family.section].list).toHaveBeenCalledTimes(1);
    expect(actionButton(family, action, true, 92)).toBeDisabled();
  });

  test.each(["rerun", "remove"] as const)("overlapping %s first keeps independent busy/deleting state and other rows enabled", async (firstAction) => {
    await mount(family, [job(), job(12)]);
    const rerun = deferred<Job>();
    const remove = deferred<void>();
    mocks[family.section].rerun.mockReturnValueOnce(rerun.promise);
    mocks[family.section].remove.mockReturnValueOnce(remove.promise);
    const secondAction = firstAction === "rerun" ? "remove" : "rerun";
    await click(actionButton(family, firstAction));
    expect(actionButton(family, firstAction, true)).toBeDisabled();
    expect(actionButton(family, secondAction)).toBeEnabled();
    await click(actionButton(family, secondAction));
    expect(mocks[family.section].rerun).toHaveBeenCalledExactlyOnceWith("session-token", 11);
    expect(mocks[family.section].remove).toHaveBeenCalledExactlyOnceWith("session-token", 11);
    expect(actionButton(family, "rerun", true)).toBeDisabled();
    expect(actionButton(family, "remove", true)).toBeDisabled();
    expect(actionButton(family, "rerun", false, 12)).toBeEnabled();
    expect(actionButton(family, "remove", false, 12)).toBeEnabled();
    await act(async () => {
      if (firstAction === "rerun") rerun.reject(new Error("R21 first command failed"));
      else remove.reject(new Error("R21 first command failed"));
    });
    expect(actionButton(family, firstAction)).toBeEnabled();
    expect(actionButton(family, secondAction, true)).toBeDisabled();
    expect(mocks[family.section].list).toHaveBeenCalledTimes(1);
  });

  test.each(["rerun", "remove"] as const)("pending %s remains isolated when other families have the same numeric ID", async (action) => {
    for (const current of families) mocks[current.section].list.mockResolvedValue([job()]);
    await mount(family);
    const command = deferred<Job | void>();
    mocks[family.section][action].mockReturnValueOnce(command.promise);
    await click(actionButton(family, action));
    expect(mocks[family.section][action]).toHaveBeenCalledExactlyOnceWith("session-token", 11);
    for (const other of families.filter((current) => current.section !== family.section)) {
      await navigate(other);
      expect(actionButton(other, "rerun")).toBeEnabled();
      expect(actionButton(other, "remove")).toBeEnabled();
      expect(mocks[other.section].rerun).not.toHaveBeenCalled();
      expect(mocks[other.section].remove).not.toHaveBeenCalled();
      expect(mocks[other.section].list).toHaveBeenCalledTimes(1);
    }
    await navigate(family);
    expect(actionButton(family, action, true)).toBeDisabled();
    expect(actionButton(family, action === "rerun" ? "remove" : "rerun")).toBeEnabled();
    expect(mocks[family.section].list).toHaveBeenCalledTimes(1);
  });

  test("retains direct parent shape, sibling order, classes and untouched family controls", async () => {
    const record = job();
    if (family.section === "terreni") {
      record.result_json = {
        items: [], processed_items: 1, failed_items: 1, total_rows: 0, imported_rows: 0,
        imported_certificati: 0, imported_details: 0, linked_units: 0, linked_occupancies: 0,
      };
    } else if (family.section === "incass") {
      record.result_json = {
        items: [], processed_subjects: 1, failed_subjects: 0,
        notices_found: 0, notices_synced: 0, total_items: 2,
      };
    }
    await mount(family, [record]);
    const rerun = actionButton(family, "rerun");
    const remove = actionButton(family, "remove");
    const parent = rerun.parentElement!;
    expect(parent.tagName).toBe("DIV");
    expect(parent.className).toBe("flex flex-wrap items-center gap-2");
    expect(remove.parentElement).toBe(parent);
    expect(rerun.nextElementSibling).toBe(remove);
    expect(remove.nextElementSibling).toBeNull();
    expect(rerun.className).toBe("btn-secondary");
    expect(remove.className).toBe("btn-secondary");
    expect(rerun).toHaveAttribute("type", "button");
    expect(remove).toHaveAttribute("type", "button");
    if (family.section === "terreni") {
      const details = row(family).getByRole("button", { name: "Dettagli" });
      const errors = row(family).getByRole("button", { name: "Errori" });
      expect([...parent.children]).toEqual([details, errors, rerun, remove]);
      expect(details.className).toBe("btn-secondary");
      expect(errors.className).toBe("btn-secondary text-amber-700");
    } else if (family.section === "incass") {
      const progress = within(parent).getByText("50%", { exact: true });
      expect([...parent.children]).toEqual([progress, rerun, remove]);
      expect(progress.tagName).toBe("SPAN");
      expect(progress.className).toBe("rounded-full bg-white px-3 py-1 text-sm font-semibold text-[#1D4E35] shadow-sm");
    } else {
      expect([...parent.children]).toEqual([rerun, remove]);
    }
  });
});
