import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioneRequestWorkspace } from "@/components/elaborazioni/request-workspace";
import { ContinuousCatastoSyncPanel } from "@/components/elaborazioni/continuous-catasto-sync-panel";

const api = vi.hoisted(() => ({
  updateConfig: vi.fn(),
  refreshSource: vi.fn(),
  runNow: vi.fn(),
  getCredentials: vi.fn(),
  getStatus: vi.fn(),
  token: "token" as string | null,
  config: {
  enabled: false,
  credential_id: null,
  credential_ids: ["credential-a"],
  primary_enabled: true,
  secondary_enabled: false,
  role_parcel_refresh_hours: 24,
  role_subject_refresh_hours: 48,
  consortium_parcel_refresh_hours: 720,
  registry_subject_refresh_hours: 720,
  batch_size: 20,
  source_watermarks: { target_count: 12 },
  last_planner_at: null,
  last_source_refresh_at: null,
  last_batch_started_at: null,
  last_error_message: null,
  updated_by_user_id: null,
  created_at: "2026-08-28T10:00:00Z",
  updated_at: "2026-08-28T10:00:00Z",
  },
}));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: () => api.token }));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getCatastoComuni: vi.fn().mockResolvedValue([]),
  getElaborazioneBatches: vi.fn().mockResolvedValue([]),
  getElaborazioneCredentials: (...args: unknown[]) => api.getCredentials(...args),
  getElaborazioneRuoloAutoSyncStatus: (...args: unknown[]) => api.getStatus(...args),
  updateElaborazioneRuoloAutoSyncConfig: (...args: unknown[]) => api.updateConfig(...args),
  refreshElaborazioneRuoloAutoSyncSource: (...args: unknown[]) => api.refreshSource(...args),
  runElaborazioneRuoloAutoSyncNow: (...args: unknown[]) => api.runNow(...args),
}));

describe("ElaborazioneRequestWorkspace continuous sync", () => {
  beforeEach(() => {
    api.token = "token";
    api.getCredentials.mockReset().mockResolvedValue({
      credentials: [
        { id: "credential-a", label: "Alessandro", sister_username: "ale", active: true },
        { id: "credential-b", label: "Marika", sister_username: "marika", active: true },
        { id: "credential-off", label: "Marco", sister_username: "marco", active: false },
      ],
      default_credential: null,
    });
    api.getStatus.mockReset().mockResolvedValue({
      config: api.config,
      counts: { total: 0, pending: 0, queued: 0, processing: 0, completed: 0, blocked_source: 0, blocked_runtime: 0 },
      running_batch: null,
      last_batch: null,
      error_items: [], recent_items: [],
      scope_counts: { ruolo_particella: { completed: 8, pending: 2 } },
      available_credential_ids: ["credential-a"],
      perpetual_error_items: [], perpetual_recent_items: [],
    });
    api.updateConfig.mockReset().mockResolvedValue({ ...api.config, enabled: true });
    api.refreshSource.mockReset().mockResolvedValue({ success: true, message: "Sorgenti aggiornate" });
    api.runNow.mockReset().mockResolvedValue({ success: true, message: "Micro-batch avviato" });
  });

  test("configures a multi-credential pool and both priority levels", async () => {
    render(<ElaborazioneRequestWorkspace embedded initialMode="autosync" />);

    expect(await screen.findByText("Sincronizzazione catastale continua")).toBeInTheDocument();
    expect(screen.getByText("8", { exact: false })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox", { name: /Marika/ }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Priorità 2/ }));
    fireEvent.click(screen.getByRole("button", { name: "Metti su ON" }));

    await waitFor(() => expect(api.updateConfig).toHaveBeenCalled());
    expect(api.updateConfig.mock.calls[0][1]).toMatchObject({
      enabled: true,
      credential_ids: ["credential-a", "credential-b"],
      primary_enabled: true,
      secondary_enabled: true,
      batch_size: 20,
    });
  });

  test("uses the continuous refresh and run endpoints", async () => {
    render(<ElaborazioneRequestWorkspace embedded initialMode="autosync" />);
    await screen.findByText("Sincronizzazione catastale continua");

    fireEvent.click(screen.getByRole("button", { name: "Aggiorna sorgente" }));
    await waitFor(() => expect(api.refreshSource).toHaveBeenCalledWith("token"));
    fireEvent.click(screen.getByRole("button", { name: "Esegui adesso" }));
    await waitFor(() => expect(api.runNow).toHaveBeenCalledWith("token"));
  });

  test("renders active batch, subject and parcel items and disables the flow", async () => {
    api.getStatus.mockResolvedValue({
      ...(await api.getStatus()),
      config: { ...api.config, enabled: true, credential_ids: null, credential_id: "credential-a", last_source_refresh_at: "2026-08-28T10:00:00Z" },
      running_batch: { id: "batch", name: null, current_operation: null, status: "processing" },
      perpetual_error_items: [{ id: "subject", search_mode: "soggetto", subject_kind: null, subject_identifier: null, intestazione: null, attempt_count: 2, next_due_at: "2026-08-29T10:00:00Z", last_error_message: "timeout", status: "pending" }],
      perpetual_recent_items: [{ id: "parcel", search_mode: "immobile", comune: null, foglio: null, particella: null, attempt_count: 1, next_due_at: "2026-08-29T10:00:00Z", last_error_message: null, status: "completed" }],
    });
    render(<ContinuousCatastoSyncPanel />);
    expect(await screen.findByText("Micro-batch attivo")).toBeInTheDocument();
    expect(screen.getByText(/identificativo mancante/)).toBeInTheDocument();
    expect(screen.getByText(/Comune non risolto/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Metti su OFF" }));
    await waitFor(() => expect(api.updateConfig).toHaveBeenCalledWith("token", expect.objectContaining({ enabled: false })));
  });

  test("shows load and action failures", async () => {
    api.getCredentials.mockRejectedValueOnce(new Error("pool non disponibile"));
    const { unmount } = render(<ContinuousCatastoSyncPanel />);
    expect(await screen.findByText("pool non disponibile")).toBeInTheDocument();
    unmount();

    api.getCredentials.mockResolvedValue({ credentials: [{ id: "credential-a", label: "Alessandro", sister_username: "ale", active: true }] });
    api.refreshSource.mockRejectedValueOnce("errore generico");
    render(<ContinuousCatastoSyncPanel />);
    await screen.findByText("Sincronizzazione catastale continua");
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna sorgente" }));
    await waitFor(() => expect(screen.getAllByText("Errore sincronizzazione")).toHaveLength(2));
    api.refreshSource.mockRejectedValueOnce(new Error("errore specifico"));
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna sorgente" }));
    expect(await screen.findByText("errore specifico")).toBeInTheDocument();
  });

  test("handles empty token and edits SLA values", async () => {
    api.token = null;
    const { unmount } = render(<ContinuousCatastoSyncPanel />);
    expect(screen.getByText("Sincronizzazione catastale continua")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna sorgente" }));
    unmount();

    api.token = "token";
    render(<ContinuousCatastoSyncPanel />);
    await screen.findByText("Alessandro");
    fireEvent.click(screen.getByRole("checkbox", { name: /Priorità 1/ }));
    for (const label of ["Particelle a ruolo", "Soggetti a ruolo", "Particelle consorzio", "Soggetti anagrafe", "Righe per micro-batch"]) {
      fireEvent.change(screen.getByLabelText(label), { target: { value: "0" } });
    }
    fireEvent.change(screen.getByLabelText("Particelle a ruolo"), { target: { value: "12" } });
    fireEvent.click(screen.getByRole("checkbox", { name: /Alessandro/ }));
    expect(screen.getByRole("button", { name: "Esegui adesso" })).toBeDisabled();
  });

  test("supports an initially empty credential selection and non-error load rejection", async () => {
    api.getStatus.mockResolvedValueOnce({
      ...(await api.getStatus()),
      config: { ...api.config, credential_ids: null, credential_id: null },
      available_credential_ids: [],
    });
    const { unmount } = render(<ContinuousCatastoSyncPanel />);
    expect((await screen.findAllByText(/occupata o fuori orario/)).length).toBeGreaterThan(0);
    unmount();
    api.getCredentials.mockRejectedValueOnce("load failure");
    render(<ContinuousCatastoSyncPanel />);
    expect(await screen.findByText("Errore caricamento sincronizzazione")).toBeInTheDocument();
  });

  test("ignores a late load failure after unmount", async () => {
    let rejectLoad: (reason: unknown) => void = () => undefined;
    api.getCredentials.mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectLoad = reject; }));
    const { unmount } = render(<ContinuousCatastoSyncPanel />);
    unmount();
    rejectLoad(new Error("late failure"));
    await Promise.resolve();
  });
});
