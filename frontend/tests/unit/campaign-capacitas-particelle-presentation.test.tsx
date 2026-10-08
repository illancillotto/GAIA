import type { ReactNode } from "react";
import { act, cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import type { CapacitasParticelleSyncJob, CapacitasParticelleSyncJobResult } from "@/types/api";

const mocks = vi.hoisted(() => ({
  token: vi.fn(), credentials: vi.fn(), terreni: vi.fn(), particelle: vi.fn(),
  history: vi.fn(), incass: vi.fn(), authError: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", () => ({
  listCapacitasCredentials: mocks.credentials,
  listCapacitasTerreniJobs: mocks.terreni,
  listCapacitasParticelleSyncJobs: mocks.particelle,
  listCapacitasAnagraficaHistoryJobs: mocks.history,
  listCapacitasInCassSyncJobs: mocks.incass,
  isAuthError: mocks.authError,
}));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({ ElaborazioneWorkspaceModal: () => null }));

function result(overrides: Partial<CapacitasParticelleSyncJobResult> = {}): CapacitasParticelleSyncJobResult {
  const success = overrides.success_items ?? 2;
  const failed = overrides.failed_items ?? 0;
  const skipped = overrides.skipped_items ?? 0;
  const statuses = [
    ...Array.from({ length: success }, () => "synced"),
    ...Array.from({ length: failed }, () => "failed"),
    ...Array.from({ length: skipped }, () => "skipped"),
  ];
  return {
    mode: "progressive", total_items: 4, processed_items: 2,
    success_items: success, failed_items: failed, skipped_items: skipped,
    progress_percent: 50, throttle_ms: 900, aggressive_window: false, recheck_hours: 72,
    recent_items: statuses.map((status, index) => ({
      particella_id: String(680 + index), label: `Uras 1/${680 + index}`,
      status, message: status === "failed" ? "Portale non disponibile" : "Record elaborato",
    })),
    ...overrides,
  };
}

function job(id: number, overrides: Partial<CapacitasParticelleSyncJob> = {}): CapacitasParticelleSyncJob {
  return {
    id, credential_id: null, requested_by_user_id: 1, status: "processing", mode: "progressive",
    payload_json: { only_due: true, limit: 4 }, result_json: null, error_detail: null,
    started_at: "2026-10-08T12:01:00Z", completed_at: null,
    created_at: "2026-10-08T12:00:00Z", updated_at: "2026-10-08T12:02:00Z", ...overrides,
  };
}

const terminalCases = [
  {
    status: "succeeded", label: "Completato", color: "bg-emerald-500",
    processed: 4, success: 3, failed: 0, skipped: 1, progress: 100, error: null,
  },
  {
    status: "completed_with_errors", label: "Con errori", color: "bg-amber-400",
    processed: 4, success: 2, failed: 1, skipped: 1, progress: 100, error: "Una particella non sincronizzata",
  },
  {
    status: "cancelled", label: "Annullato", color: "bg-slate-300",
    processed: 2, success: 1, failed: 0, skipped: 1, progress: 50, error: null,
  },
  {
    status: "failed", label: "Fallito", color: "bg-rose-400",
    processed: 1, success: 0, failed: 1, skipped: 0, progress: 25, error: "Portale non disponibile",
  },
];

function terminalJob(id: number, outcome: typeof terminalCases[number]): CapacitasParticelleSyncJob {
  return job(id, {
    status: outcome.status, completed_at: "2026-10-08T12:02:00Z", error_detail: outcome.error,
    result_json: result({
      processed_items: outcome.processed, success_items: outcome.success, failed_items: outcome.failed,
      skipped_items: outcome.skipped, progress_percent: outcome.progress,
    }),
  });
}

async function mount(jobs: CapacitasParticelleSyncJob[]) {
  mocks.particelle.mockResolvedValue(jobs);
  render(<ElaborazioniCapacitasWorkspace embedded initialSection="particelle" />);
  await act(async () => {});
  expect(mocks.particelle).toHaveBeenCalledExactlyOnceWith("session-token");
  expect(screen.queryByText("Caricamento job particelle...")).not.toBeInTheDocument();
}

function card(id: number) {
  const element = screen.getByText(`Job #${id}`).closest('div[class*="rounded-[24px]"], div[class*="rounded-[20px]"]');
  expect(element).not.toBeNull();
  return { element: element as HTMLElement, queries: within(element as HTMLElement) };
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.useFakeTimers();
  mocks.token.mockReturnValue("session-token");
  for (const list of [mocks.credentials, mocks.terreni, mocks.particelle, mocks.history, mocks.incass]) {
    list.mockResolvedValue([]);
  }
  mocks.authError.mockReturnValue(false);
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("Capacitas Particelle active presentation residuals", () => {
  test.each([
    { label: "omitted", value: result() },
    { label: "null", value: result({ current_label: null }) },
  ])("renders progress without a dangling current-label separator when current_label is $label", async ({ value }) => {
    await mount([job(31, { result_json: value })]);
    const row = card(31);
    expect(row.queries.getByText("2/4", { exact: true })).toHaveTextContent(/^2\/4$/);
    expect(row.queries.getByText("In corso")).toBeVisible();
    expect(row.queries.getByText("50%")).toBeVisible();
    const progress = row.element.querySelector("div[style]");
    expect(progress).toHaveClass("bg-sky-500");
    expect(progress).toHaveStyle({ width: "50%" });
    expect(row.queries.getByText("Fascia diurna · 900ms · 1w")).toBeVisible();
    expect(row.queries.getByRole("button", { name: "Standard" })).toBeEnabled();
    expect(row.queries.getByRole("button", { name: "Stop" })).toBeEnabled();
    expect(row.queries.queryByRole("button", { name: "Rilancia" })).not.toBeInTheDocument();
  });

  test.each([
    { label: "null", value: null },
    { label: "persisted object without result fields", value: {} },
    { label: "persisted array", value: [] },
  ])("keeps an active job's diagnostic visible when result_json is $label", async ({ value }) => {
    await mount([job(31, { result_json: value, error_detail: "Errore transitorio del portale" })]);
    const row = card(31);
    expect(row.queries.getByText("In corso")).toBeVisible();
    expect(row.queries.getByText("Errore transitorio del portale")).toBeVisible();
    expect(row.queries.queryByText(/%$/)).not.toBeInTheDocument();
    expect(row.element.querySelector("div[style]")).toBeNull();
    expect(row.queries.queryByRole("table")).not.toBeInTheDocument();
    expect(row.queries.queryByRole("button", { name: "Standard" })).not.toBeInTheDocument();
    expect(row.queries.getByRole("button", { name: "Stop" })).toBeEnabled();
    expect(row.queries.queryByRole("button", { name: "Elimina" })).not.toBeInTheDocument();
  });
});

describe("Capacitas Particelle terminal result presentation", () => {
  test.each(terminalCases)("renders $status result progress, color and counters instead of a job diagnostic", async (outcome) => {
    await mount([terminalJob(31, outcome)]);
    const row = card(31);
    expect(row.queries.getByText(outcome.label)).toBeVisible();
    expect(row.queries.getByText(`${outcome.progress}%`)).toBeVisible();
    const progress = row.element.querySelector("div[style]");
    expect(progress).toHaveClass(outcome.color);
    expect(progress).toHaveStyle({ width: `${outcome.progress}%` });
    const processed = row.queries.getByText(String(outcome.processed), { selector: "span.text-gray-700" });
    expect(processed.parentElement).toHaveTextContent(`${outcome.processed}/4 · ok ${outcome.success} · failed ${outcome.failed}`);
    expect(row.queries.getByText(String(outcome.success), { selector: "span.text-emerald-700" })).toBeVisible();
    expect(row.queries.getByText(String(outcome.failed), { selector: "span.text-rose-600" })).toBeVisible();
    if (outcome.error) expect(row.queries.queryByText(outcome.error)).not.toBeInTheDocument();
    expect(row.queries.getByRole("button", { name: "Rilancia" })).toBeEnabled();
    expect(row.queries.getByRole("button", { name: "Elimina" })).toBeEnabled();
    expect(row.queries.queryByRole("button", { name: "Stop" })).not.toBeInTheDocument();
    expect(row.queries.queryByRole("button", { name: "Standard" })).not.toBeInTheDocument();
    expect(row.queries.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByText("Completati", { exact: true })).not.toBeInTheDocument();
  });

  test("mixed active and completed jobs retain distinct sections and their own public controls", async () => {
    const completed = terminalCases.map((outcome, index) => terminalJob(41 + index, outcome));
    await mount([...completed, job(31, { result_json: result() })]);
    expect(screen.getByText("Completati", { exact: true })).toBeVisible();
    expect(screen.getAllByText(/^Job #\d+$/).map((element) => element.textContent)).toEqual([
      "Job #31", "Job #41", "Job #42", "Job #43", "Job #44",
    ]);
    expect(card(31).queries.getByRole("button", { name: "Stop" })).toBeEnabled();
    expect(screen.getAllByRole("button", { name: "Rilancia" })).toHaveLength(4);
    expect(screen.getAllByRole("button", { name: "Elimina" })).toHaveLength(4);
    for (const [index, outcome] of terminalCases.entries()) {
      const row = card(41 + index);
      expect(row.queries.getByText(outcome.label)).toBeVisible();
      expect(row.element.querySelector("div[style]")).toHaveClass(outcome.color);
      expect(row.queries.queryByRole("button", { name: "Stop" })).not.toBeInTheDocument();
    }
  });
});
