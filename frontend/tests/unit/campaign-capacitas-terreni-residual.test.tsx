import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import type { CapacitasTerreniBatchResult, CapacitasTerreniJob, CapacitasTerreniJobCreateInput } from "@/types/api";

const mocks = vi.hoisted(() => ({
  token: vi.fn<() => string | null>(),
  credentials: vi.fn(),
  terreniJobs: vi.fn<(token: string) => Promise<CapacitasTerreniJob[]>>(),
  particelleJobs: vi.fn(),
  historyJobs: vi.fn(),
  incassJobs: vi.fn(),
  createTerreni: vi.fn<(token: string, input: CapacitasTerreniJobCreateInput) => Promise<CapacitasTerreniJob>>(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", async () => {
  const actual = await import("@/lib/api/core");
  return {
    listCapacitasCredentials: mocks.credentials,
    listCapacitasTerreniJobs: mocks.terreniJobs,
    listCapacitasParticelleSyncJobs: mocks.particelleJobs,
    listCapacitasAnagraficaHistoryJobs: mocks.historyJobs,
    listCapacitasInCassSyncJobs: mocks.incassJobs,
    createCapacitasTerreniJob: mocks.createTerreni,
    isAuthError: actual.isAuthError,
  };
});
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
vi.mock("@/components/elaborazioni/workspace-modal", () => ({
  ElaborazioneWorkspaceModal: () => null,
}));

function job(overrides: Partial<CapacitasTerreniJob> = {}): CapacitasTerreniJob {
  return {
    id: 81,
    credential_id: null,
    requested_by_user_id: null,
    status: "succeeded",
    mode: "batch",
    payload_json: { items: [] },
    result_json: null,
    error_detail: null,
    started_at: null,
    completed_at: null,
    created_at: "2026-10-08T12:00:00Z",
    updated_at: "2026-10-08T12:00:00Z",
    ...overrides,
  };
}

function monitor() {
  return within(screen.getByText("Monitor job Capacitas Terreni").closest("article")!);
}

async function mount() {
  render(<ElaborazioniCapacitasWorkspace embedded initialSection="terreni" />);
  await waitFor(() => expect(screen.getByRole("button", { name: "Aggiorna job" })).toBeEnabled());
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.token.mockReturnValue("session-token");
  for (const list of [mocks.credentials, mocks.terreniJobs, mocks.particelleJobs, mocks.historyJobs, mocks.incassJobs]) {
    list.mockResolvedValue([]);
  }
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("Capacitas Terreni residual public transitions", () => {
  test("retains the actual errors snapshot after its target disappears from the refreshed monitor", async () => {
    const failed: CapacitasTerreniBatchResult = {
      processed_items: 1,
      failed_items: 1,
      total_rows: 0,
      imported_rows: 0,
      imported_certificati: 0,
      imported_details: 0,
      linked_units: 0,
      linked_occupancies: 0,
      items: [{
        label: "Original failed parcel",
        search_key: "URAS/1/680",
        ok: false,
        total_rows: 0,
        imported_rows: 0,
        imported_certificati: 0,
        imported_details: 0,
        linked_units: 0,
        linked_occupancies: 0,
        error: "Original portal diagnostic",
      }],
    };
    mocks.terreniJobs.mockResolvedValueOnce([job({
      status: "completed_with_errors",
      payload_json: { items: [{ label: "Original failed parcel", comune: "Uras", foglio: "1", particella: "680", sezione: "", sub: "" }] },
      result_json: failed,
    })]);
    await mount();
    const initialRow = monitor().getByText("#81").closest("tr")!;
    fireEvent.click(within(initialRow).getByRole("button", { name: "Errori" }));
    expect(screen.getByRole("heading", { name: "1 item con errore" })).toBeInTheDocument();
    expect(screen.getByText("Original failed parcel")).toBeInTheDocument();
    expect(screen.getByText("URAS/1/680")).toBeInTheDocument();
    expect(screen.getByText("Original portal diagnostic")).toBeInTheDocument();

    let resolveRefresh!: (value: CapacitasTerreniJob[]) => void;
    mocks.terreniJobs.mockReturnValueOnce(new Promise(resolve => { resolveRefresh = resolve; }));
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna job" }));
    expect(monitor().getByText("Caricamento job Terreni...")).toBeInTheDocument();
    expect(screen.getByText("Original portal diagnostic")).toBeInTheDocument();
    await act(async () => resolveRefresh([job({ id: 82 })]));

    expect(monitor().getByText("#82")).toBeInTheDocument();
    expect(monitor().queryByText("#81")).not.toBeInTheDocument();
    expect(monitor().queryByText("Caricamento job Terreni...")).not.toBeInTheDocument();
    expect(screen.getByText("Job #81")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "1 item con errore" })).toBeInTheDocument();
    expect(screen.getByText("Original failed parcel")).toBeInTheDocument();
    expect(screen.getByText("URAS/1/680")).toBeInTheDocument();
    expect(screen.getByText("Original portal diagnostic")).toBeInTheDocument();
    expect(screen.queryByText("Nessun errore da mostrare.")).not.toBeInTheDocument();
    expect(mocks.terreniJobs).toHaveBeenCalledTimes(2);
    expect(mocks.terreniJobs).toHaveBeenNthCalledWith(2, "session-token");

    fireEvent.click(screen.getByText("Chiudi", { selector: "button" }));
    expect(screen.queryByRole("heading", { name: "1 item con errore" })).not.toBeInTheDocument();
    expect(screen.queryByText("Original portal diagnostic")).not.toBeInTheDocument();
    expect(monitor().getByText("#82")).toBeInTheDocument();
  });

  test("submits exact worker counts for the actual parallel toggle sequence 1 to 2 to 1", async () => {
    const createdJobs: CapacitasTerreniJob[] = [];
    mocks.createTerreni.mockImplementation(async (_token, input) => {
      const created = job({ id: 91 + createdJobs.length, status: "pending", payload_json: { ...input } });
      createdJobs.push(created);
      mocks.terreniJobs.mockResolvedValue([...createdJobs]);
      return created;
    });
    await mount();
    const contents = "comune,foglio,particella\nUras,1,680";
    const file = new File([contents], "terreni.csv", { type: "text/csv" });
    Object.defineProperty(file, "text", { value: () => Promise.resolve(contents) });
    fireEvent.change(screen.getByLabelText("File batch"), { target: { files: [file] } });
    const submit = screen.getByRole("button", { name: "Avvia job batch" });
    await waitFor(() => expect(submit).toBeEnabled());

    const input: CapacitasTerreniJobCreateInput = {
      credential_id: undefined,
      continue_on_error: true,
      fetch_certificati: true,
      fetch_details: true,
      double_speed: false,
      parallel_workers: 1,
      throttle_ms: undefined,
      auto_resume: false,
      items: [{ label: "Uras 1/680", comune: "Uras", foglio: "1", particella: "680", sezione: "", sub: "" }],
    };
    for (const [index, workers] of [1, 2, 1].entries()) {
      if (index > 0) fireEvent.click(screen.getByRole("button", { name: /Parallelo x2/ }));
      const toggle = screen.getByRole("button", { name: /Parallelo x2/ });
      expect(within(toggle).getByText(workers === 2 ? "Parallelo x2 attivo" : "Parallelo x2", { exact: true })).toBeInTheDocument();
      expect(within(toggle).getByText(workers === 2 ? "Apre 2 sessioni Capacitas dedicate per il job." : "Divide il batch su due worker concorrenti.")).toBeInTheDocument();
      fireEvent.click(submit);
      await screen.findByText(`Job batch #${91 + index} creato con 1 righe in velocita standard e ${workers} worker.`);
      await waitFor(() => expect(submit).toBeEnabled());
      expect(mocks.createTerreni).toHaveBeenCalledTimes(index + 1);
      expect(mocks.createTerreni).toHaveBeenNthCalledWith(index + 1, "session-token", { ...input, parallel_workers: workers });
      expect(mocks.terreniJobs).toHaveBeenCalledTimes(index + 2);
      expect(mocks.terreniJobs).toHaveBeenLastCalledWith("session-token");
    }
    expect(monitor().getAllByText(/^#9[123]$/).map(element => element.textContent)).toEqual(["#91", "#92", "#93"]);
  });
});
