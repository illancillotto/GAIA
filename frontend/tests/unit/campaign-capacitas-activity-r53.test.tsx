import type { ReactNode } from "react";
import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import type { CapacitasAnagraficaHistoryImportJob, CapacitasParticelleSyncJob, CapacitasTerreniJob } from "@/types/api";

type Job = CapacitasTerreniJob | CapacitasParticelleSyncJob | CapacitasAnagraficaHistoryImportJob;
const mocks = vi.hoisted(() => ({
  token: vi.fn<() => string | null>(),
  credentials: vi.fn(),
  terreni: vi.fn<(token: string) => Promise<Job[]>>(),
  particelle: vi.fn<(token: string) => Promise<Job[]>>(),
  storico: vi.fn<(token: string) => Promise<Job[]>>(),
  incass: vi.fn(),
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

const families = ["terreni", "particelle", "storico"] as const;
const cases = [
  { statuses: [], active: false, name: "empty" },
  { statuses: ["pending"], active: true, name: "pending" },
  { statuses: ["processing"], active: true, name: "processing" },
  { statuses: ["queued_resume"], active: true, name: "queued_resume" },
  { statuses: ["cancelling"], active: false, name: "cancelling" },
  { statuses: ["cancelled"], active: false, name: "cancelled" },
  { statuses: ["succeeded"], active: false, name: "succeeded" },
  { statuses: ["completed_with_errors"], active: false, name: "completed_with_errors" },
  { statuses: ["failed"], active: false, name: "failed" },
  { statuses: ["unknown"], active: false, name: "unknown" },
  { statuses: ["PENDING"], active: false, name: "case-sensitive pending" },
  { statuses: ["processing "], active: false, name: "trailing-space processing" },
  { statuses: [""], active: false, name: "empty status" },
  { statuses: ["unknown", "cancelling", "queued_resume"], active: true, name: "active tail" },
  { statuses: ["pending", "failed", "unknown"], active: true, name: "active head" },
];

function job(id: number, status: string): Job {
  return {
    id, status, credential_id: null, requested_by_user_id: null, mode: "batch",
    payload_json: null, result_json: null, error_detail: null, started_at: null, completed_at: null,
    created_at: "2026-10-12T08:00:00Z", updated_at: "2026-10-12T08:00:00Z",
  };
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.useFakeTimers();
  mocks.token.mockReturnValue("r53-session");
  for (const list of [mocks.credentials, mocks.terreni, mocks.particelle, mocks.storico, mocks.incass]) {
    list.mockResolvedValue([]);
  }
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe.each(families)("R53 %s mounted activity membership", (family) => {
  test.each(cases)("$name preserves strict polling membership and terminal shutdown", async ({ statuses, active }) => {
    const rows = statuses.map((status, index) => job(index + 71, status));
    const list = mocks[family];
    list.mockResolvedValueOnce(rows).mockResolvedValue(rows.map((row) => ({ ...row, status: "failed" })));
    const view = render(<ElaborazioniCapacitasWorkspace embedded initialSection={family} />);
    await act(async () => {});
    expect(list).toHaveBeenCalledExactlyOnceWith("r53-session");
    for (const row of rows) {
      expect(screen.getByText(family === "terreni" ? `#${row.id}` : `Job #${row.id}`)).toBeVisible();
    }
    await act(async () => { await vi.advanceTimersByTimeAsync(14999); });
    expect(list).toHaveBeenCalledTimes(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(list).toHaveBeenCalledTimes(active ? 2 : 1);
    await act(async () => { await vi.advanceTimersByTimeAsync(45000); });
    expect(list).toHaveBeenCalledTimes(active ? 2 : 1);
    view.unmount();
    await act(async () => { await vi.advanceTimersByTimeAsync(45000); });
    expect(list).toHaveBeenCalledTimes(active ? 2 : 1);
  });
});
